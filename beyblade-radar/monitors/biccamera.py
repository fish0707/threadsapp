"""ビックカメラ.com monitor —— 盯單一商品頁,一開放預購 / 有貨就要知道。

Bic Camera 沒有公開 API,只能讀商品頁(零售商自己的公開頁面 = 第一手來源;
依「來源分級」原則低頻讀公開事實,並遵守 robots.txt)。

⚠️ 只能從家用網路執行:Bic 的防機器人機制會擋雲端機房 IP(GitHub Actions 等),
   被擋時不會寫入假狀態,而是記錄錯誤、由 health.py 送「監控失敗」警示。
⚠️ 頁面結構無法在開發環境確認,請在家裡電腦跑 tools/biccamera_check.py 校準。

判斷順序:
    1. 頁面內嵌的 JSON-LD(schema.org Offer.availability)—— 最可靠
    2. 退回頁面文字關鍵字,「否定詞優先」(避免推薦區的「カートに入れる」誤判)
    3. 都判斷不出來 → 視為錯誤(可能改版),不寫入狀態
"""

from __future__ import annotations

import html as _html
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.robotparser import RobotFileParser

import requests

from config import SETTINGS, Watch
from monitors.base import ProductSnapshot

BASE_URL = "https://www.biccamera.com"
PRODUCT_URL = BASE_URL + "/bc/item/{id}/"
ROBOTS_URL = BASE_URL + "/robots.txt"

PREORDER = "preorder"
INSTOCK = "instock"
UNAVAILABLE = "unavailable"
UNKNOWN = "unknown"

# schema.org availability → (模式, 顯示用狀態)
_LD_AVAILABILITY = {
    "PREORDER": (PREORDER, "予約受付中"),
    "PRESALE": (PREORDER, "予約受付中"),
    "INSTOCK": (INSTOCK, "在庫あり"),
    "LIMITEDAVAILABILITY": (INSTOCK, "在庫わずか"),
    "BACKORDER": (INSTOCK, "お取り寄せ"),
    "OUTOFSTOCK": (UNAVAILABLE, "在庫なし"),
    "SOLDOUT": (UNAVAILABLE, "売り切れ"),
    "DISCONTINUED": (UNAVAILABLE, "販売終了"),
}

# 頁面文字規則(依序檢查,先命中先算)。「店舗在庫」是實體店庫存,不是網購,排除。
_TEXT_RULES: tuple[tuple[str, str, str], ...] = (
    # 否定:已結束 / 沒貨 / 還沒開始
    (UNAVAILABLE, r"販売を終了|販売終了", "販売終了"),
    (UNAVAILABLE, r"予約受付を終了|予約受付終了|予約の受付を終了", "予約受付終了"),
    (UNAVAILABLE, r"完売|売り切れ|売切れ|品切れ", "売り切れ"),
    (UNAVAILABLE, r"(?<!店舗)在庫なし", "在庫なし"),
    (UNAVAILABLE, r"予約受付前|予約開始前|近日予約受付", "予約受付前"),
    # 肯定:可預購
    (PREORDER, r"予約受付中|予約する|ご予約はこちら", "予約受付中"),
    # 肯定:有貨 / 可訂
    (INSTOCK, r"カートに入れる", "カートに入れる"),
    (INSTOCK, r"(?<!店舗)在庫あり", "在庫あり"),
    (INSTOCK, r"お取り寄せ", "お取り寄せ"),
)

_BLOCK_MARKERS = (
    "access denied", "reference #", "request unsuccessful", "pardon our interruption",
    "errors.edgesuite.net", "bot manager", "are you a robot",
)

_LD_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_PRICE_RES = (
    re.compile(r"([\d,]{3,})\s*円\s*[(（]\s*税込"),
    re.compile(r"[¥￥]\s*([\d,]{3,})"),
)


class BicFetchError(RuntimeError):
    pass


@dataclass
class PageState:
    """一次讀頁的判定結果(給 monitor 與校準工具共用)。"""

    mode: str                         # preorder | instock | unavailable | unknown
    status_text: str = ""             # 顯示用狀態(例:予約受付中)
    price: Optional[int] = None
    name: str = ""
    source: str = ""                  # "json-ld" | "text" | ""
    blocked: bool = False
    ld_availability: str = ""         # JSON-LD 原始值(校準用)
    matches: list[str] = field(default_factory=list)  # 命中的關鍵字與前後文(校準用)

    @property
    def orderable(self) -> bool:
        return self.mode in (PREORDER, INSTOCK)


class BicCameraMonitor:
    platform = "biccamera"

    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()
        self._robots: Optional[RobotFileParser] = None
        self.last_error: Optional[str] = None

    # --- 抓取 ---------------------------------------------------------------

    def fetch(self, watches: list[Watch]) -> list[ProductSnapshot]:
        out: list[ProductSnapshot] = []
        errors: list[str] = []
        for w in watches:
            if w.platform != self.platform or not w.item_id:
                continue
            try:
                out.append(self._fetch_one(w))
            except BicFetchError as exc:
                print(f"[biccamera] {w.item_id} 失敗: {exc}")
                errors.append(str(exc))
        self.last_error = errors[0] if errors else None
        return out

    def _fetch_one(self, w: Watch) -> ProductSnapshot:
        url = PRODUCT_URL.format(id=w.item_id)
        self.ensure_allowed(url)
        state = self.fetch_state(url)
        return self.to_snapshot(state, w)

    def fetch_state(self, url: str) -> PageState:
        """抓頁面並判定狀態;被擋、HTTP 錯誤、無法判定都丟 BicFetchError。"""
        try:
            resp = self._session.get(url, headers=_headers(), timeout=SETTINGS.http_timeout_sec)
        except requests.RequestException as exc:
            raise BicFetchError(f"連線失敗:{exc}") from None
        if resp.status_code != 200:
            raise BicFetchError(_status_message(resp.status_code))
        state = self.parse_page(resp.text)
        if state.blocked:
            raise BicFetchError("收到防機器人頁面,被 Bic 擋住了(雲端主機常見;家用網路通常正常)")
        if state.mode == UNKNOWN:
            raise BicFetchError("頁面狀態無法判斷(可能改版):請跑 tools/biccamera_check.py 校準")
        return state

    @property
    def robots_checked(self) -> bool:
        """robots.txt 是否已成功讀取(讀不到時 ensure_allowed 會暫時放行)。"""
        return self._robots is not None

    def ensure_allowed(self, url: str) -> None:
        """遵守 robots.txt;讀不到 robots(非 403/429)時放行並印警告。"""
        if self._robots is None:
            try:
                resp = self._session.get(ROBOTS_URL, headers=_headers(), timeout=SETTINGS.http_timeout_sec)
            except requests.RequestException as exc:
                print(f"[biccamera] 讀不到 robots.txt({exc}),本輪先放行")
                return
            if resp.status_code in (403, 429):
                raise BicFetchError(f"robots.txt {_status_message(resp.status_code)}")
            rp = RobotFileParser()
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp.parse([])  # 404 等:沒有規則 = 全部允許
            self._robots = rp
        if not self._robots.can_fetch("*", url):
            raise BicFetchError("robots.txt 不允許抓取這個網址,已停止(不會繞過)")

    # --- 解析(純函式,方便測試與校準) ---------------------------------------

    @staticmethod
    def parse_page(page: str) -> PageState:
        page = page or ""
        low = page.lower()

        product = _find_ld_product(page)
        name = str((product or {}).get("name") or "")
        offer = _first_offer(product) if product else {}
        price = _to_int(offer.get("price")) if offer else None
        ld_avail = str(offer.get("availability") or "") if offer else ""

        if not product and any(m in low for m in _BLOCK_MARKERS):
            return PageState(mode=UNKNOWN, blocked=True)

        text = _visible_text(page)
        matches = _keyword_matches(text)
        if price is None:
            price = _price_from_text(text)

        key = ld_avail.rsplit("/", 1)[-1].upper()
        if key in _LD_AVAILABILITY:
            mode, label = _LD_AVAILABILITY[key]
            return PageState(mode=mode, status_text=label, price=price, name=name,
                             source="json-ld", ld_availability=ld_avail, matches=matches)

        for mode, pattern, label in _TEXT_RULES:
            if re.search(pattern, text):
                return PageState(mode=mode, status_text=label, price=price, name=name,
                                 source="text", ld_availability=ld_avail, matches=matches)

        return PageState(mode=UNKNOWN, price=price, name=name, ld_availability=ld_avail,
                         matches=matches)

    @staticmethod
    def to_snapshot(state: PageState, w: Watch) -> ProductSnapshot:
        return ProductSnapshot(
            product_key=w.product_key,
            platform="biccamera",
            item_id=w.item_id,
            name=w.name or state.name or f"ビックカメラ {w.item_id}",
            url=PRODUCT_URL.format(id=w.item_id),
            price=state.price,
            original_price=w.original_price,
            stock=None,
            on_sale_ts=None,
            available=state.orderable,
            raw={"status_text": state.status_text, "mode": state.mode},
        )


# --- 小工具 -----------------------------------------------------------------

def _headers() -> dict:
    return {
        "User-Agent": SETTINGS.user_agent,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "ja,en;q=0.8",
    }


def _status_message(status: int) -> str:
    if status in (403, 429):
        return f"HTTP {status}:被 Bic 的防機器人機制擋住(雲端主機常見;家用網路通常正常)"
    if status == 404:
        return "HTTP 404:商品頁不存在(網址或商品碼錯了,或商品被下架)"
    return f"HTTP {status}"


def _visible_text(page: str) -> str:
    text = _SCRIPT_STYLE_RE.sub(" ", page)
    text = _TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", _html.unescape(text))


def _keyword_matches(text: str) -> list[str]:
    out = []
    for _, pattern, _label in _TEXT_RULES:
        for m in re.finditer(pattern, text):
            s, e = max(0, m.start() - 15), min(len(text), m.end() + 15)
            out.append(f"「{m.group(0)}」…{text[s:e].strip()}…")
            if len(out) >= 20:
                return out
    return out


def _price_from_text(text: str) -> Optional[int]:
    for rx in _PRICE_RES:
        m = rx.search(text)
        if m:
            return _to_int(m.group(1))
    return None


def _find_ld_product(page: str) -> Optional[dict]:
    for m in _LD_JSON_RE.finditer(page):
        try:
            block = json.loads(m.group(1).strip())
        except (ValueError, TypeError):
            continue
        for node in _flatten(block):
            t = node.get("@type")
            if t == "Product" or (isinstance(t, list) and "Product" in t):
                return node
    return None


def _flatten(block: Any):
    if isinstance(block, list):
        for item in block:
            yield from _flatten(item)
    elif isinstance(block, dict):
        graph = block.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _flatten(item)
        yield block


def _first_offer(product: dict) -> dict:
    offers = product.get("offers")
    if isinstance(offers, list):
        return offers[0] if offers and isinstance(offers[0], dict) else {}
    return offers if isinstance(offers, dict) else {}


def _to_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None
