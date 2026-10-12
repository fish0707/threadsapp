"""排程主迴圈。

一輪:各 monitor 抓即時狀態 → 寫進行事曆(去重/狀態機)→ 有變更就通知。
兩種跑法:
    python run.py            # 常駐迴圈(每 POLL_INTERVAL_SEC 跑一輪)
    python run.py --once     # 只跑一輪(給 cron / GitHub Actions 排程用)

部署建議:單機只有開機才跑;要可靠命中 00:00 開賣,放常開主機
(Raspberry Pi / 便宜雲主機),或用 GitHub Actions 排程呼叫 `--once`。
"""

from __future__ import annotations

import argparse
import time

from alerts import is_targeted, select_alerts
from calendar_db import Calendar
from config import SEARCHES, SETTINGS, TARGETS, WATCHES
from monitors.eslite import EsliteMonitor
from monitors.funbox import FunboxMonitor
from monitors.momo import MomoMonitor
from monitors.pchome import PChomeMonitor
from monitors.rakuten_jp import RakutenJPMonitor
from monitors.base import ProductSnapshot
from notify import Notifier

# 盯「已知商品碼」的 monitor
ITEM_MONITORS = [MomoMonitor(), PChomeMonitor(), FunboxMonitor()]
# 掃「搜尋頁 / 搜尋 API」的發現式 monitor(一站一個 adapter)
DISCOVERY_MONITORS = [RakutenJPMonitor(), EsliteMonitor()]


def run_once(cal: Calendar, notifier: Notifier, now: int | None = None) -> int:
    """跑一輪。回傳送出的通知數。"""
    lead = SETTINGS.imminent_lead_min * 60
    all_changes = []
    n_obs = 0

    # 1) 盯已知商品碼
    item_snaps: list[ProductSnapshot] = []
    for mon in ITEM_MONITORS:
        try:
            item_snaps.extend(mon.fetch(WATCHES))
        except Exception as exc:  # 單一 monitor 出錯不拖垮整輪
            print(f"[run] monitor {mon.platform} 失敗: {exc}")
    n_obs += len(item_snaps)
    all_changes.extend(cal.upsert_many(item_snaps, now=now, imminent_lead_sec=lead))

    # 2) 發現式掃描
    #    - 有設目標價的平台(如樂天 UX-15):只在商品「進入條件」時通知,首輪也照常通知。
    #    - 沒設目標的平台:首次掃描建立基準線(不通知),避免第一輪洗版。
    target_alerts = []
    for mon in DISCOVERY_MONITORS:
        if not any(s.platform == mon.platform for s in SEARCHES):
            continue  # 這個平台目前沒設定任何掃描(例如已停用的誠品)
        try:
            dsnaps = mon.fetch_searches(SEARCHES)
        except Exception as exc:
            print(f"[run] discovery {mon.platform} 失敗: {exc}")
            continue
        n_obs += len(dsnaps)
        if is_targeted(mon.platform, TARGETS):
            changes = cal.upsert_many(dsnaps, now=now, imminent_lead_sec=lead)
            target_alerts.extend(select_alerts(changes, TARGETS))
            continue
        first_run = cal.count_platform(mon.platform) == 0
        changes = cal.upsert_many(dsnaps, now=now, imminent_lead_sec=lead)
        if first_run:
            print(f"[run] {mon.platform} 首次掃描,建立基準線 {len(dsnaps)} 筆(不通知)。")
        else:
            all_changes.extend(changes)

    for c in all_changes:
        notifier.notify_change(c)
    for c, t in target_alerts:
        notifier.notify_target(c, t)

    sent = len(all_changes) + len(target_alerts)
    if sent:
        print(f"[run] 本輪 {n_obs} 筆觀測,送出 {sent} 則通知。")
    else:
        print(f"[run] 本輪 {n_obs} 筆觀測,無需通知。")
    return sent


def main() -> None:
    p = argparse.ArgumentParser(description="Beyblade X 雷達(目前:日本樂天 UX-15 目標價通知)")
    p.add_argument("--once", action="store_true", help="只跑一輪(cron 模式)")
    args = p.parse_args()

    cal = Calendar(SETTINGS.db_path)
    notifier = Notifier()

    if args.once:
        run_once(cal, notifier)
        return

    print(f"[run] 常駐模式,每 {SETTINGS.poll_interval_sec}s 一輪。Ctrl-C 結束。")
    try:
        while True:
            run_once(cal, notifier)
            time.sleep(SETTINGS.poll_interval_sec)
    except KeyboardInterrupt:
        print("\n[run] 已停止。")
    finally:
        cal.close()


if __name__ == "__main__":
    main()
