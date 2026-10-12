"""目標價通知測試:只在「進入條件」那一刻通知 + 通知格式 + run_once 端到端。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run  # noqa: E402
from alerts import qualifies, select_alerts  # noqa: E402
from calendar_db import ON_SALE, SOLD_OUT, Calendar, Change, EventRow  # noqa: E402
from config import Target  # noqa: E402
from monitors.base import ProductSnapshot  # noqa: E402
from notify import format_change, format_target_alert  # noqa: E402

TARGET = Target(product_key="UX-15", max_price=5000, list_price=4200)
NOW = 1_800_000_000


def snap(price, available=True, item_id="joshin:1", platform="rakuten_jp"):
    return ProductSnapshot(
        product_key="UX-15", platform=platform, item_id=item_id,
        name="BEYBLADE X UX-15 シャークスケイルデッキセット",
        url=f"https://item.rakuten.co.jp/{item_id.replace(':', '/')}/",
        price=price, available=available,
        raw={"shop": "ジョーシン楽天市場店", "postage": "送料別"},
    )


class SelectAlertsTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.cal = Calendar(self.path)
        self.t = NOW

    def tearDown(self):
        self.cal.close()
        os.remove(self.path)

    def step(self, *snaps) -> list:
        self.t += 600
        changes = self.cal.upsert_many(list(snaps), now=self.t)
        return select_alerts(changes, [TARGET])

    def test_first_seen_qualifying_alerts_once(self):
        self.assertEqual(len(self.step(snap(4580))), 1)
        self.assertEqual(self.step(snap(4580)), [])          # 持續符合 → 不重複

    def test_price_drop_into_range_alerts(self):
        self.assertEqual(self.step(snap(6240)), [])          # 有貨但太貴
        alerts = self.step(snap(4580))                        # 降進門檻
        self.assertEqual(len(alerts), 1)
        self.assertTrue(alerts[0][0].price_dropped)

    def test_small_moves_inside_range_do_not_realert(self):
        self.step(snap(4800))
        self.assertEqual(self.step(snap(4900)), [])          # 漲但仍 ≤5000
        self.assertEqual(self.step(snap(4700)), [])          # 降但之前就符合

    def test_rise_out_then_back_in_alerts_again(self):
        self.step(snap(4800))
        self.assertEqual(self.step(snap(5500)), [])          # 漲出門檻
        self.assertEqual(len(self.step(snap(4800))), 1)      # 再降回來 → 通知

    def test_restock_under_price_alerts(self):
        self.step(snap(4800))
        self.assertEqual(self.step(snap(4800, available=False)), [])   # 售罄
        alerts = self.step(snap(4800))                                  # 補貨
        self.assertEqual(len(alerts), 1)
        self.assertEqual(self.step(snap(4800)), [])                     # RESTOCKED→ON_SALE 不再通知

    def test_out_of_stock_cheap_listing_alerts_when_in_stock(self):
        self.assertEqual(self.step(snap(4500, available=False)), [])
        self.assertEqual(len(self.step(snap(4500))), 1)

    def test_above_threshold_never_alerts(self):
        self.assertEqual(self.step(snap(5001)), [])
        self.assertEqual(self.step(snap(5001, available=False)), [])
        self.assertEqual(self.step(snap(5001)), [])

    def test_exact_threshold_counts(self):
        self.assertEqual(len(self.step(snap(5000))), 1)

    def test_other_platform_ignored(self):
        self.assertEqual(self.step(snap(100, platform="momo")), [])

    def test_qualifies(self):
        self.assertTrue(qualifies(ON_SALE, 5000, TARGET))
        self.assertFalse(qualifies(SOLD_OUT, 100, TARGET))
        self.assertFalse(qualifies(ON_SALE, None, TARGET))


def event(**kw) -> EventRow:
    base = dict(
        product_key="UX-15", platform="rakuten_jp", item_id="joshin:1",
        name="BEYBLADE X UX-15 シャークスケイルデッキセット",
        url="https://item.rakuten.co.jp/joshin/1/", price=4580, original_price=None,
        is_original_price=None, stock=None, on_sale_ts=None, available=True,
        status="ON_SALE", first_seen_at=0, last_updated_at=0, id=1,
        raw={"shop": "ジョーシン楽天市場店", "postage": "送料別"},
    )
    base.update(kw)
    return EventRow(**base)


class FormatTest(unittest.TestCase):
    def test_target_alert_message(self):
        msg = format_target_alert(Change(event=event(), old_status=None, old_price=None), TARGET)
        self.assertIn("🎯【UX-15 有貨 ≤ ¥5,000】", msg)
        self.assertIn("店家:ジョーシン楽天市場店(樂天市場)", msg)
        self.assertIn("售價:¥4,580(送料別)・官方定價 ¥4,200", msg)
        self.assertIn("原因:新發現", msg)
        self.assertIn("https://item.rakuten.co.jp/joshin/1/", msg)
        self.assertNotIn("NT$", msg)

    def test_target_alert_reasons(self):
        drop = Change(event=event(), old_status="ON_SALE", old_price=6240)
        self.assertIn("原因:降價 ¥6,240 → ¥4,580", format_target_alert(drop, TARGET))
        restock = Change(event=event(status="RESTOCKED"), old_status="SOLD_OUT", old_price=4580)
        self.assertIn("原因:售罄後補貨", format_target_alert(restock, TARGET))

    def test_currency_by_platform(self):
        jp = format_change(Change(event=event(), old_status=None, old_price=None))
        tw = format_change(Change(event=event(platform="momo", price=390), old_status=None, old_price=None))
        self.assertIn("¥4,580", jp)
        self.assertIn("NT$390", tw)


class FakeMonitor:
    platform = "rakuten_jp"

    def __init__(self):
        self.rounds = []

    def fetch_searches(self, searches):
        return self.rounds.pop(0)


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def notify_change(self, change):
        self.sent.append(format_change(change))

    def notify_target(self, change, target):
        self.sent.append(format_target_alert(change, target))


class RunOnceTest(unittest.TestCase):
    """三輪模擬:¥6,240 有貨(不通知)→ ¥4,580(通知)→ 同價(不通知)。"""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.cal = Calendar(self.path)
        self._saved = (run.ITEM_MONITORS, run.DISCOVERY_MONITORS, run.TARGETS)
        self.mon = FakeMonitor()
        run.ITEM_MONITORS = []
        run.DISCOVERY_MONITORS = [self.mon]
        run.TARGETS = [TARGET]

    def tearDown(self):
        run.ITEM_MONITORS, run.DISCOVERY_MONITORS, run.TARGETS = self._saved
        self.cal.close()
        os.remove(self.path)

    def test_three_rounds(self):
        self.mon.rounds = [[snap(6240)], [snap(4580)], [snap(4580)]]
        notifier = FakeNotifier()
        counts = [run.run_once(self.cal, notifier, now=NOW + i * 600) for i in range(3)]
        self.assertEqual(counts, [0, 1, 0])
        self.assertEqual(len(notifier.sent), 1)
        self.assertIn("降價 ¥6,240 → ¥4,580", notifier.sent[0])


if __name__ == "__main__":
    unittest.main()
