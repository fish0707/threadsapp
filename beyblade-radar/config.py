"""
Beyblade X 原價開賣雷達 — 設定檔

- 監控清單:要盯哪些商品(商品碼 / 關鍵字 / 平台 / 已知原價)。
- 執行參數:輪詢間隔、「即將開賣」提前提醒的分鐘數。
- 金鑰一律走環境變數 / .env,不硬編碼(見 .env.example)。

原則:此檔只放「設定資料」,不放邏輯。上線前用 DevTools 再確認 momo 端點/參數,
別把易變的 API 細節寫死在這裡。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

# --- .env 載入(可選,沒裝 python-dotenv 也能跑,直接讀 os.environ) --------
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:  # pragma: no cover - dotenv 為選配
    pass


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# --- 監控目標 ---------------------------------------------------------------

@dataclass
class Watch:
    """一筆監控目標。

    product_key: 跨平台同款合併用的正規化鍵(例如 "UX-04")。同一顆陀螺在
                 momo / PChome / Funbox 上請用「相同」的 product_key,行事曆
                 才能把它們併成一個事件。
    platform:    "momo" | "pchome" | "funbox"
    item_id:     平台商品識別碼。momo 為 goodsCode;PChome 為 prod id
                 (如 "DGAJ8T-A900AVFV7");funbox 直接填「商品頁完整網址」。
    keyword:     搜尋用關鍵字(給搜尋型 monitor 抓新品用,單品監控可留空)。
    original_price: 已知「原價 / 建議售價」(NT$)。用來判斷觀測到的售價是否為原價。
                    不填則 is_original_price 會是 None(未知)。
    name:        人類可讀名稱(通知/草稿顯示用)。
    """

    product_key: str
    platform: str
    item_id: str = ""
    keyword: str = ""
    original_price: Optional[int] = None
    name: str = ""


# 監控清單 —— 這裡放你要盯的 Beyblade X 商品。
# 範例:UX-04(計畫書驗證用;商品碼與開賣時間以上線前實測為準)。
# 目前專注日本市場,台灣通路先停用(程式碼保留,要恢復把下面範例取消註解即可)。
WATCHES: list[Watch] = [
    # ビックカメラ.com:CX-20 カスタマイズセットC(預購型商品)。
    # 只能從家用網路抓(Bic 會擋雲端機房 IP),所以只在家裡電腦執行(RADAR_PLATFORMS=biccamera)。
    Watch(
        product_key="CX-20",
        platform="biccamera",
        item_id="15680151",
        name="BEYBLADE X CX-20 カスタマイズセットC",
    ),
    # Watch(
    #     product_key="UX-04",
    #     platform="momo",
    #     item_id="15462754",
    #     original_price=390,
    #     name="Beyblade X UX-04(範例)",
    # ),
    # 跨平台同款:用「相同 product_key」串起來,行事曆會自動合併。
    # 打開下面兩筆(填真實 id / 網址)即可讓 PChome、Funbox 一起盯 UX-04。
    #
    # Watch(
    #     product_key="UX-04",
    #     platform="pchome",
    #     item_id="DGAJ8T-XXXXXXXX",   # PChome prod id
    #     original_price=390,
    #     name="Beyblade X UX-04",
    # ),
    # Watch(
    #     product_key="UX-04",
    #     platform="funbox",
    #     item_id="https://funbox 商品頁完整網址",  # funbox 用網址當 item_id
    #     original_price=390,
    #     name="Beyblade X UX-04",
    # ),
]


# --- 搜尋 / 發現式監控目標 --------------------------------------------------

@dataclass
class Search:
    """一筆「掃描搜尋頁抓新品」的目標。

    跟 Watch 不同:Watch 是盯「已知商品碼」;Search 是拿關鍵字去掃某商城的
    搜尋/分類頁,把「以前沒看過的 Beyblade X 商品」當新上架通知你。
    首次掃描會先建立基準線(不通知),之後才通知真正的新品。
    """

    platform: str            # "rakuten_jp" | "eslite" | …
    keyword: str             # 搜尋關鍵字
    name: str = ""           # 這組掃描的人類可讀標籤


# 掃描清單 —— 這裡放「要在哪些商城、用什麼關鍵字掃」。
# 目前盯日本樂天的 UX-15 與 CX-20C(台灣誠品掃描先停用)。
SEARCHES: list[Search] = [
    Search(
        platform="rakuten_jp",
        keyword="UX-15 シャークスケイルデッキセット",
        name="樂天 UX-15",
    ),
    Search(
        platform="rakuten_jp",
        keyword="CX-20 カスタマイズセットC",
        name="樂天 CX-20C",
    ),
    # Search(platform="eslite", keyword="beyblade", name="誠品 Beyblade X 掃描"),
]


# --- 目標條件(價格門檻通知) ------------------------------------------------

@dataclass
class Target:
    """「這個商品可以下單(有貨或可預購)、且價格 ≤ max_price 時通知我」。

    只在商品「從不符合變成符合」的那一刻通知一次(alerts.select_alerts),
    持續符合不會重複推播。門檻只看商品標價,不含運費。
    max_price=None 表示不限價:只要能下單就通知。
    """

    product_key: str                  # 例 "UX-15"
    max_price: Optional[int]          # 價格上限(含),單位依平台幣別(日本平台為日圓);None = 不限
    list_price: Optional[int] = None  # 官方定價,通知裡當參考
    platforms: tuple[str, ...] = ("rakuten_jp",)  # 套用這個目標的平台


TARGETS: list[Target] = [
    # BEYBLADE X UX-15 シャークスケイルデッキセット:官方定價 ¥4,200(2025/8/9 發售)
    Target(product_key="UX-15", max_price=5000, list_price=4200),
    # CX-20 カスタマイズセットC:メーカー価格 ¥6,600(Bic 售 ¥6,270,2026 年 11 月發售)
    # Bic Camera:一開放預購 / 有貨就通知(Bic 賣定價以下,不設上限)
    Target(product_key="CX-20", max_price=None, list_price=6600, platforms=("biccamera",)),
    # 樂天各店:≤ ¥7,000(≈ 定價 +6%,定價店家會通知,三倍轉賣價不會)
    Target(product_key="CX-20", max_price=7000, list_price=6600, platforms=("rakuten_jp",)),
]

# 品名含這些字就排除:中古品、拆賣單顆(停產品常見把整套拆開賣)。
# 注意不要放「開封」:會誤殺「未開封」(=全新)這種正是我們要的商品。
EXCLUDE_WORDS: tuple[str, ...] = (
    "中古", "ジャンク", "開封済", "開封品", "単品", "バラ", "のみ", "USED",
)


# --- 執行參數 ---------------------------------------------------------------

@dataclass
class Settings:
    # 輪詢間隔(秒)。低頻,尊重對方站台;預設 5 分鐘。
    poll_interval_sec: int = field(default_factory=lambda: _env_int("POLL_INTERVAL_SEC", 300))
    # 「即將開賣」提前多少分鐘提醒(進 IMMINENT 狀態)。
    imminent_lead_min: int = field(default_factory=lambda: _env_int("IMMINENT_LEAD_MIN", 30))
    # SQLite 檔路徑。
    db_path: str = field(default_factory=lambda: _env("RADAR_DB_PATH", "radar.db"))
    # HTTP 請求逾時(秒)。
    http_timeout_sec: int = field(default_factory=lambda: _env_int("HTTP_TIMEOUT_SEC", 15))
    # 送出的 User-Agent(擬一般瀏覽器,低頻使用)。
    user_agent: str = field(
        default_factory=lambda: _env(
            "RADAR_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        )
    )

    # --- 通知管道(擇一或都填) ---
    telegram_bot_token: str = field(default_factory=lambda: _env("TELEGRAM_BOT_TOKEN"))
    telegram_chat_id: str = field(default_factory=lambda: _env("TELEGRAM_CHAT_ID"))
    discord_webhook_url: str = field(default_factory=lambda: _env("DISCORD_WEBHOOK_URL"))

    # --- 分潤 ---
    # 蝦皮分潤 ID(過審後填);未填時 draft 只放純導流連結。
    shopee_affiliate_id: str = field(default_factory=lambda: _env("SHOPEE_AFFILIATE_ID"))

    # --- 樂天市場 API(2026 新規格:applicationId + accessKey + Referer) ---
    rakuten_app_id: str = field(default_factory=lambda: _env("RAKUTEN_APP_ID"))
    rakuten_access_key: str = field(default_factory=lambda: _env("RAKUTEN_ACCESS_KEY"))
    # 必須與樂天後台「許可された Web サイト」登記的網址一致,否則 403。
    rakuten_referer: str = field(default_factory=lambda: _env("RAKUTEN_REFERER"))
    # 每個關鍵字最多抓幾頁(每頁 30 筆),頁間會間隔 1 秒避免 429。
    rakuten_max_pages: int = field(default_factory=lambda: _env_int("RAKUTEN_MAX_PAGES", 2))

    # --- 執行分工 ---
    # 只執行這些平台的 monitor(逗號分隔);留空 = 全部。
    # 家裡電腦:biccamera(Bic 擋雲端 IP);GitHub Actions:rakuten_jp。
    radar_platforms: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            p.strip() for p in _env("RADAR_PLATFORMS").split(",") if p.strip()
        )
    )
    # 連續失敗幾輪才送一次「監控失敗」警示(避免偶發斷線就吵你)。
    health_fail_threshold: int = field(default_factory=lambda: _env_int("HEALTH_FAIL_THRESHOLD", 3))

    def platform_enabled(self, platform: str) -> bool:
        return not self.radar_platforms or platform in self.radar_platforms

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def has_discord(self) -> bool:
        return bool(self.discord_webhook_url)

    @property
    def has_rakuten(self) -> bool:
        return bool(self.rakuten_app_id and self.rakuten_access_key)


SETTINGS = Settings()
