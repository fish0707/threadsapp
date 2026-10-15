"""Bic Camera monitor 測試(餵 mock HTML,不打真實網站)。"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Watch  # noqa: E402
from monitors.biccamera import (  # noqa: E402
    INSTOCK, PREORDER, PRODUCT_URL, ROBOTS_URL, UNAVAILABLE, UNKNOWN, BicCameraMonitor,
)

WATCH = Watch(product_key="CX-20", platform="biccamera", item_id="15680151",
              name="BEYBLADE X CX-20 カスタマイズセットC")
URL = PRODUCT_URL.format(id="15680151")


def ld_page(availability, price="5980", body=""):
    ld = {
        "@context": "https://schema.org", "@type": "Product",
        "name": "ベイブレードX CX-20 カスタマイズセットC",
        "offers": {"@type": "Offer", "price": price, "priceCurrency": "JPY",
                   "availability": f"https://schema.org/{availability}"},
    }
    return (f'<html><head><script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}'
            f'</script></head><body>{body}</body></html>')


def text_page(body):
    return f"<html><head><title>CX-20</title></head><body>{body}</body></html>"


class ParseTest(unittest.TestCase):
    def test_jsonld_preorder(self):
        s = BicCameraMonitor.parse_page(ld_page("PreOrder"))
        self.assertEqual((s.mode, s.status_text, s.price, s.source), (PREORDER, "予約受付中", 5980, "json-ld"))
        self.assertTrue(s.orderable)

    def test_jsonld_instock_and_out_of_stock(self):
        self.assertEqual(BicCameraMonitor.parse_page(ld_page("InStock")).mode, INSTOCK)
        out = BicCameraMonitor.parse_page(ld_page("OutOfStock"))
        self.assertEqual(out.mode, UNAVAILABLE)
        self.assertFalse(out.orderable)

    def test_text_preorder_with_price(self):
        s = BicCameraMonitor.parse_page(text_page("<p>5,980円（税込）</p><button>予約受付中</button>"))
        self.assertEqual((s.mode, s.price, s.source), (PREORDER, 5980, "text"))

    def test_yen_sign_price(self):
        s = BicCameraMonitor.parse_page(text_page("<span>¥5,980</span><a>カートに入れる</a>"))
        self.assertEqual((s.mode, s.price), (INSTOCK, 5980))

    def test_negative_wins_over_recommendation_cart_button(self):
        # 推薦區的別的商品有「カートに入れる」,但本商品已「販売を終了」→ 不可下單
        s = BicCameraMonitor.parse_page(text_page(
            "<div>この商品は販売を終了しました</div><div class='reco'><a>カートに入れる</a></div>"))
        self.assertEqual(s.mode, UNAVAILABLE)

    def test_reservation_closed_is_not_preorder(self):
        s = BicCameraMonitor.parse_page(text_page("<p>予約受付を終了しました</p>"))
        self.assertEqual((s.mode, s.status_text), (UNAVAILABLE, "予約受付終了"))

    def test_store_stock_is_not_online_stock(self):
        # 「店舗在庫あり / なし」是實體店庫存,不能當網購判斷依據
        self.assertEqual(BicCameraMonitor.parse_page(text_page("<p>店舗在庫あり</p>")).mode, UNKNOWN)
        self.assertEqual(BicCameraMonitor.parse_page(text_page("<p>店舗在庫なし</p>")).mode, UNKNOWN)

    def test_keywords_inside_script_are_ignored(self):
        s = BicCameraMonitor.parse_page(text_page('<script>var s="予約受付中";</script><p>商品情報</p>'))
        self.assertEqual(s.mode, UNKNOWN)

    def test_block_page_detected(self):
        s = BicCameraMonitor.parse_page("<html><body><h1>Access Denied</h1>Reference #18.abc</body></html>")
        self.assertTrue(s.blocked)

    def test_calibration_matches_have_context(self):
        s = BicCameraMonitor.parse_page(text_page("<p>この商品は 予約受付中 です</p>"))
        self.assertTrue(any("予約受付中" in m for m in s.matches))

    def test_snapshot_mapping(self):
        snap = BicCameraMonitor.to_snapshot(BicCameraMonitor.parse_page(ld_page("PreOrder")), WATCH)
        self.assertEqual((snap.platform, snap.product_key, snap.item_id), ("biccamera", "CX-20", "15680151"))
        self.assertTrue(snap.available)
        self.assertEqual(snap.url, URL)
        self.assertEqual(snap.raw, {"status_text": "予約受付中", "mode": PREORDER})


class FakeResponse:
    def __init__(self, status, text=""):
        self.status_code = status
        self.text = text


class FakeSession:
    def __init__(self, routes):
        self.routes = routes          # url -> FakeResponse
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        return self.routes[url]


ROBOTS_OK = FakeResponse(200, "User-agent: *\nDisallow: /bc/cart/\n")


class FetchTest(unittest.TestCase):
    def fetch(self, routes):
        sess = FakeSession(routes)
        mon = BicCameraMonitor(session=sess)
        return mon, sess, mon.fetch([WATCH])

    def test_preorder_page(self):
        mon, sess, snaps = self.fetch({ROBOTS_URL: ROBOTS_OK, URL: FakeResponse(200, ld_page("PreOrder"))})
        self.assertEqual(len(snaps), 1)
        self.assertTrue(snaps[0].available)
        self.assertIsNone(mon.last_error)

    def test_blocked_403_records_error_and_no_snapshot(self):
        mon, sess, snaps = self.fetch({ROBOTS_URL: ROBOTS_OK, URL: FakeResponse(403, "denied")})
        self.assertEqual(snaps, [])
        self.assertIn("403", mon.last_error)
        self.assertIn("防機器人", mon.last_error)

    def test_challenge_page_with_200_is_an_error(self):
        page = "<html><body>Access Denied. Reference #1.2.3</body></html>"
        mon, sess, snaps = self.fetch({ROBOTS_URL: ROBOTS_OK, URL: FakeResponse(200, page)})
        self.assertEqual(snaps, [])
        self.assertIn("擋住", mon.last_error)

    def test_unknown_page_is_an_error_not_a_fake_state(self):
        # 判斷不出來時不能寫成「無貨」,否則修好後會誤報「補貨」
        mon, sess, snaps = self.fetch({ROBOTS_URL: ROBOTS_OK, URL: FakeResponse(200, text_page("<p>商品情報</p>"))})
        self.assertEqual(snaps, [])
        self.assertIn("無法判斷", mon.last_error)

    def test_robots_disallow_stops_before_fetching_page(self):
        robots = FakeResponse(200, "User-agent: *\nDisallow: /bc/item/\n")
        mon, sess, snaps = self.fetch({ROBOTS_URL: robots, URL: FakeResponse(200, ld_page("PreOrder"))})
        self.assertEqual(snaps, [])
        self.assertNotIn(URL, sess.calls)
        self.assertIn("robots.txt", mon.last_error)

    def test_robots_404_means_allowed(self):
        mon, sess, snaps = self.fetch({ROBOTS_URL: FakeResponse(404), URL: FakeResponse(200, ld_page("InStock"))})
        self.assertEqual(len(snaps), 1)

    def test_robots_403_is_treated_as_blocked(self):
        mon, sess, snaps = self.fetch({ROBOTS_URL: FakeResponse(403), URL: FakeResponse(200, ld_page("InStock"))})
        self.assertEqual(snaps, [])
        self.assertNotIn(URL, sess.calls)
        self.assertIn("403", mon.last_error)

    def test_robots_fetched_once(self):
        sess = FakeSession({ROBOTS_URL: ROBOTS_OK, URL: FakeResponse(200, ld_page("PreOrder"))})
        mon = BicCameraMonitor(session=sess)
        mon.fetch([WATCH])
        mon.fetch([WATCH])
        self.assertEqual(sess.calls.count(ROBOTS_URL), 1)
        self.assertEqual(sess.calls.count(URL), 2)

    def test_error_clears_after_recovery(self):
        sess = FakeSession({ROBOTS_URL: ROBOTS_OK, URL: FakeResponse(403)})
        mon = BicCameraMonitor(session=sess)
        mon.fetch([WATCH])
        self.assertIsNotNone(mon.last_error)
        sess.routes[URL] = FakeResponse(200, ld_page("PreOrder"))
        mon.fetch([WATCH])
        self.assertIsNone(mon.last_error)


if __name__ == "__main__":
    unittest.main()
