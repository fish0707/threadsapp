"""樂天 monitor 測試(餵 mock 回應,不打真實 API)。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SETTINGS, Search  # noqa: E402
from monitors.rakuten_jp import (  # noqa: E402
    API_URL, RakutenAPIError, RakutenJPMonitor, alias_tokens, matches_product,
    model_from_keyword, normalize,
)

SEARCH = Search(platform="rakuten_jp", keyword="UX-15 シャークスケイルデッキセット")


def item(**kw) -> dict:
    base = {
        "itemCode": "joshin:10001",
        "itemName": "タカラトミー BEYBLADE X UX-15 シャークスケイルデッキセット",
        "itemPrice": 4580,
        "itemUrl": "https://item.rakuten.co.jp/joshin/10001/",
        "availability": 1,
        "shopName": "ジョーシン楽天市場店",
        "postageFlag": 1,
    }
    base.update(kw)
    return base


class FakeResponse:
    def __init__(self, status: int, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return self.responses.pop(0)


class ParseTest(unittest.TestCase):
    def test_flat_format_v2(self):
        snaps = RakutenJPMonitor.parse_response({"Items": [item()]}, SEARCH)
        self.assertEqual(len(snaps), 1)
        s = snaps[0]
        self.assertEqual(s.platform, "rakuten_jp")
        self.assertEqual(s.product_key, "UX-15")
        self.assertEqual(s.item_id, "joshin:10001")
        self.assertEqual(s.price, 4580)
        self.assertTrue(s.available)
        self.assertEqual(s.raw, {"shop": "ジョーシン楽天市場店", "postage": "送料別"})

    def test_wrapped_format_v1(self):
        snaps = RakutenJPMonitor.parse_response({"Items": [{"Item": item(postageFlag=0)}]}, SEARCH)
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps[0].raw["postage"], "送料込")

    def test_full_width_model_code_matches(self):
        snaps = RakutenJPMonitor.parse_response(
            {"Items": [item(itemName="ベイブレードＸ ＵＸ１５ デッキセット")]}, SEARCH
        )
        self.assertEqual(len(snaps), 1)

    def test_alias_without_model_code_matches(self):
        snaps = RakutenJPMonitor.parse_response(
            {"Items": [item(itemName="ベイブレードX シャークスケイルデッキセット 新品")]}, SEARCH
        )
        self.assertEqual(len(snaps), 1)

    def test_other_models_rejected(self):
        names = [
            "ベイブレードX UX-150 何か別の商品",       # UX-150 不是 UX-15
            "ベイブレードX UX-14 スコーピオスピア",     # 別的型號
            "ベイブレードX BX-15 何か",                 # 前綴不同
        ]
        data = {"Items": [item(itemCode=f"s:{i}", itemName=n) for i, n in enumerate(names)]}
        self.assertEqual(RakutenJPMonitor.parse_response(data, SEARCH), [])

    def test_used_and_single_parts_excluded(self):
        names = [
            "【中古】UX-15 シャークスケイルデッキセット",
            "UX-15 シャークスケイル4-50UF 単品",
            "UX-15 より ティラノロア のみ",
            "UX-15 開封品",
            "UX-15 シャークスケイルデッキセット バラ売り",
        ]
        data = {"Items": [item(itemCode=f"s:{i}", itemName=n) for i, n in enumerate(names)]}
        self.assertEqual(RakutenJPMonitor.parse_response(data, SEARCH), [])

    def test_unopened_is_not_excluded(self):
        # 「未開封」= 全新,不能被排除字誤殺
        snaps = RakutenJPMonitor.parse_response(
            {"Items": [item(itemName="【新品・未開封】UX-15 シャークスケイルデッキセット")]}, SEARCH
        )
        self.assertEqual(len(snaps), 1)

    def test_out_of_stock_flag(self):
        snaps = RakutenJPMonitor.parse_response({"Items": [item(availability=0)]}, SEARCH)
        self.assertFalse(snaps[0].available)

    def test_missing_fields_do_not_crash(self):
        data = {"Items": [{}, {"itemName": "UX-15"}, None, "junk", item(itemPrice=None)]}
        snaps = RakutenJPMonitor.parse_response(data, SEARCH)
        self.assertEqual(len(snaps), 1)          # 只有最後一筆有 itemCode + 名稱
        self.assertIsNone(snaps[0].price)
        self.assertEqual(RakutenJPMonitor.parse_response({}, SEARCH), [])
        self.assertEqual(RakutenJPMonitor.parse_response(None, SEARCH), [])

    def test_helpers(self):
        self.assertEqual(normalize("ＵＸ－１５"), "UX-15")
        self.assertEqual(model_from_keyword("UX-15 シャークスケイルデッキセット"), "UX-15")
        self.assertEqual(model_from_keyword("ux15"), "UX-15")
        self.assertEqual(alias_tokens("UX-15 シャークスケイルデッキセット"), ["シャークスケイルデッキセット"])
        self.assertTrue(matches_product("UX ‐ 15", "UX-15", []))
        self.assertFalse(matches_product("AUX-15", "UX-15", []))


class RequestTest(unittest.TestCase):
    KEYS = ("rakuten_app_id", "rakuten_access_key", "rakuten_referer", "rakuten_max_pages")

    def setUp(self):
        self._saved = {k: getattr(SETTINGS, k) for k in self.KEYS}
        SETTINGS.rakuten_app_id = "APPID123456"
        SETTINGS.rakuten_access_key = "SECRETKEY987"
        SETTINGS.rakuten_referer = "https://fish0707.github.io/radar/"
        SETTINGS.rakuten_max_pages = 3

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(SETTINGS, k, v)

    def test_sends_auth_referer_and_params(self):
        sess = FakeSession([FakeResponse(200, {"Items": [item()], "pageCount": 1})])
        snaps = RakutenJPMonitor(session=sess, sleep=lambda s: None).fetch_searches([SEARCH])
        self.assertEqual(len(snaps), 1)
        call = sess.calls[0]
        self.assertEqual(call["url"], API_URL)
        self.assertEqual(call["params"]["applicationId"], "APPID123456")
        self.assertEqual(call["params"]["accessKey"], "SECRETKEY987")
        self.assertEqual(call["params"]["availability"], 0)
        self.assertEqual(call["params"]["formatVersion"], 2)
        self.assertEqual(call["params"]["NGKeyword"], "中古")
        self.assertEqual(call["headers"]["Referer"], "https://fish0707.github.io/radar/")
        self.assertEqual(call["headers"]["Origin"], "https://fish0707.github.io")

    def test_pagination_stops_at_page_count_and_dedups(self):
        sleeps = []
        sess = FakeSession([
            FakeResponse(200, {"Items": [item(itemCode="a:1")], "pageCount": 2}),
            FakeResponse(200, {"Items": [item(itemCode="a:1"), item(itemCode="b:2")], "pageCount": 2}),
        ])
        snaps = RakutenJPMonitor(session=sess, sleep=sleeps.append).fetch_searches([SEARCH])
        self.assertEqual(len(sess.calls), 2)                     # pageCount=2,不打第 3 頁
        self.assertEqual([c["params"]["page"] for c in sess.calls], [1, 2])
        self.assertEqual(sleeps, [1.0])                          # 頁間有停頓
        self.assertEqual(sorted(s.item_id for s in snaps), ["a:1", "b:2"])

    def test_error_is_reported_without_leaking_keys(self):
        sess = FakeSession([FakeResponse(403, {
            "error": "HTTP_REFERRER_NOT_ALLOWED",
            "error_description": "applicationId=APPID123456 accessKey=SECRETKEY987",
        })])
        mon = RakutenJPMonitor(session=sess, sleep=lambda s: None)
        with self.assertRaises(RakutenAPIError) as ctx:
            mon.request_page("UX-15", 1)
        msg = str(ctx.exception)
        self.assertEqual(ctx.exception.status, 403)
        self.assertIn("HTTP_REFERRER_NOT_ALLOWED", msg)
        self.assertIn("Referer", msg)                 # 附白話提示
        self.assertNotIn("APPID123456", msg)
        self.assertNotIn("SECRETKEY987", msg)

    def test_scope_error_gets_scope_hint_not_referer_hint(self):
        # 真實回應(2026/10 GitHub Actions log)
        sess = FakeSession([FakeResponse(403, {
            "errorCode": 403, "errorMessage": "REQUESTED_SCOPES_NOT_ALLOWED",
        })])
        with self.assertRaises(RakutenAPIError) as ctx:
            RakutenJPMonitor(session=sess, sleep=lambda s: None).request_page("UX-15", 1)
        msg = str(ctx.exception)
        self.assertIn("REQUESTED_SCOPES_NOT_ALLOWED", msg)
        self.assertIn("API Access Scopes", msg)
        self.assertIn("Rakuten Ichiba API", msg)
        self.assertNotIn("Referer 不符", msg)
        self.assertNotIn("{", msg)            # 讀出 errorMessage,不是整包 dict

    def test_referer_error_gets_referer_hint(self):
        sess = FakeSession([FakeResponse(403, {"errorCode": 403, "errorMessage": "HTTP_REFERRER_NOT_ALLOWED"})])
        with self.assertRaises(RakutenAPIError) as ctx:
            RakutenJPMonitor(session=sess, sleep=lambda s: None).request_page("UX-15", 1)
        self.assertIn("Referer 不符", str(ctx.exception))

    def test_redacts_url_encoded_keys(self):
        from monitors.rakuten_jp import redact
        SETTINGS.rakuten_access_key = "ab+c/d=="
        leaked = "GET /x?accessKey=ab%2Bc%2Fd%3D%3D failed; raw=ab+c/d=="
        out = redact(leaked)
        self.assertNotIn("ab%2Bc%2Fd%3D%3D", out)
        self.assertNotIn("ab+c/d==", out)

    def test_error_does_not_break_the_round(self):
        # fetch_searches 會吞掉單一關鍵字的錯誤,不拖垮整輪
        sess = FakeSession([FakeResponse(429, {"error": "too_many_requests"})])
        snaps = RakutenJPMonitor(session=sess, sleep=lambda s: None).fetch_searches([SEARCH])
        self.assertEqual(snaps, [])

    def test_unconfigured_skips_without_request(self):
        SETTINGS.rakuten_app_id = ""
        sess = FakeSession([])
        snaps = RakutenJPMonitor(session=sess, sleep=lambda s: None).fetch_searches([SEARCH])
        self.assertEqual(snaps, [])
        self.assertEqual(sess.calls, [])


if __name__ == "__main__":
    unittest.main()
