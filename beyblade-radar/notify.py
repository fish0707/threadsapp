"""通知層 —— 把事件變更推給你自己(Telegram / Discord)。

LINE Notify 已停用,故走 Telegram bot 或 Discord webhook(擇一或都設)。
金鑰走環境變數(見 config.py / .env.example),不硬編碼。
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

import requests

from calendar_db import (
    ANNOUNCED, IMMINENT, ON_SALE, SOLD_OUT, RESTOCKED, Change, EventRow,
)
from config import SETTINGS, Target

_STATUS_LABEL = {
    ANNOUNCED: "🗓 預告",
    IMMINENT: "⏰ 即將開賣",
    ON_SALE: "🟢 已上架/開賣",
    SOLD_OUT: "🔴 售罄",
    RESTOCKED: "🟢 原價補貨",
}

# 以日圓計價的平台(其餘維持新台幣)。
_JPY_PLATFORMS = {"rakuten_jp", "biccamera"}

_PLATFORM_LABEL = {"rakuten_jp": "樂天市場", "biccamera": "ビックカメラ.com"}


def money(platform: str, amount: int) -> str:
    """依平台幣別格式化金額:樂天 → ¥4,580;台灣通路 → NT$390。"""
    if platform in _JPY_PLATFORMS:
        return f"¥{amount:,}"
    return f"NT${amount:,}"


class Notifier:
    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()

    # --- 對外 ---------------------------------------------------------------

    def send(self, text: str) -> bool:
        """送純文字到所有已設定的管道。回傳「是否至少送出一個管道」。"""
        sent = False
        if SETTINGS.has_telegram:
            sent = self._send_telegram(text) or sent
        if SETTINGS.has_discord:
            sent = self._send_discord(text) or sent
        if not (SETTINGS.has_telegram or SETTINGS.has_discord):
            print("[notify] 未設定任何通知管道,略過。訊息內容:\n" + text)
        return sent

    def notify_change(self, change: Change) -> bool:
        return self.send(format_change(change))

    def notify_target(self, change: Change, target: Target) -> bool:
        return self.send(format_target_alert(change, target))

    # --- 各管道實作 ---------------------------------------------------------

    def _send_telegram(self, text: str) -> bool:
        url = f"https://api.telegram.org/bot{SETTINGS.telegram_bot_token}/sendMessage"
        try:
            resp = self._session.post(
                url,
                json={
                    "chat_id": SETTINGS.telegram_chat_id,
                    "text": text,
                    "disable_web_page_preview": False,
                },
                timeout=SETTINGS.http_timeout_sec,
            )
            resp.raise_for_status()
            return True
        except requests.RequestException as exc:
            print(f"[notify] Telegram 送出失敗: {exc}")
            return False

    def _send_discord(self, text: str) -> bool:
        try:
            resp = self._session.post(
                SETTINGS.discord_webhook_url,
                json={"content": text[:1900]},  # Discord 單則上限 2000 字
                timeout=SETTINGS.http_timeout_sec,
            )
            resp.raise_for_status()
            return True
        except requests.RequestException as exc:
            print(f"[notify] Discord 送出失敗: {exc}")
            return False


# --- 訊息格式化(可獨立測試) ----------------------------------------------

def format_change(change: Change) -> str:
    e = change.event
    lines: list[str] = []

    # 標題:最想被看到的訊號優先。
    if change.is_original_price_restock:
        headline = "🔥【原價補貨】"
    elif change.is_restock:
        headline = "🟢【補貨】"
    elif change.is_imminent:
        headline = "⏰【即將開賣】"
    elif change.is_new and e.available:
        headline = "🆕【新商品上架】"
    elif change.is_new:
        headline = "🆕【新情報】"
    else:
        headline = "🔔【狀態更新】"
    lines.append(f"{headline} {e.name}")

    # 狀態列
    label = _STATUS_LABEL.get(e.status, e.status)
    if change.status_changed and not change.is_new:
        old_label = _STATUS_LABEL.get(change.old_status or "", change.old_status)
        lines.append(f"狀態:{old_label} → {label}")
    else:
        lines.append(f"狀態:{label}")

    # 價格 / 原價旗標
    if e.price is not None:
        price_line = f"售價:{money(e.platform, e.price)}"
        if e.is_original_price is True:
            price_line += "（原價✅）"
        elif e.is_original_price is False:
            price_line += "（高於原價⚠️）"
        if change.price_dropped and change.old_price is not None:
            price_line += f"（↓ 原 {money(e.platform, change.old_price)}）"
        lines.append(price_line)

    if e.stock is not None:
        lines.append(f"庫存:{e.stock}")

    if e.on_sale_ts is not None:
        lines.append(f"開賣:{_fmt_ts(e.on_sale_ts)}")

    lines.append(f"平台:{e.platform}")
    if e.url:
        lines.append(e.url)

    return "\n".join(lines)


def format_target_alert(change: Change, target: Target) -> str:
    """目標通知:限價(如 UX-15 有貨且 ≤ ¥5,000)或不限價(如 Bic CX-20 開放預購)。"""
    e = change.event
    p = e.platform
    raw = e.raw or {}
    preorder = raw.get("mode") == "preorder"

    if target.max_price is None:
        headline = f"🎯【{target.product_key} {'可以預購了' if preorder else '有貨了'}!】"
    else:
        headline = f"🎯【{target.product_key} 有貨 ≤ {money(p, target.max_price)}】"
    lines = [headline, e.name]

    if change.is_restock or change.old_status == SOLD_OUT:
        reason = "重新開放預購" if preorder else "售罄後補貨"
    elif change.price_dropped and change.old_price is not None:
        reason = f"降價 {money(p, change.old_price)} → {money(p, e.price)}"
    elif change.is_new:
        reason = "新發現"
    else:
        reason = "開放預購" if preorder else "轉為有貨"
    lines.append(f"原因:{reason}")

    if raw.get("status_text"):
        lines.append(f"狀態:{raw['status_text']}")

    label = _PLATFORM_LABEL.get(p, p)
    shop = raw.get("shop")
    lines.append(f"店家:{shop}({label})" if shop else f"店家:{label}")

    if e.price is not None:
        price_line = f"售價:{money(p, e.price)}"
        postage = (e.raw or {}).get("postage")
        if postage:
            price_line += f"({postage})"
        if target.list_price:
            price_line += f"・官方定價 {money(p, target.list_price)}"
        lines.append(price_line)

    if e.url:
        lines.append(e.url)
    return "\n".join(lines)


def _fmt_ts(ts: int) -> str:
    """unix 秒 → 台灣時間字串(UTC+8)。"""
    tz = _dt.timezone(_dt.timedelta(hours=8))
    return _dt.datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M")
