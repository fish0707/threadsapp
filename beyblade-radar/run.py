"""排程主迴圈。

一輪:各 monitor 抓即時狀態 → 寫進行事曆(去重/狀態機)→ 有變更就通知。
跑法:
    python run.py                 # 常駐迴圈(每 POLL_INTERVAL_SEC 跑一輪)—— 家裡電腦用
    python run.py --once          # 只跑一輪 —— GitHub Actions 排程用
    python run.py --test-notify   # 送一則測試訊息,確認 Telegram 設定正確

分工(用 RADAR_PLATFORMS 切):
    家裡電腦     RADAR_PLATFORMS=biccamera   Bic 會擋雲端 IP,只能用家用網路抓
    GitHub Actions RADAR_PLATFORMS=rakuten_jp  樂天官方 API,雲端可用
"""

from __future__ import annotations

import argparse
import time

from alerts import is_targeted, select_alerts
from calendar_db import Calendar, Change
from config import SEARCHES, SETTINGS, TARGETS, WATCHES
from health import HealthTracker
from monitors.biccamera import BicCameraMonitor
from monitors.eslite import EsliteMonitor
from monitors.funbox import FunboxMonitor
from monitors.momo import MomoMonitor
from monitors.pchome import PChomeMonitor
from monitors.rakuten_jp import RakutenJPMonitor
from notify import Notifier

# 盯「已知商品碼」的 monitor
ITEM_MONITORS = [BicCameraMonitor(), MomoMonitor(), PChomeMonitor(), FunboxMonitor()]
# 掃「搜尋頁 / 搜尋 API」的發現式 monitor(一站一個 adapter)
DISCOVERY_MONITORS = [RakutenJPMonitor(), EsliteMonitor()]


def run_once(cal: Calendar, notifier: Notifier, now: int | None = None) -> int:
    """跑一輪。回傳送出的通知數(不含健康警示)。"""
    lead = SETTINGS.imminent_lead_min * 60
    health = HealthTracker(cal, SETTINGS.health_fail_threshold)
    plain: list[Change] = []          # 一般狀態變更通知(台灣模式用)
    targeted: list = []               # 目標條件通知(日本模式)
    n_obs = 0

    jobs = [(m, WATCHES, "fetch") for m in ITEM_MONITORS] + \
           [(m, SEARCHES, "fetch_searches") for m in DISCOVERY_MONITORS]

    for mon, items, method in jobs:
        if not SETTINGS.platform_enabled(mon.platform):
            continue                  # 這台機器不負責這個平台(見 RADAR_PLATFORMS)
        if not any(i.platform == mon.platform for i in items):
            continue                  # 這個平台目前沒設定任何監控(例如已停用的台灣通路)

        try:
            snaps = getattr(mon, method)(items)
            error = getattr(mon, "last_error", None)
        except Exception as exc:      # 單一 monitor 出錯不拖垮整輪
            print(f"[run] {mon.platform} 失敗: {exc}")
            snaps, error = [], str(exc)

        warning = health.update(mon.platform, error)
        if warning:
            notifier.send(warning)
        n_obs += len(snaps)

        if is_targeted(mon.platform, TARGETS):
            # 有目標條件的平台:只在商品「進入條件」時通知,首輪也照常通知。
            changes = cal.upsert_many(snaps, now=now, imminent_lead_sec=lead)
            targeted.extend(select_alerts(changes, TARGETS))
        elif method == "fetch_searches":
            # 沒設目標的發現式掃描:首次掃描建立基準線(不通知),避免第一輪洗版。
            first_run = cal.count_platform(mon.platform) == 0
            changes = cal.upsert_many(snaps, now=now, imminent_lead_sec=lead)
            if first_run:
                print(f"[run] {mon.platform} 首次掃描,建立基準線 {len(snaps)} 筆(不通知)。")
            else:
                plain.extend(changes)
        else:
            plain.extend(cal.upsert_many(snaps, now=now, imminent_lead_sec=lead))

    for c in plain:
        notifier.notify_change(c)
    for c, t in targeted:
        notifier.notify_target(c, t)

    sent = len(plain) + len(targeted)
    if sent:
        print(f"[run] 本輪 {n_obs} 筆觀測,送出 {sent} 則通知。")
    else:
        print(f"[run] 本輪 {n_obs} 筆觀測,無需通知。")
    return sent


def main() -> None:
    p = argparse.ArgumentParser(description="Beyblade X 雷達(日本:Bic Camera / 樂天)")
    p.add_argument("--once", action="store_true", help="只跑一輪(cron 模式)")
    p.add_argument("--test-notify", action="store_true", help="送一則測試訊息後結束")
    args = p.parse_args()

    notifier = Notifier()
    if args.test_notify:
        ok = notifier.send("🧪 雷達測試訊息:收到這則代表 Telegram 設定正確。")
        print("[run] 測試訊息已送出。" if ok else "[run] 測試訊息送出失敗,請檢查 .env 的 Telegram 設定。")
        return

    cal = Calendar(SETTINGS.db_path)
    platforms = ",".join(SETTINGS.radar_platforms) or "全部"
    if args.once:
        run_once(cal, notifier)
        cal.close()
        return

    print(f"[run] 常駐模式,每 {SETTINGS.poll_interval_sec}s 一輪,負責平台:{platforms}。Ctrl-C 結束。")
    try:
        while True:
            try:
                run_once(cal, notifier)
            except Exception as exc:  # 單輪的意外錯誤不讓常駐程式停掉
                print(f"[run] 本輪發生未預期錯誤,下一輪繼續:{exc!r}")
            time.sleep(SETTINGS.poll_interval_sec)
    except KeyboardInterrupt:
        print("\n[run] 已停止。")
    finally:
        cal.close()


if __name__ == "__main__":
    main()
