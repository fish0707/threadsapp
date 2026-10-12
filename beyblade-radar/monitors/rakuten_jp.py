"""樂天市場(日本)monitor —— 用官方 Ichiba Item Search API 掃指定商品。

走官方 API,不爬網頁。一支 adapter 涵蓋所有在樂天開店的日本零售商。

⚠️ 2026 新規格(取自改版後的實作紀錄,首次實連請用 tools/rakuten_check.py 校準):
    端點:  https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701
           (舊 app.rakuten.co.jp 已於 2026/5 停用)
    認證:  applicationId + accessKey(2026/2 後需重新註冊,舊 ID 失效)
    Referer:必須與樂天後台「許可された Web サイト」一致,否則 403
             (HTTP_REFERRER_MISSING / HTTP_REFERRER_NOT_ALLOWED)
    限流:  約 1 req/sec,超過回 429

刻意用 availability=0(有貨、無貨都回傳)並自己讀每筆的庫存旗標:
若只抓有貨的,商品售罄時會從結果「消失」,補貨回來時資料庫以為它一直都在,
就偵測不到補貨。全抓才能看到「無貨 → 有貨」的轉換。
"""

from __future__ import annotations

import re
import time
import unicodedata
from typing import Any, Optional
from urllib.parse import quote, quote_plus, urlparse

import requests

from config import EXCLUDE_WORDS, SETTINGS, Search
from monitors.base import ProductSnapshot
from monitors.discovery import DiscoveryMonitor

API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
HITS_PER_PAGE = 30
PAGE_PAUSE_SEC = 1.0

# 各種「橫線」寫法:半形 -、全形經 NFKC 後已轉半形,另補常見的 Unicode 連字號與長音符號。
_DASHES = "-‐‑‒–—―ーｰ"
_MODEL_IN_KEYWORD = re.compile(r"([A-Z]{2,3})\s*[" + _DASHES + r"]?\s*(\d{1,3})")

_POSTAGE = {0: "送料込", 1: "送料別"}

# 先依樂天回的錯誤碼(errorMessage 等)判斷,比單看 HTTP 狀態碼準:
# 同樣是 403,可能是 scope 沒開,也可能是 Referer 不符。
_MESSAGE_HINTS = (
    ("REQUESTED_SCOPES_NOT_ALLOWED",
     "這個應用程式沒有樂天市場 API 的權限:到 Rakuten Developers → Your Apps → 你的應用程式"
     " → API Access Scopes 勾選「Rakuten Ichiba API」並存檔(若顯示審核中,需等樂天核准)"),
    ("HTTP_REFERRER",
     "Referer 不符:RAKUTEN_REFERER 的網域要列在樂天後台「Allowed websites」裡"),
)

_STATUS_HINTS = {
    400: "參數錯誤(常見:缺 accessKey,或 applicationId 是 2026/2 以前的舊 ID)",
    401: "認證失敗:applicationId / accessKey 不正確",
    403: "權限被拒:檢查樂天後台的 API Access Scopes 與 Allowed websites",
    404: "端點不存在:API 版本或路徑可能又改了,請對照樂天官方文件",
    429: "請求太頻繁(限流),降低頻率或減少 RAKUTEN_MAX_PAGES",
}


def error_hint(status: int, detail: str) -> str:
    upper = (detail or "").upper()
    for code, hint in _MESSAGE_HINTS:
        if code in upper:
            return hint
    return _STATUS_HINTS.get(status, "")


class RakutenAPIError(RuntimeError):
    def __init__(self, status: int, detail: str):
        self.status = status
        hint = error_hint(status, detail)
        super().__init__(f"HTTP {status}: {detail}" + (f" —— {hint}" if hint else ""))


class RakutenJPMonitor(DiscoveryMonitor):
    platform = "rakuten_jp"

    def __init__(self, session: Optional[requests.Session] = None, sleep=time.sleep):
        super().__init__(session)
        self._sleep = sleep
        self._warned_unconfigured = False

    # --- 抓取 ---------------------------------------------------------------

    def _search(self, search: Search) -> list[ProductSnapshot]:
        if not SETTINGS.has_rakuten:
            if not self._warned_unconfigured:
                print("[rakuten_jp] 未設定 RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY,略過。")
                self._warned_unconfigured = True
            return []

        snaps: list[ProductSnapshot] = []
        seen: set[str] = set()
        max_pages = max(1, SETTINGS.rakuten_max_pages)
        for page in range(1, max_pages + 1):
            if page > 1:
                self._sleep(PAGE_PAUSE_SEC)
            data = self.request_page(search.keyword, page)
            for s in self.parse_response(data, search):
                if s.item_id not in seen:
                    seen.add(s.item_id)
                    snaps.append(s)
            page_count = _to_int(data.get("pageCount")) or 1
            if page >= page_count:
                break
        return snaps

    def request_page(self, keyword: str, page: int) -> dict:
        """打一頁 API,回傳 JSON。非 200 時丟出已遮蔽金鑰的 RakutenAPIError。"""
        try:
            resp = self._session.get(
                API_URL,
                params=build_params(keyword, page),
                headers=build_headers(),
                timeout=SETTINGS.http_timeout_sec,
            )
        except requests.RequestException as exc:
            # requests 的錯誤訊息會含完整 URL(含金鑰),一律遮蔽後再往外丟。
            raise RakutenAPIError(0, redact(str(exc))) from None

        if resp.status_code != 200:
            raise RakutenAPIError(resp.status_code, redact(_error_detail(resp)))
        try:
            return resp.json()
        except ValueError:
            raise RakutenAPIError(resp.status_code, "回應不是 JSON") from None

    # --- 解析(純函式,方便單元測試) -----------------------------------------

    @classmethod
    def parse_response(cls, data: Any, search: Search) -> list[ProductSnapshot]:
        if not isinstance(data, dict):
            return []
        items = data.get("Items") or data.get("items") or []
        model = model_from_keyword(search.keyword)
        aliases = alias_tokens(search.keyword)
        out: list[ProductSnapshot] = []
        for raw in items:
            # formatVersion=1 每筆包在 {"Item": {...}};formatVersion=2 是扁平物件。
            item = raw.get("Item") if isinstance(raw, dict) and isinstance(raw.get("Item"), dict) else raw
            snap = cls.to_snapshot(item, search, model, aliases)
            if snap is not None:
                out.append(snap)
        return out

    @staticmethod
    def to_snapshot(
        item: Any,
        search: Search,
        model: Optional[str],
        aliases: list[str],
    ) -> Optional[ProductSnapshot]:
        if not isinstance(item, dict):
            return None
        item_code = str(item.get("itemCode") or "").strip()
        name = str(item.get("itemName") or "").strip()
        if not item_code or not name:
            return None

        norm = normalize(name)
        if is_excluded(norm):
            return None
        if not matches_product(norm, model, aliases):
            return None

        postage = _POSTAGE.get(_to_int(item.get("postageFlag")), "")
        return ProductSnapshot(
            product_key=model or search.keyword,
            platform="rakuten_jp",
            item_id=item_code,
            name=name,
            url=str(item.get("itemUrl") or ""),
            price=_to_int(item.get("itemPrice")),
            original_price=None,
            stock=None,                       # API 只給有貨/無貨,不給數量
            on_sale_ts=None,
            available=_to_int(item.get("availability")) == 1,
            raw={"shop": str(item.get("shopName") or ""), "postage": postage},
        )


# --- 請求組裝 ---------------------------------------------------------------

def build_params(keyword: str, page: int) -> dict:
    return {
        "applicationId": SETTINGS.rakuten_app_id,
        "accessKey": SETTINGS.rakuten_access_key,
        "keyword": keyword,
        "NGKeyword": "中古",
        "availability": 0,       # 有貨無貨都回傳,自己判斷(見檔頭說明)
        "hits": HITS_PER_PAGE,
        "page": page,
        "formatVersion": 2,
    }


def build_headers() -> dict:
    headers = {"User-Agent": SETTINGS.user_agent, "Accept": "application/json"}
    referer = SETTINGS.rakuten_referer
    if referer:
        headers["Referer"] = referer
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
    return headers


def redact(text: str) -> str:
    """把 applicationId / accessKey 從字串裡遮掉(避免金鑰進到 log)。"""
    for secret in (SETTINGS.rakuten_app_id, SETTINGS.rakuten_access_key):
        if not secret:
            continue
        # 錯誤訊息裡的 URL 是編碼過的(如 + → %2B),原文與編碼形式都要遮。
        for form in {secret, quote_plus(secret), quote(secret, safe="")}:
            text = text.replace(form, "***")
    return text


def _error_detail(resp: requests.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return (resp.text or "")[:200]
    if isinstance(body, dict):
        # 新規格回 {"errorCode": 403, "errorMessage": "..."};舊規格回 error / error_description。
        keys = ("errorMessage", "error", "error_description", "errors")
        parts = [str(body.get(k)) for k in keys if body.get(k)]
        if parts:
            return " / ".join(parts)[:300]
    return str(body)[:200]


# --- 品名比對 ---------------------------------------------------------------

def normalize(text: str) -> str:
    """NFKC 正規化(全形英數 →半形,如「ＵＸ１５」→「UX15」)並轉大寫。"""
    return unicodedata.normalize("NFKC", text or "").upper()


def model_from_keyword(keyword: str) -> Optional[str]:
    m = _MODEL_IN_KEYWORD.search(normalize(keyword))
    return f"{m.group(1)}-{m.group(2)}" if m else None


def alias_tokens(keyword: str) -> list[str]:
    """關鍵字裡型號以外、夠長的詞(如「シャークスケイルデッキセット」)當別名比對。"""
    norm = normalize(keyword)
    norm = _MODEL_IN_KEYWORD.sub(" ", norm)
    return [t for t in norm.split() if len(t) >= 6]


def matches_product(norm_name: str, model: Optional[str], aliases: list[str]) -> bool:
    if model:
        prefix, digits = model.split("-")
        pat = re.compile(
            r"(?<![A-Z])" + prefix + r"\s*[" + _DASHES + r"]?\s*0*" + digits + r"(?!\d)"
        )
        if pat.search(norm_name):
            return True
    return any(a in norm_name for a in aliases)


def is_excluded(norm_name: str) -> bool:
    return any(normalize(w) in norm_name for w in EXCLUDE_WORDS)


def _to_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None
