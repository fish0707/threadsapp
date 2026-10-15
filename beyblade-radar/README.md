# Beyblade X 原價開賣情報・個人雷達

> **目前狀態:日本模式** —— Bic Camera CX-20C 一開放預購就通知(家裡電腦,每 60 秒);樂天 UX-15 ≤ ¥5,000、CX-20C ≤ ¥7,000 有貨就通知(GitHub Actions,每 10 分鐘)。

自動盯各購物平台,在 **Beyblade X「原價」商品**開賣 / 上架 / **補貨**時**通知你自己**(Telegram / Discord),
並生成帶**蝦皮分潤連結**的貼文草稿,由你審核後手動貼到 Threads / IG / FB。

> **個人雷達,不公開帳號、不自動發文**。系統只通知你、發文你自己貼。
> 不做社群自動發文 API(省掉審核最嚴的部分)。

## 🇯🇵 日本模式(目前啟用)

| 盯什麼 | 條件 | 在哪跑 | 多快 |
|---|---|---|---|
| **Bic Camera** CX-20 カスタマイズセットC([商品頁](https://www.biccamera.com/bc/item/15680151/)) | 可預購或有貨(不限價) | **家裡電腦** | 每 60 秒 |
| **樂天** UX-15 シャークスケイルデッキセット | 有貨且 ≤ ¥5,000 | GitHub Actions | 每 10 分鐘 |
| **樂天** CX-20 カスタマイズセットC | 有貨且 ≤ ¥7,000 | GitHub Actions | 每 10 分鐘 |

用 `RADAR_PLATFORMS` 分工(家裡電腦 `biccamera`、雲端 `rakuten_jp`),兩邊不會重複通知。
任何一邊**連續失敗 3 輪**(被擋、改版、斷線)會送一則 ⚠️「監控失敗」,恢復時送 ✅。

### 🏠 家裡電腦執行(Bic Camera)

Bic Camera 沒有 API,只能讀商品頁,而且它的防機器人機制會擋雲端機房 IP(GitHub Actions 就是),
所以這部分要用**家用網路**跑。雷達會遵守 Bic 的 robots.txt。

1. 安裝 [Python 3.11 以上](https://www.python.org/downloads/)(安裝畫面**勾選「Add python.exe to PATH」**)。
2. GitHub repo 頁面 → **Code → Download ZIP** → 解壓縮,進到 `beyblade-radar` 資料夾。
3. 在資料夾空白處按右鍵 →「在終端機中開啟」,執行:`python -m pip install -r requirements.txt`
4. 把 `.env.example` 複製一份改名為 `.env`,用記事本填:
   ```
   TELEGRAM_BOT_TOKEN=(你的 beyblade bot token)
   TELEGRAM_CHAT_ID=(你的 chat id)
   RADAR_PLATFORMS=biccamera
   POLL_INTERVAL_SEC=60
   ```
5. `python run.py --test-notify` → Telegram 應收到測試訊息。
6. `python tools/biccamera_check.py` → 確認抓得到、判斷正確(**第一次請把輸出貼回來校準**)。
7. **雙擊 `start_radar.bat`** 開始常駐(視窗開著就在監控;意外結束會自動重啟)。
8. 讓它一直跑:Windows 設定 → 系統 → 電源 →「睡眠」設為**永不**;
   開機自動啟動:按 `Win+R` 輸入 `shell:startup`,把 `start_radar.bat` 的**捷徑**放進去。

> Mac:步驟相同,第 7 步改在終端機執行 `caffeinate -i python3 run.py`(防止休眠)。

---

### 樂天:UX-15 有貨且 ≤ ¥5,000 就通知

盯 **BEYBLADE X UX-15 シャークスケイルデッキセット**
(官方定價 ¥4,200,2025/8/9 發售)。當**全新品、有庫存、商品標價 ≤ ¥5,000**(不含運費)
時推 Telegram,而且同一筆商品**只在「進入條件」那一刻通知一次**:

| 情況 | 通知? |
|---|---|
| 第一次看到就已有貨且 ≤ ¥5,000 | ✅ |
| 從 ¥6,240 降到 ¥4,580 | ✅ |
| 售罄後補貨,且 ≤ ¥5,000 | ✅ |
| 持續符合(¥4,800 → ¥4,900) | ❌ 不重複 |
| 有貨但 > ¥5,000、或中古 / 拆賣單顆 | ❌ |

門檻與商品在 `config.py` 的 `TARGETS` / `SEARCHES` / `EXCLUDE_WORDS` 調整。

### 資料來源:樂天市場官方 API

一支 adapter(`monitors/rakuten_jp.py`)涵蓋所有在樂天開店的日本零售商(ジョーシン、
ビック、EDION、玩具店…)。走官方 API,不爬網頁。

**設定步驟:**

1. 到 [Rakuten Developers](https://webservice.rakuten.co.jp/) 註冊新應用程式
   (2026/2 改版後**舊 ID 全部失效**,一定要新註冊)。
2. 「許可された Web サイト」填一個你掌控的固定網址,例如 GitHub Pages
   `https://fish0707.github.io/`。**這個網址就是 `RAKUTEN_REFERER`**,兩邊不一致會 403。
3. 取得 `applicationId` 與 `accessKey`,填進 `.env`(本機)與 GitHub Secrets(雲端)。
4. 校準:`python tools/rakuten_check.py` —— 會印出連線結果、第一筆商品欄位、
   以及哪些商品符合門檻。**輸出的金鑰已遮蔽,可直接貼給別人看。**
5. `python run.py --once` 跑一輪;雲端用 GitHub Actions(見下方「部署」)。

> ⚠️ 樂天 2026 新規格(`openapi.rakuten.co.jp`、accessKey、Referer 檢查)取自改版後的
> 實作紀錄,首次連線請先跑第 4 步確認。常見錯誤:400 = 缺 accessKey / 舊 ID;
> 403 `REQUESTED_SCOPES_NOT_ALLOWED` = 應用程式沒勾「Rakuten Ichiba API」scope(或尚待核准);
> 403 `HTTP_REFERRER_*` = Referer 網域不在 Allowed websites;429 = 太頻繁。

### 沒有 API 的通路:手動設定(不寫程式)

| 通路 | 為什麼不自動 | 替代做法 |
|---|---|---|
| Amazon JP | PA-API 已於 2026/5 終止;Keepa API €49/月 | 用 **Keepa 免費版** 設 Price Watch:UX-15 ≤ ¥5,000、CX-20C([B0HMGJCGVN](https://www.amazon.co.jp/dp/B0HMGJCGVN))≤ ¥7,000(記得勾 New 3rd Party) |
| Bic Camera(備援) | 雷達已自動盯,但家裡電腦關機時會停 | Bic 官方 App 的「ほしいもの」登記 CX-20C,入荷時官方推播 |
| ホビーサーチ | 無 API | 商品頁登記免費的「注文再開メール」 |
| Yahoo!ショッピング | 官方 API 要 Yahoo! JAPAN ID,需日本手機號收 SMS | 暫不做 |
| ヨドバシ / タカラトミーモール | 無公開 API(ヨドバシ已販売終了) | 不做 |
| メルカリ / 價格.com | C2C 二手 / 彙整站,無 API(見「來源分級」) | 不做 |

---

## 🇹🇼 台灣模式(停用中)

以下是原本的台灣通路設計,程式碼保留,在 `config.py` 把 `WATCHES` / `SEARCHES` 的範例取消註解即可恢復。

## 為什麼這樣設計(關鍵結論)

- **分潤只押蝦皮**:momo 分潤(點點賺)已於 **2026/01/31 停止**,個人分潤主力只剩
  [蝦皮分潤計畫](https://affiliate.shopee.tw)(商城約 2–5%,需先申請:約 300 追蹤、審核約 5 工作天、滿 NT$500 提領)。
  momo / PChome / Funbox 只能純導流。過審前草稿放純導流連結即可。
- **最好自動監控(有 API/JSON)**:momo(`getGoodsRealTimeInfo`)、PChome(公開 JSON)、Funbox 官網(SHOPLINE)。
- **難抓**(超商限量、誠品、粉專公告)→ 用 `feed_manual.py` 人工餵進同一行事曆,不硬爬。
- **LINE Notify 已停用** → 通知走 **Telegram bot** 或 **Discord webhook**。

## 架構

```
監控層(自動)          統一行事曆(核心)        通知 + 草稿(給你)
monitors/momo.py  ─┐                          ┌─ notify.py   (Telegram/Discord)
monitors/pchome.py ─┼─▶ calendar_db.py (SQLite) ─┤
monitors/funbox.py ─┘   去重/跨平台合併/狀態機   └─ draft.py    (貼文草稿+蝦皮連結)
feed_manual.py ─────────▶ (人工餵料走同一路徑)
run.py = 排程主迴圈(常駐 or --once 給 cron/GitHub Actions)
```

**狀態機**:`預告(ANNOUNCED) → 即將開賣(IMMINENT) → 已上架/開賣(ON_SALE) → 售罄(SOLD_OUT) → 回補(RESTOCKED)`。
最想被通知的訊號是 **RESTOCKED 且為原價**(秒殺後常見加價轉賣,回到原價才值得搶)。

**兩種監控方式**:
- **盯已知商品碼**(`WATCHES`):Watch 指定商品碼,追它的價格/庫存/開賣時間變化。
- **掃搜尋頁抓新品**(`SEARCHES`,發現式):拿關鍵字掃某商城搜尋頁,「以前沒看過的
  Beyblade X 商品」就當**新商品上架**通知你(如誠品 eslite)。首次掃描先建立基準線
  (不通知),之後才通知真正的新品,避免第一輪洗版。**加新商城 = 加一個 adapter**
  (照 `monitors/eslite.py` 抄)。

## 檔案

| 檔案 | 狀態 | 說明 |
|------|------|------|
| `config.py` | ✅ | 監控清單(`WATCHES`)、輪詢間隔、金鑰(env) |
| `monitors/momo.py` | ✅ MVP | momo `getGoodsRealTimeInfo`,回開賣時間戳/庫存/價格 |
| `monitors/base.py` | ✅ | `ProductSnapshot` 統一格式 + monitor 介面 |
| `calendar_db.py` | ✅ MVP | SQLite 行事曆:去重、跨平台合併、狀態機、變更偵測 |
| `notify.py` | ✅ MVP | Telegram / Discord 通知 + 訊息格式化 |
| `draft.py` | ✅ | 貼文草稿(自寫摘要)+ 蝦皮分潤/導流連結 |
| `feed_manual.py` | ✅ | 人工餵料(超商/粉專公告),走同一 upsert/狀態機/通知 |
| `run.py` | ✅ | 排程主迴圈 |
| `monitors/pchome.py` | ✅ 階段二 | PChome 公開 JSON(Price P/M、Qty);市價 M 可當原價後備 |
| `monitors/funbox.py` | ✅ 階段二 | Funbox SHOPLINE:解析商品頁 JSON-LD(Offer 的 price/availability) |
| `monitors/discovery.py` | ✅ | 發現式監控基底(掃搜尋頁抓新品),一站一個 adapter |
| `monitors/eslite.py` | ✅ | 誠品線上:掃搜尋頁 → 新上架就通知(★需真實 HTML 校準) |
| `monitors/rakuten_jp.py` | ✅ 日本 | 樂天市場官方 API(2026 新規格),品名比對 + 排除中古/拆賣 |
| `alerts.py` | ✅ 日本 | 目標價條件:有貨且 ≤ 門檻,只在「進入條件」時通知一次 |
| `tools/rakuten_check.py` | ✅ 日本 | 樂天 API 校準工具(金鑰遮蔽輸出) |
| `monitors/biccamera.py` | ✅ 日本 | Bic Camera 商品頁:以「第一個下單按鈕可不可按」判斷(灰色按鈕 = 不能買),輔以 JSON-LD / 文字;遵守 robots.txt;被擋時記錯不寫假狀態 |
| `tools/biccamera_check.py` | ✅ 日本 | Bic 校準工具(家裡電腦執行) |
| `health.py` | ✅ | 連續失敗警示 / 恢復通知 |
| `start_radar.bat` | ✅ | Windows 常駐啟動檔(自動重啟) |

## 快速開始

```bash
cd beyblade-radar
pip install -r requirements.txt
cp .env.example .env          # 填 Telegram/Discord;分潤先留空
python -m unittest discover -s tests   # 跑測試(113 項,無需金鑰、不打網路)

python run.py --once          # 跑一輪(cron 模式)
python run.py                 # 常駐,每 POLL_INTERVAL_SEC 一輪
```

要盯哪些商品,改 `config.py` 的 `WATCHES`(商品碼 / 平台 / 已知原價)。
同一顆陀螺在不同平台請用**相同 `product_key`**,行事曆才會跨平台合併。

**人工餵一筆情報**(例:超商限量):

```bash
python feed_manual.py --key UX-05 --platform seven --name "UX-05 超商限量" \
  --price 390 --original-price 390 --on-sale "2026-08-01 00:00" --stock 30 --available
```

## 部署(要可靠命中 00:00 開賣通知)

單機只有開機才跑,建議放**常開主機**或用**雲端排程**:

- **常開主機**(Raspberry Pi / 便宜雲主機):`cron` 每 N 分鐘跑 `python run.py --once`,
  或直接 `python run.py` 常駐。SQLite 會保存上一輪狀態,能正確偵測「售罄→回補」。
- **GitHub Actions**:已附 [`.github/workflows/beyblade-radar.yml`](../.github/workflows/beyblade-radar.yml),
  每 10 分鐘跑一輪。在 repo Secrets 填 `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、
  `RAKUTEN_APP_ID`、`RAKUTEN_ACCESS_KEY`、`RAKUTEN_REFERER`。
  - `radar.db` 用 `actions/cache` 在每輪之間保存,所以「售罄→補貨」、「降進門檻」都偵測得到,
    也不會重複通知。(快取 7 天沒被讀取會被清掉;每 10 分鐘一輪不會發生。)
  - ⚠️ **workflow 必須在預設分支上**:排程(cron)和 Actions 頁面的「Run workflow」手動按鈕,
    都要等這個檔案合併進 repo 的預設分支才會出現 / 生效。
  - ⚠️ 公開 repo 連續 60 天沒活動,GitHub 會暫停排程,到 Actions 頁面重新啟用即可。

## 來源分級(本專案原則)

不是所有「網路上看得到的情報」都能用同一種方式取得。加新來源前先分級:

| 級別 | 例子 | 可以怎麼用 |
|---|---|---|
| **第一手**:零售商自己的公開商品頁 | momo、PChome、Funbox、誠品 | 可低頻自動抓**公開事實**(價格/庫存/上架/開賣時間) |
| **彙整站**:別人整理好的情報資料庫 | beybladehub.app 之類 | **只接站方主動提供的 feed / API,或取得授權;不爬清單頁** |

彙整站的價值來自站方投入人力蒐集、正規化資料。整批複製他人彙整的資料庫,與抓第一手公開
事實**性質不同**(參 Lawsnote 判例)。沒有 feed 就走人工餵料(`feed_manual.py`),
不要寫爬蟲繞過這條線。

接新來源前,先跑探測腳本確認站方有沒有提供 feed:

```bash
python tools/probe_feed.py https://要探測的網站/
```

它會唯讀檢查 `robots.txt`、常見 feed 路徑、首頁的 feed 宣告與內嵌資料,並印出判讀提示。
(JS 動態載入的請求它看不到,需另用 DevTools → Network → Fetch/XHR 確認。)

## 校準抓取器(上線前必做)

發現式 adapter(如 `monitors/eslite.py`)的選擇器需要用**真實 HTML** 對準,因為各站
結構會改版,且開發環境無法連外。步驟:

1. 用瀏覽器開誠品搜尋頁(如 `https://www.eslite.com/search?keyword=beyblade`),F12 開
   DevTools。
2. 看資料從哪來:多半是 `__NEXT_DATA__` 內嵌 JSON,或某個 `/api/...` 搜尋 API 回 JSON,
   或商品頁 JSON-LD。`eslite.py` 三種都試(`extract_products`),但欄位名稱可能要微調。
3. 把一份真實搜尋結果存成 HTML,丟進 `EsliteMonitor.parse_search()` 跑一次,確認有正確
   撈到商品 id / 名稱 / 價格。對不到就改 `_walk_product_like` 的候選欄位名。

> 加其他商城(ToysRUs / 博客來 / 蝦皮…):複製 `eslite.py` 換 `SEARCH_URL` 與抽取邏輯即可。
> 蝦皮反爬強,建議低頻或改人工。

## 關鍵約束與風險

- **法律 / 合規**:只抓公開「事實資料」(價格 / 上架 / 庫存 / 時間)、**低頻**、遵守 robots.txt、
  不繞登入牆、不整批複製他人資料庫(參 Lawsnote 判例)。貼文用**自寫摘要 + 自拍/官方素材**,
  勿轉原圖原文。分潤連結**明示「內含推廣」**(`draft.py` 已內建揭露句)。
- **蝦皮反爬強** → 只做人工 + 分潤連結,別硬爬。
- **momo 會改版**:`getGoodsRealTimeInfo` 端點/欄位可能變動。`monitors/momo.py` 已做防呆解析
  (欄位缺漏不炸整輪),但上線前請用 DevTools Network 再確認一次端點/參數。
- **金鑰不硬編碼**:全走環境變數 / `.env`(見 `.env.example`);`.env` 與 `*.db` 已在 `.gitignore`。

## 分階段

- **MVP(已完成)**:momo monitor + calendar_db + notify + draft + feed_manual + run。
- **階段二(已完成)**:`monitors/pchome.py`(公開 JSON)、`monitors/funbox.py`(JSON-LD)。
  三平台同款用相同 `product_key` 自動合併,`by_product_key()` 可查各平台現況。
- **階段三**:蝦皮分潤過審後,把 `draft.py` 的 `shopee_link` 換成分潤後台產生的正式連結。

共 113 項單元測試(Bic 頁面判斷與 robots + 健康警示 + 樂天解析與請求 + 目標價通知 + 台灣各站解析 + 行事曆狀態機 + 通知 + 草稿),
全部不需金鑰、不打真實網路。

## 測試

```bash
python -m unittest discover -s tests -v
```

涵蓋:momo 回應解析(含缺欄防呆)、狀態機五態轉換、去重、跨平台合併、原價判斷、
價格下跌偵測、通知訊息格式、草稿含推廣揭露。全部不需金鑰、不打真實網路。
