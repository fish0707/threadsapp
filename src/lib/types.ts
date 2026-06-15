// 共用型別定義

/** 從 Threads keyword_search 取回的熱門貼文 */
export interface ThreadsPost {
  id: string;
  text: string;
  username: string;
  permalink: string;
  timestamp: string; // ISO 字串
  media_type?: string;
}

/** AI 生成的草稿風格 */
export type DraftStyle = "story" | "humor" | "listicle" | "insight";

export const DRAFT_STYLES: { value: DraftStyle; label: string; hint: string }[] = [
  { value: "story", label: "故事情緒型", hint: "用個人經歷與情緒帶出共鳴" },
  { value: "humor", label: "幽默有梗型", hint: "輕鬆、有梗、容易被轉發" },
  { value: "listicle", label: "條列乾貨型", hint: "重點條列、資訊密度高" },
  { value: "insight", label: "觀點洞察型", hint: "提出獨到觀點、引發討論" },
];

/** AI 模型模式 */
export type AiMode = "gemini" | "claude";

/** 草稿狀態 */
export type DraftStatus = "draft" | "published";

/** 草稿匣中的一筆草稿 */
export interface Draft {
  id: string;
  user_id: string;
  topic: string;
  content: string;
  style: DraftStyle;
  char_count: number;
  status: DraftStatus;
  created_at: string;
}

/** 已發佈紀錄 */
export interface PublishedPost {
  id: string;
  user_id: string;
  draft_id: string | null;
  threads_post_id: string;
  permalink?: string;
  published_at: string;
}

/** 主題快取 */
export interface TopicCache {
  topic: string;
  fetched_date: string; // YYYY-MM-DD
  posts: ThreadsPost[];
  cached_at: string;
}

export interface GenerateRequest {
  topic: string;
  references: ThreadsPost[];
  style: DraftStyle;
  mode: AiMode;
  count?: number;
}
