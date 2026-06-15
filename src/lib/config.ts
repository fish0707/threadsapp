// 環境偵測：依金鑰是否存在，決定走真實串接還是 mock 模式。

export const config = {
  gemini: {
    apiKey: process.env.GEMINI_API_KEY ?? "",
    model: process.env.GEMINI_MODEL ?? "gemini-2.5-flash",
    get enabled() {
      return this.apiKey.length > 0;
    },
  },
  claude: {
    apiKey: process.env.ANTHROPIC_API_KEY ?? "",
    model: process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-6",
    get enabled() {
      return this.apiKey.length > 0;
    },
  },
  supabase: {
    // 容錯：去掉空白、結尾 /rest/v1、結尾斜線，只留基底網址
    url: (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "")
      .trim()
      .replace(/\/rest\/v1\/?$/, "")
      .replace(/\/+$/, ""),
    serviceKey: (process.env.SUPABASE_SERVICE_ROLE_KEY ?? "").trim(),
    get enabled() {
      return this.url.length > 0 && this.serviceKey.length > 0;
    },
  },
  threads: {
    // env token：選用的後備（手動貼 token）。優先用 OAuth 存進 DB 的長效 token。
    accessToken: process.env.THREADS_ACCESS_TOKEN ?? "",
    userId: process.env.THREADS_USER_ID ?? "me",
    apiVersion: process.env.THREADS_API_VERSION ?? "v1.0",
    // OAuth 應用程式憑證
    appId: process.env.THREADS_APP_ID ?? "",
    appSecret: process.env.THREADS_APP_SECRET ?? "",
    // 可選：明確指定 redirect uri，否則由請求 origin 動態組出
    redirectUri: process.env.THREADS_REDIRECT_URI ?? "",
    scopes: ["threads_basic", "threads_content_publish", "threads_keyword_search"],
    get oauthEnabled() {
      return this.appId.length > 0 && this.appSecret.length > 0;
    },
  },
  cache: {
    hours: Number(process.env.TOPIC_CACHE_HOURS ?? "24"),
  },
  // Token 靜態加密金鑰（選用）。設了就 AES-256-GCM 加密後存 DB。
  tokenEncryptionKey: process.env.TOKEN_ENCRYPTION_KEY ?? "",
};

// Phase 1 自用：先以單一固定 user。Phase 2 改成 OAuth 多使用者。
export const SELF_USER_ID = "self";
