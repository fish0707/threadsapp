"""樂天 API 校準工具 —— 拿到金鑰後先跑這支,確認端點、認證、Referer 都對。

樂天 2026/2 改版後,端點、accessKey、Referer 規則都變了。雷達程式是依改版後的
實作紀錄寫的,第一次連線前用這支確認真實回應長怎樣。

用法(在 beyblade-radar/ 目錄下,.env 已填 RAKUTEN_*):
    python tools/rakuten_check.py
    python tools/rakuten_check.py --keyword "UX-15"     # 換關鍵字試

輸出的金鑰一律遮蔽,可以直接整段貼回來。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alerts import qualifies  # noqa: E402
from calendar_db import ON_SALE  # noqa: E402
from config import SEARCHES, SETTINGS, TARGETS, Search  # noqa: E402
from monitors.rakuten_jp import (  # noqa: E402
    API_URL, RakutenAPIError, RakutenJPMonitor, build_headers, redact,
)


def main() -> int:
    default_kw = next((s.keyword for s in SEARCHES if s.platform == "rakuten_jp"), "UX-15")
    ap = argparse.ArgumentParser(description="樂天 API 連線校準")
    ap.add_argument("--keyword", default=default_kw)
    args = ap.parse_args()

    print("=== 設定檢查 ===")
    print(f"  端點        : {API_URL}")
    print(f"  applicationId: {'已設定' if SETTINGS.rakuten_app_id else '❌ 未設定 RAKUTEN_APP_ID'}")
    print(f"  accessKey    : {'已設定' if SETTINGS.rakuten_access_key else '❌ 未設定 RAKUTEN_ACCESS_KEY'}")
    print(f"  Referer      : {SETTINGS.rakuten_referer or '❌ 未設定 RAKUTEN_REFERER(幾乎一定會 403)'}")
    print(f"  送出標頭     : {json.dumps({k: v for k, v in build_headers().items() if k != 'User-Agent'}, ensure_ascii=False)}")
    if not SETTINGS.has_rakuten:
        print("\n請先在 .env 填好 RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY / RAKUTEN_REFERER。")
        return 1

    print(f"\n=== 搜尋「{args.keyword}」第 1 頁 ===")
    mon = RakutenJPMonitor()
    try:
        data = mon.request_page(args.keyword, 1)
    except RakutenAPIError as exc:
        print(f"  ❌ {exc}")
        print("\n把上面這段貼回來即可(金鑰已遮蔽)。")
        return 2

    print("  ✅ HTTP 200")
    print(f"  頂層欄位   : {sorted(data.keys())}")
    print(f"  總筆數/頁數: count={data.get('count')} pageCount={data.get('pageCount')}")
    items = data.get("Items") or data.get("items") or []
    print(f"  本頁筆數   : {len(items)}")
    if items:
        first = items[0].get("Item", items[0]) if isinstance(items[0], dict) else items[0]
        if isinstance(first, dict):
            print(f"  第一筆欄位 : {sorted(first.keys())}")
            preview = {k: first.get(k) for k in (
                "itemName", "itemPrice", "itemCode", "availability", "shopName", "postageFlag", "itemUrl",
            )}
            print("  第一筆內容 :", redact(json.dumps(preview, ensure_ascii=False, indent=2)))

    search = Search(platform="rakuten_jp", keyword=args.keyword)
    snaps = RakutenJPMonitor.parse_response(data, search)
    print(f"\n=== 雷達解析結果:{len(snaps)} 筆通過品名/排除字篩選 ===")
    target = next((t for t in TARGETS if "rakuten_jp" in t.platforms), None)
    for s in snaps:
        stock = "有貨" if s.available else "無貨"
        hit = ""
        if target and qualifies(ON_SALE if s.available else None, s.price, target):
            hit = f"  🎯 符合 ≤ ¥{target.max_price:,}"
        price = f"¥{s.price:,}" if s.price is not None else "?"
        print(f"  - [{stock}] {price:>8}  {s.raw.get('shop', '')}  {s.name[:40]}{hit}")
    if items and not snaps:
        print("  (API 有回資料但全被篩掉 —— 把上面的第一筆內容貼回來,我調整比對規則)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
