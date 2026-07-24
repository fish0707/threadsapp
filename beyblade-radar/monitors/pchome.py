"""PChome 24h monitor(階段二骨架)。

PChome 有公開 JSON API,實作時可用:
    搜尋:  https://ecshweb.pchome.com.tw/search/v3.3/all/results?q=beyblade&page=1&sort=sale/dc
    單品:  https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/{id}&fields=Id,Name,Price,Qty,ButtonType
只抓公開事實資料、低頻。此檔目前為骨架:回傳空清單,不影響主迴圈。
上線時把 _fetch_one 補齊即可(結構刻意對齊 momo.py 方便照抄)。
"""

from __future__ import annotations

from typing import Optional

import requests

from config import Watch
from monitors.base import ProductSnapshot

SEARCH_URL = "https://ecshweb.pchome.com.tw/search/v3.3/all/results"
PROD_URL = "https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/{id}&fields=Id,Name,Price,Qty,ButtonType"


class PChomeMonitor:
    platform = "pchome"

    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()

    def fetch(self, watches: list[Watch]) -> list[ProductSnapshot]:
        # TODO(階段二):打 PROD_URL 取單品即時價量,套 ProductSnapshot。
        # 目前回空清單,讓 run.py 能在只做 momo MVP 時正常運作。
        return []
