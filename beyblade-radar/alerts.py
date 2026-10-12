"""目標價通知:商品「從不符合變成符合」的那一刻才通知一次。

符合 = 有貨(ON_SALE / RESTOCKED)且 價格 ≤ Target.max_price。

用 calendar_db 回傳的 Change(帶 old_status / old_price)判斷「之前符不符合」,
不需要額外的資料表:
    - 第一次看到就已符合        → 通知
    - 一直符合                  → 不重複通知
    - 售罄後補貨回來且符合      → 通知
    - ¥6,000 降到 ¥4,800        → 通知
    - ¥4,800 → ¥4,900(仍符合)→ 不通知
"""

from __future__ import annotations

from typing import Optional

from calendar_db import ON_SALE, RESTOCKED, Change, EventRow
from config import Target

_IN_STOCK = (ON_SALE, RESTOCKED)


def qualifies(status: Optional[str], price: Optional[int], target: Target) -> bool:
    return status in _IN_STOCK and price is not None and price <= target.max_price


def target_for(event: EventRow, targets: list[Target]) -> Optional[Target]:
    for t in targets:
        if t.product_key == event.product_key and event.platform in t.platforms:
            return t
    return None


def is_targeted(platform: str, targets: list[Target]) -> bool:
    return any(platform in t.platforms for t in targets)


def select_alerts(changes: list[Change], targets: list[Target]) -> list[tuple[Change, Target]]:
    out: list[tuple[Change, Target]] = []
    for c in changes:
        t = target_for(c.event, targets)
        if t is None:
            continue
        now_ok = qualifies(c.event.status, c.event.price, t)
        was_ok = c.old_status is not None and qualifies(c.old_status, c.old_price, t)
        if now_ok and not was_ok:
            out.append((c, t))
    return out
