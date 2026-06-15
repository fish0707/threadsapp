# 脈脈（MaiMai）Threads 經營助手

輸入一個主題 → 抓當天 Threads 熱門文 → AI 參考風格生成貼文草稿 → 草稿匣管理 → 一鍵發佈。

> Phase 1（自用 MVP）。技術棧：Next.js (App Router) + TypeScript + Tailwind CSS + Supabase + Gemini / Claude，部署於 Vercel。

## ✨ 特色：免金鑰即可試跑（Mock 模式）

沒有任何金鑰也能 `npm install && npm run dev` 直接跑起來體驗完整流程：

| 功能 | 沒金鑰時的行為 |
|------|----------------|
| 搜尋熱門文 | 回傳帶入你主題的範例熱門貼文 |
| AI 生成 | 回傳依風格的範例草稿 |
| 草稿匣 | 存在記憶體（重啟即清空） |
| 發佈 | 模擬發佈，回傳假貼文 id |

頁面上方的黃色橫幅會即時顯示「目前哪些功能在 mock」。填入金鑰後該功能自動切換為真實串接，無需改程式。

## 🚀 快速開始

```bash
npm install
cp .env.example .env.local   # 可全部留空，先跑 mock
npm run dev                  # http://localhost:3000
```

## 🔑 啟用真實串接

編輯 `.env.local`，填入對應金鑰（任一組可獨立啟用）：

- **Gemini 生成**：`GEMINI_API_KEY`
- **Claude 高品質模式**：`ANTHROPIC_API_KEY`
- **資料持久化**：`NEXT_PUBLIC_SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`
  - 先到 Supabase SQL Editor 執行 [`supabase/schema.sql`](supabase/schema.sql) 建表。
- **Threads 搜尋 + 發佈（推薦走 OAuth）**：`THREADS_APP_ID` + `THREADS_APP_SECRET`
  - 設好後首頁會出現「連結 Threads 帳號」按鈕，點一下完成授權即可，系統自動換**長效 token（~60 天）並在到期前自動續期**，存進 Supabase（設 `TOKEN_ENCRYPTION_KEY` 會加密儲存）。
  - 到 Meta → Threads 使用案例 → 設定，把這個加進 **Redirect Callback URLs**：
    `https://你的網域/api/auth/threads/callback`
  - 後備：也可不走 OAuth，直接手動貼 `THREADS_ACCESS_TOKEN`（+ `THREADS_USER_ID`）。
  - 需先完成 Meta 開發者帳號、Threads App、`keyword_search` 與 publishing 權限審核（見下方 Phase 0）。

### Threads OAuth 流程（自動換 / 續 token）

```
首頁「連結 Threads 帳號」→ /api/auth/threads/login
   → Threads 授權頁（threads_basic / content_publish / keyword_search）
   → /api/auth/threads/callback?code=...
   → 換短效 token → 換長效 token(~60天) → (加密) 存 Supabase users 表
搜尋 / 發佈時：resolveThreadsToken() 讀 DB token，剩 <7 天自動續期
```

完整變數說明見 [`.env.example`](.env.example)。

## 🗂 專案結構

```
src/
├── app/
│   ├── page.tsx              主流程：搜尋→勾選→生成→草稿
│   ├── drafts/page.tsx       草稿匣（編輯 / 複製 / 刪除 / 發佈）
│   └── api/
│       ├── search/route.ts   keyword_search + 快取
│       ├── generate/route.ts AI 生成
│       ├── drafts/…          草稿 CRUD
│       ├── publish/route.ts  Threads 兩步驟發佈
│       └── status/route.ts   回報 mock 狀態
├── lib/
│   ├── config.ts             環境偵測（決定真實 / mock）
│   ├── threads.ts            Threads API client（含 mock）
│   ├── ai.ts                 Gemini / Claude（含 mock）
│   ├── store.ts              Supabase / 記憶體 雙實作
│   ├── prompts.ts            各風格 prompt 模板
│   └── mockData.ts           mock 熱門文
└── components/               UI 元件
supabase/schema.sql           建表 SQL
```

## ⚠️ Threads API 注意事項（已納入設計）

- **查詢額度**：每使用者滾動 24h 最多 2,200 次（跨 app 共用）→ 同主題當天結果快取於 DB，不重複查詢。
- **無互動數**：keyword_search 不回傳讚 / 回覆數，「熱門」依官方 `search_type=TOP` 排序。
- **敏感字詞**：含敏感字的查詢會回空陣列（正常行為）。
- **發佈為兩步驟**：建立 container → publish。保留「人工確認後發佈」步驟，不做全自動轟炸。
- 以上政策可能被 Meta 調整，產品化前需再次核對官方文件。

## 🧭 部署到 Vercel

1. Push 到 GitHub。
2. Vercel 匯入專案，於 Project Settings → Environment Variables 填入金鑰。
3. Deploy。

> 注意：記憶體 store 僅供本機 / demo。正式部署請務必設定 Supabase，否則 serverless 各次呼叫不共用資料。

## 🛣 後續（Phase 2）

多使用者 OAuth 授權、用量 / 額度控管、成效儀表板、付費方案（Claude 高品質）、第三方互動數補強。

---

### Phase 0 前置作業檢查清單

- [ ] 申請 Meta 開發者帳號、建立 Threads App。
- [ ] 申請 `keyword_search`、publishing 權限（需審核）。
- [ ] 跑通 OAuth 授權流程，取得 access token。
