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

# 判斷順序(實際 Bic 頁面校準後的結論,2026/10 使用者截圖):
#   不能買的時候「カートに入れる」按鈕「照樣存在、只是變灰色」,
#   所以絕不能看到這幾個字就當有貨 —— 要看按鈕本身可不可按。
#
# 1) 明確的狀態句(「…しました」):頁面直接宣告結束 → 不可下單
_STATUS_NEGATIVE: tuple[tuple[str, str], ...] = (
    (r"販売を終了しました|販売終了しました|販売終了商品", "販売終了"),
    (r"予約受付を終了しました|予約受付は終了|予約の受付を終了しました", "予約受付終了"),
    (r"完売しました|売り切れました", "売り切れ"),
)
# 2) 下單按鈕(購物車 / 預約):第一個按鈕的「可不可按」說了算
_ORDER_BUTTON_LABEL = re.compile(r"カートに入れる|予約する")
# 3) JSON-LD(見 _LD_AVAILABILITY)
# 4) 其餘文字線索(較弱;注意頁尾購買須知是固定文字,所以不用單獨的「品切れ」之類字眼)
#    「店舗在庫」是實體店庫存,不是網購,排除。
_TEXT_RULES: tuple[tuple[str, str, str], ...] = (
    (PREORDER, r"予約受付中|ご予約はこちら", "予約受付中"),
    (UNAVAILABLE, r"予約受付前|予約開始前|近日予約受付", "予約受付前"),
    (UNAVAILABLE, r"(?<!店舗)在庫なし|在庫切れ", "在庫なし"),
    (INSTOCK, r"(?<!店舗)在庫あり", "在庫あり"),
    (INSTOCK, r"お取り寄せ", "お取り寄せ"),
)
# 校準工具要列出的關鍵字(含按鈕文字,方便對照)
_CALIBRATION_KEYWORDS = (
    [p for p, _ in _STATUS_NEGATIVE] + [r"カートに入れる|予約する"] + [p for _, p, _ in _TEXT_RULES]
)

# 按鈕「不可按」的線索:disabled 屬性、aria-disabled、或 class 名稱
_DISABLED_ATTR_RE = re.compile(r"\sdisabled(?:\s|=|>|/)|aria-disabled\s*=\s*[\"']?true", re.IGNORECASE)
_DISABLED_CLASS_RE = re.compile(
    r"disable|inactive|soldout|sold[-_]out|nocart|no[-_]cart|unavailable|gr[ae]y|[-_]off\b",
    re.IGNORECASE,
)
_CAMEL_OFF_RE = re.compile(r"[a-z]Off\b")          # 例:btnCartOff
_CLASS_ATTR_RE = re.compile(r"class\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)
_CLICKABLE_START_RE = re.compile(r"<(button|a|input)\b", re.IGNORECASE)

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
# 售價:優先「価格 : 6,270円」,且前面不是「メーカー」(那是定價);再退回一般寫法。
_PRICE_RES = (
    re.compile(r"(?<!メーカー)価格\s*[:：]?\s*([\d,]{3,})\s*円"),
    re.compile(r"([\d,]{3,})\s*円\s*[(（]\s*税込"),
    re.compile(r"[¥￥]\s*([\d,]{3,})"),
)
_LIST_PRICE_RE = re.compile(r"メーカー価格\s*[:：]?\s*([\d,]{3,})\s*円")
_RELEASE_RE = re.compile(
    r"メーカー発売日\s*[:：]?\s*(\d{4}年\d{1,2}月(?:\d{1,2}日)?(?:上旬|中旬|下旬)?|\d{4}/\d{1,2}(?:/\d{1,2})?)"
)


class BicFetchError(RuntimeError):
    pass


@dataclass
class PageState:
    """一次讀頁的判定結果(給 monitor 與校準工具共用)。"""

    mode: str                         # preorder | instock | unavailable | unknown
    status_text: str = ""             # 顯示用狀態(例:予約受付中)
    price: Optional[int] = None       # 售價(Bic 的「価格」)
    list_price: Optional[int] = None  # 定價(「メーカー価格」)
    release: str = ""                 # 發售日(「メーカー発売日」)
    name: str = ""
    source: str = ""                  # "status" | "button" | "json-ld" | "text" | ""
    blocked: bool = False
    ld_availability: str = ""         # JSON-LD 原始值(校準用)
    matches: list[str] = field(default_factory=list)  # 命中的關鍵字與前後文(校準用)
    buttons: list[dict] = field(default_factory=list)  # 找到的下單按鈕與判定(校準用)

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

        no_script = _SCRIPT_STYLE_RE.sub(" ", page)   # JS 字串裡的「カートに入れる」不算
        text = _visible_text(page)
        if price is None:
            price = _price_from_text(text)
        list_m = _LIST_PRICE_RE.search(text)
        release_m = _RELEASE_RE.search(text)
        base = dict(
            price=price, name=name, ld_availability=ld_avail,
            list_price=_to_int(list_m.group(1)) if list_m else None,
            release=release_m.group(1) if release_m else "",
            matches=_keyword_matches(text), buttons=_order_buttons(no_script),
        )

        # 1) 頁面明確宣告結束
        for pattern, label in _STATUS_NEGATIVE:
            if re.search(pattern, text):
                return PageState(mode=UNAVAILABLE, status_text=label, source="status", **base)

        # 2) 第一個下單按鈕說了算(主商品的按鈕在推薦區之前)
        if base["buttons"]:
            first = base["buttons"][0]
            if not first["enabled"]:
                return PageState(mode=UNAVAILABLE, status_text="カートボタン無効(受付前/在庫なし)",
                                 source="button", **base)
            if first["label"] == "予約する" or "発売日以降" in text:
                return PageState(mode=PREORDER, status_text="予約受付中(発売日以降お届け)",
                                 source="button", **base)
            return PageState(mode=INSTOCK, status_text="在庫あり(カートに入れる)",
                             source="button", **base)

        # 3) JSON-LD
        key = ld_avail.rsplit("/", 1)[-1].upper()
        if key in _LD_AVAILABILITY:
            mode, label = _LD_AVAILABILITY[key]
            return PageState(mode=mode, status_text=label, source="json-ld", **base)

        # 4) 其餘文字線索
        for mode, pattern, label in _TEXT_RULES:
            if re.search(pattern, text):
                return PageState(mode=mode, status_text=label, source="text", **base)

        return PageState(mode=UNKNOWN, **base)

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
            raw={"status_text": state.status_text, "mode": state.mode,
                 **({"release": state.release} if state.release else {})},
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
    for pattern in _CALIBRATION_KEYWORDS:
        for m in re.finditer(pattern, text):
            s, e = max(0, m.start() - 15), min(len(text), m.end() + 15)
            out.append(f"「{m.group(0)}」…{text[s:e].strip()}…")
            if len(out) >= 20:
                return out
    return out


def _order_buttons(page: str) -> list[dict]:
    """找出頁面上的下單按鈕(依出現順序),判斷每個可不可按。

    每個按鈕取「它所在的可點元素(button / a / input)開始標籤」到按鈕文字為止的片段,
    檢查 disabled 屬性、aria-disabled、或 class 名稱。
    """
    out: list[dict] = []
    for m in _ORDER_BUTTON_LABEL.finditer(page):
        window_start = max(0, m.start() - 800)
        starts = list(_CLICKABLE_START_RE.finditer(page, window_start, m.start()))
        if not starts:
            continue                      # 不在可點元素裡(例如說明文字)→ 不是按鈕
        start = starts[-1].start()
        between = page[start:m.start()]
        if ">" not in between:            # 文字在標籤屬性裡(例 <input value="カートに入れる">)
            end = page.find(">", m.end())
            segment = page[start:end + 1 if end != -1 else m.end()]
        else:
            tag = starts[-1].group(1).lower()
            if tag == "input":
                continue                  # <input> 沒有內文;文字在它之後就不是它的標籤
            # 文字前面若已有該元素的結束標籤,代表文字不在這個按鈕裡
            if re.search(rf"</{tag}\s*>", between, re.IGNORECASE):
                continue
            segment = between
        reason = _disabled_reason(segment)
        out.append({
            "label": m.group(0),
            "enabled": reason is None,
            "reason": reason or "",
            "snippet": re.sub(r"\s+", " ", segment)[:200],
        })
    return out


def _disabled_reason(segment: str) -> Optional[str]:
    if _DISABLED_ATTR_RE.search(segment):
        return "disabled 屬性"
    for cls in _CLASS_ATTR_RE.findall(segment):
        if _DISABLED_CLASS_RE.search(cls) or _CAMEL_OFF_RE.search(cls):
            return f'class="{cls}"'
    return None


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
