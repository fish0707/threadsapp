"""Funbox 官網 monitor(階段二骨架 —— 原價第一手,優先做穩)。

Funbox 官網為 SHOPLINE 站型,商品頁通常可取到 JSON(SHOPLINE 有商品 API/內嵌 JSON)。
原價開賣多半這裡最早,是最值得盯的第一手來源。此檔為骨架:回傳空清單。
上線時補齊 fetch:抓商品頁 → 解析價格/庫存/上架狀態 → 套 ProductSnapshot。
低頻、遵守 robots.txt、不繞登入牆。
"""

from __future__ import annotations

from typing import Optional

import requests

from config import Watch
from monitors.base import ProductSnapshot


class FunboxMonitor:
    platform = "funbox"

    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()

    def fetch(self, watches: list[Watch]) -> list[ProductSnapshot]:
        # TODO(階段二):抓 Funbox SHOPLINE 商品 JSON/HTML,套 ProductSnapshot。
        return []
