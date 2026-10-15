"""Bic Camera 校準工具 —— 在「家裡電腦」先跑這支,確認抓得到、判斷得對。

Bic 的頁面結構無法在開發環境確認,雷達的判斷規則是依常見寫法推的。
這支會印出:robots.txt 是否允許、HTTP 狀態、是否被擋、JSON-LD 內容、
命中的關鍵字與前後文、最後判定 —— 整段貼回來就能微調規則。

用法(在 beyblade-radar/ 目錄下):
    python tools/biccamera_check.py                 # 預設檢查 config 裡的 Bic 商品
    python tools/biccamera_check.py 15680151        # 指定商品碼
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402

from config import WATCHES  # noqa: E402
from monitors.biccamera import (  # noqa: E402
    PRODUCT_URL, BicCameraMonitor, BicFetchError, _headers,
)

_MODE_LABEL = {
    "preorder": "✅ 可預購(會通知)",
    "instock": "✅ 有貨(會通知)",
    "unavailable": "⏳ 目前不能下單(等它變化時通知)",
    "unknown": "❓ 判斷不出來",
}


def main() -> int:
    default_id = next((w.item_id for w in WATCHES if w.platform == "biccamera"), "15680151")
    ap = argparse.ArgumentParser(description="Bic Camera 商品頁校準")
    ap.add_argument("item_id", nargs="?", default=default_id)
    args = ap.parse_args()
    url = PRODUCT_URL.format(id=args.item_id)
    mon = BicCameraMonitor()

    print(f"=== 商品頁 ===\n  {url}\n")
    print("=== 1) robots.txt ===")
    try:
        mon.ensure_allowed(url)
        if mon.robots_checked:
            print("  ✅ robots.txt 允許抓取這個商品頁")
        else:
            print("  ⚠️ 讀不到 robots.txt(暫時放行);如果下面也連不上,多半是網路問題")
    except BicFetchError as exc:
        print(f"  ❌ {exc}")
        return 2

    print("\n=== 2) 抓頁面 ===")
    try:
        resp = requests.get(url, headers=_headers(), timeout=20)
    except requests.RequestException as exc:
        print(f"  ❌ 連線失敗:{exc}")
        return 2
    print(f"  HTTP {resp.status_code},{len(resp.text):,} 字元")
    if resp.status_code != 200:
        print("  ❌ 不是 200。403/429 代表被防機器人機制擋住;在家用網路仍被擋的話,把這段貼回來。")
        return 2

    state = BicCameraMonitor.parse_page(resp.text)
    print("\n=== 3) 判讀 ===")
    if state.blocked:
        print("  ❌ 收到的是防機器人頁面,不是商品頁。")
        return 2
    print(f"  JSON-LD availability : {state.ld_availability or '(頁面沒有)'}")
    print(f"  商品名稱(JSON-LD)  : {state.name or '(頁面沒有)'}")
    print(f"  價格                 : {f'¥{state.price:,}' if state.price else '(抓不到)'}")
    print(f"  判斷依據             : {state.source or '(無)'}")
    print("  命中的關鍵字:")
    for m in state.matches or ["  (沒有命中任何關鍵字)"]:
        print(f"    - {m}")

    print(f"\n=== 最後判定:{_MODE_LABEL[state.mode]}  {state.status_text} ===")
    print("\n請把以上整段貼回來。也請告訴我:你用瀏覽器打開這個網址,實際看到的狀態是什麼"
          "(例如「予約受付中」按鈕、「販売を終了しました」…),我會比對判定是否正確。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
