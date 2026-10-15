"""健康警示 + 日本模式整合測試(Bic 預購通知、平台分工、樂天 CX-20 門檻)。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run  # noqa: E402
from alerts import qualifies  # noqa: E402
from calendar_db import ON_SALE, Calendar, Change, EventRow  # noqa: E402
from config import SETTINGS, TARGETS, Target  # noqa: E402
from health import HealthTracker  # noqa: E402
from monitors.base import ProductSnapshot  # noqa: E402
from notify import format_target_alert  # noqa: E402

NOW = 1_800_000_000


class TempCal:
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.cal = Calendar(self.path)

    def tearDown(self):
        self.cal.close()
        os.remove(self.path)


class HealthTrackerTest(TempCal, unittest.TestCase):
    def test_warns_once_after_threshold_then_recovers_once(self):
        h = HealthTracker(self.cal, threshold=3)
        self.assertIsNone(h.update("biccamera", "HTTP 403"))
        self.assertIsNone(h.update("biccamera", "HTTP 403"))
        warn = h.update("biccamera", "HTTP 403")
        self.assertIn("⚠️", warn)
        self.assertIn("ビックカメラ", warn)
        self.assertIn("HTTP 403", warn)
        self.assertIsNone(h.update("biccamera", "HTTP 403"))        # 不重複警示
        self.assertIn("✅", h.update("biccamera", None))              # 恢復一次
        self.assertIsNone(h.update("biccamera", None))

    def test_single_blip_does_not_warn(self):
        h = HealthTracker(self.cal, threshold=3)
        h.update("biccamera", "timeout")
        self.assertIsNone(h.update("biccamera", None))               # 沒警示過,恢復也不通知
        self.assertIsNone(h.update("biccamera", "timeout"))          # 計數已歸零

    def test_state_survives_restart(self):
        HealthTracker(self.cal, threshold=2).update("rakuten_jp", "x")
        self.assertIsNotNone(HealthTracker(self.cal, threshold=2).update("rakuten_jp", "x"))

    def test_platforms_are_independent(self):
        h = HealthTracker(self.cal, threshold=2)
        h.update("biccamera", "x")
        self.assertIsNone(h.update("rakuten_jp", "x"))


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return True

    def notify_change(self, change):
        self.sent.append(f"[change] {change.event.name}")

    def notify_target(self, change, target):
        self.sent.append(format_target_alert(change, target))


class FakeBic:
    platform = "biccamera"

    def __init__(self):
        self.rounds = []          # 每輪:(snapshots, error)
        self.last_error = None
        self.calls = 0

    def fetch(self, watches):
        self.calls += 1
        snaps, self.last_error = self.rounds.pop(0)
        return snaps


class Boom:
    def __init__(self, platform, method):
        self.platform = platform
        setattr(self, method, self._boom)

    def _boom(self, items):
        raise AssertionError(f"{self.platform} 不該被呼叫")


def bic(mode, status_text, price=5980):
    return ProductSnapshot(
        product_key="CX-20", platform="biccamera", item_id="15680151",
        name="BEYBLADE X CX-20 カスタマイズセットC",
        url="https://www.biccamera.com/bc/item/15680151/", price=price,
        available=mode in ("preorder", "instock"),
        raw={"status_text": status_text, "mode": mode},
    )


class RunIntegrationTest(TempCal, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._saved = (run.ITEM_MONITORS, run.DISCOVERY_MONITORS, SETTINGS.radar_platforms)
        self.bic = FakeBic()
        run.ITEM_MONITORS = [self.bic]
        run.DISCOVERY_MONITORS = []
        SETTINGS.radar_platforms = ()

    def tearDown(self):
        run.ITEM_MONITORS, run.DISCOVERY_MONITORS, SETTINGS.radar_platforms = self._saved
        super().tearDown()

    def rounds(self, n, notifier):
        return [run.run_once(self.cal, notifier, now=NOW + i * 60) for i in range(n)]

    def test_bic_preorder_opens_notifies_once(self):
        self.bic.rounds = [
            ([bic("unavailable", "予約受付前")], None),
            ([bic("preorder", "予約受付中")], None),
            ([bic("preorder", "予約受付中")], None),
        ]
        n = FakeNotifier()
        self.assertEqual(self.rounds(3, n), [0, 1, 0])
        msg = n.sent[0]
        self.assertIn("🎯【CX-20 可以預購了!】", msg)
        self.assertIn("原因:開放預購", msg)
        self.assertIn("狀態:予約受付中", msg)
        self.assertIn("店家:ビックカメラ.com", msg)
        self.assertIn("¥5,980", msg)
        self.assertIn("https://www.biccamera.com/bc/item/15680151/", msg)

    def test_already_open_on_first_check_notifies_immediately(self):
        self.bic.rounds = [([bic("preorder", "予約受付中")], None)]
        n = FakeNotifier()
        self.assertEqual(self.rounds(1, n), [1])

    def test_failures_send_one_health_warning(self):
        self.bic.rounds = [([], "HTTP 403")] * 4
        n = FakeNotifier()
        self.assertEqual(self.rounds(4, n), [0, 0, 0, 0])
        warnings = [s for s in n.sent if "監控失敗" in s]
        self.assertEqual(len(warnings), 1)

    def test_platform_switch(self):
        # 家裡電腦只跑 Bic:樂天不該被呼叫
        SETTINGS.radar_platforms = ("biccamera",)
        run.DISCOVERY_MONITORS = [Boom("rakuten_jp", "fetch_searches")]
        self.bic.rounds = [([bic("unavailable", "予約受付前")], None)]
        self.rounds(1, FakeNotifier())
        self.assertEqual(self.bic.calls, 1)

        # GitHub Actions 只跑樂天:Bic 不該被呼叫
        SETTINGS.radar_platforms = ("rakuten_jp",)
        run.ITEM_MONITORS = [Boom("biccamera", "fetch")]
        run.DISCOVERY_MONITORS = []
        self.rounds(1, FakeNotifier())


class Cx20TargetsTest(unittest.TestCase):
    def target(self, platform):
        return next(t for t in TARGETS if t.product_key == "CX-20" and platform in t.platforms)

    def test_bic_has_no_price_cap(self):
        t = self.target("biccamera")
        self.assertIsNone(t.max_price)
        self.assertTrue(qualifies(ON_SALE, None, t))      # 抓不到價格也照樣通知
        self.assertTrue(qualifies(ON_SALE, 99999, t))

    def test_rakuten_cap_is_7000(self):
        t = self.target("rakuten_jp")
        self.assertTrue(qualifies(ON_SALE, 6980, t))
        self.assertTrue(qualifies(ON_SALE, 7000, t))
        self.assertFalse(qualifies(ON_SALE, 7480, t))

    def test_capped_headline_unchanged(self):
        e = EventRow(product_key="CX-20", platform="rakuten_jp", item_id="s:1", name="CX-20",
                     url="u", price=6980, original_price=None, is_original_price=None, stock=None,
                     on_sale_ts=None, available=True, status="ON_SALE", first_seen_at=0,
                     last_updated_at=0, raw={"shop": "某店", "postage": "送料込"})
        msg = format_target_alert(Change(event=e, old_status=None, old_price=None), self.target("rakuten_jp"))
        self.assertIn("🎯【CX-20 有貨 ≤ ¥7,000】", msg)


if __name__ == "__main__":
    unittest.main()
