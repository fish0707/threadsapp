// 環境偵測：依金鑰是否存在，決定走真實串接還是 mock 模式。

export const config = {
  gemini: {
    apiKey: process.env.GEMINI_API_KEY ?? "",
    model: process.env.GEMINI_MODEL ?? "gemini-2.0-flash",
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
    url: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
    serviceKey: process.env.SUPABASE_SERVICE_ROLE_KEY ?? "",
    get enabled() {
      return this.url.length > 0 && this.serviceKey.length > 0;
    },
  },
  threads: {
    accessToken: process.env.THREADS_ACCESS_TOKEN ?? "",
    userId: process.env.THREADS_USER_ID ?? "me",
    apiVersion: process.env.THREADS_API_VERSION ?? "v1.0",
    get enabled() {
      return this.accessToken.length > 0;
    },
  },
  cache: {
    hours: Number(process.env.TOPIC_CACHE_HOURS ?? "24"),
  },
};

/** 給前端顯示的「目前哪些功能在 mock」狀態 */
export function getMockStatus() {
  return {
    search: !config.threads.enabled, // 搜尋熱門文
    publish: !config.threads.enabled, // 發佈
    geminiGenerate: !config.gemini.enabled,
    claudeGenerate: !config.claude.enabled,
    storage: !config.supabase.enabled,
  };
}

// Phase 1 自用：先以單一固定 user。Phase 2 改成 OAuth 多使用者。
export const SELF_USER_ID = "self";
