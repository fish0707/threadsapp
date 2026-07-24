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

from calendar_db import Calendar
from config import SETTINGS, WATCHES
from monitors.funbox import FunboxMonitor
from monitors.momo import MomoMonitor
from monitors.pchome import PChomeMonitor
from monitors.base import ProductSnapshot
from notify import Notifier

MONITORS = [MomoMonitor(), PChomeMonitor(), FunboxMonitor()]


def run_once(cal: Calendar, notifier: Notifier, now: int | None = None) -> int:
    """跑一輪。回傳送出的通知數。"""
    snaps: list[ProductSnapshot] = []
    for mon in MONITORS:
        try:
            snaps.extend(mon.fetch(WATCHES))
        except Exception as exc:  # 單一 monitor 出錯不拖垮整輪
            print(f"[run] monitor {mon.platform} 失敗: {exc}")

    changes = cal.upsert_many(
        snaps, now=now, imminent_lead_sec=SETTINGS.imminent_lead_min * 60
    )
    for c in changes:
        notifier.notify_change(c)
    if changes:
        print(f"[run] 本輪 {len(snaps)} 筆觀測,{len(changes)} 筆變更並已通知。")
    else:
        print(f"[run] 本輪 {len(snaps)} 筆觀測,無變更。")
    return len(changes)


def main() -> None:
    p = argparse.ArgumentParser(description="Beyblade X 原價開賣雷達")
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
