import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { config } from "./config";
import type { Draft, DraftStyle, DraftStatus, PublishedPost, ThreadsPost } from "./types";

/** 已授權使用者的 Threads token 紀錄（access_token 為密文/明文） */
export interface AuthUser {
  access_token: string;
  threads_user_id: string;
  username: string | null;
  token_expires_at: string | null; // ISO
}

/**
 * 資料存取層。有 Supabase 金鑰 → 走 Supabase；否則用記憶體暫存（demo 用，重啟即清空）。
 * 透過介面隔離，Phase 2 可無痛換成真實 DB / 加 RLS。
 */
export interface Store {
  getTopicCache(topic: string): Promise<ThreadsPost[] | null>;
  setTopicCache(topic: string, posts: ThreadsPost[]): Promise<void>;
  listDrafts(userId: string): Promise<Draft[]>;
  createDraft(input: {
    userId: string;
    topic: string;
    content: string;
    style: DraftStyle;
  }): Promise<Draft>;
  updateDraft(
    userId: string,
    id: string,
    patch: Partial<Pick<Draft, "content" | "status">>,
  ): Promise<Draft | null>;
  deleteDraft(userId: string, id: string): Promise<boolean>;
  recordPublished(input: {
    userId: string;
    draftId: string | null;
    threadsPostId: string;
    permalink?: string;
  }): Promise<PublishedPost>;
  getAuthUser(userId: string): Promise<AuthUser | null>;
  saveAuthUser(userId: string, data: AuthUser): Promise<void>;
  clearAuthUser(userId: string): Promise<void>;
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function isFresh(cachedAt: string): boolean {
  const ageMs = Date.now() - new Date(cachedAt).getTime();
  return ageMs < config.cache.hours * 60 * 60 * 1000;
}

// ───────────────────────── 記憶體實作 ─────────────────────────
interface MemoryDb {
  topicCache: Map<string, { posts: ThreadsPost[]; cached_at: string; date: string }>;
  drafts: Draft[];
  published: PublishedPost[];
  authUsers: Map<string, AuthUser>;
}

// 用 globalThis 讓 dev 熱重載時不被清空
const g = globalThis as unknown as { __maimaiDb?: MemoryDb };
const memory: MemoryDb =
  g.__maimaiDb ??
  (g.__maimaiDb = {
    topicCache: new Map(),
    drafts: [],
    published: [],
    authUsers: new Map(),
  });

class MemoryStore implements Store {
  async getTopicCache(topic: string): Promise<ThreadsPost[] | null> {
    const entry = memory.topicCache.get(topic);
    if (entry && entry.date === todayStr() && isFresh(entry.cached_at)) {
      return entry.posts;
    }
    return null;
  }
  async setTopicCache(topic: string, posts: ThreadsPost[]): Promise<void> {
    memory.topicCache.set(topic, {
      posts,
      cached_at: new Date().toISOString(),
      date: todayStr(),
    });
  }
  async listDrafts(userId: string): Promise<Draft[]> {
    return memory.drafts
      .filter((d) => d.user_id === userId)
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
  }
  async createDraft(input: {
    userId: string;
    topic: string;
    content: string;
    style: DraftStyle;
  }): Promise<Draft> {
    const draft: Draft = {
      id: `d_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      user_id: input.userId,
      topic: input.topic,
      content: input.content,
      style: input.style,
      char_count: [...input.content].length,
      status: "draft",
      created_at: new Date().toISOString(),
    };
    memory.drafts.push(draft);
    return draft;
  }
  async updateDraft(
    userId: string,
    id: string,
    patch: Partial<Pick<Draft, "content" | "status">>,
  ): Promise<Draft | null> {
    const draft = memory.drafts.find((d) => d.id === id && d.user_id === userId);
    if (!draft) return null;
    if (patch.content !== undefined) {
      draft.content = patch.content;
      draft.char_count = [...patch.content].length;
    }
    if (patch.status !== undefined) draft.status = patch.status;
    return draft;
  }
  async deleteDraft(userId: string, id: string): Promise<boolean> {
    const idx = memory.drafts.findIndex((d) => d.id === id && d.user_id === userId);
    if (idx === -1) return false;
    memory.drafts.splice(idx, 1);
    return true;
  }
  async recordPublished(input: {
    userId: string;
    draftId: string | null;
    threadsPostId: string;
    permalink?: string;
  }): Promise<PublishedPost> {
    const rec: PublishedPost = {
      id: `p_${Date.now()}`,
      user_id: input.userId,
      draft_id: input.draftId,
      threads_post_id: input.threadsPostId,
      permalink: input.permalink,
      published_at: new Date().toISOString(),
    };
    memory.published.push(rec);
    return rec;
  }
  async getAuthUser(userId: string): Promise<AuthUser | null> {
    return memory.authUsers.get(userId) ?? null;
  }
  async saveAuthUser(userId: string, data: AuthUser): Promise<void> {
    memory.authUsers.set(userId, data);
  }
  async clearAuthUser(userId: string): Promise<void> {
    memory.authUsers.delete(userId);
  }
}

// ───────────────────────── Supabase 實作 ─────────────────────────
class SupabaseStore implements Store {
  private db: SupabaseClient;
  constructor() {
    this.db = createClient(config.supabase.url, config.supabase.serviceKey, {
      auth: { persistSession: false },
    });
  }
  async getTopicCache(topic: string): Promise<ThreadsPost[] | null> {
    const { data } = await this.db
      .from("topic_cache")
      .select("posts, cached_at, fetched_date")
      .eq("topic", topic)
      .eq("fetched_date", todayStr())
      .maybeSingle();
    if (data && isFresh(data.cached_at)) return data.posts as ThreadsPost[];
    return null;
  }
  async setTopicCache(topic: string, posts: ThreadsPost[]): Promise<void> {
    await this.db.from("topic_cache").upsert(
      {
        topic,
        fetched_date: todayStr(),
        posts,
        cached_at: new Date().toISOString(),
      },
      { onConflict: "topic,fetched_date" },
    );
  }
  async listDrafts(userId: string): Promise<Draft[]> {
    const { data } = await this.db
      .from("drafts")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });
    return (data ?? []) as Draft[];
  }
  async createDraft(input: {
    userId: string;
    topic: string;
    content: string;
    style: DraftStyle;
  }): Promise<Draft> {
    const { data, error } = await this.db
      .from("drafts")
      .insert({
        user_id: input.userId,
        topic: input.topic,
        content: input.content,
        style: input.style,
        char_count: [...input.content].length,
        status: "draft" as DraftStatus,
      })
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return data as Draft;
  }
  async updateDraft(
    userId: string,
    id: string,
    patch: Partial<Pick<Draft, "content" | "status">>,
  ): Promise<Draft | null> {
    const payload: Record<string, unknown> = { ...patch };
    if (patch.content !== undefined) payload.char_count = [...patch.content].length;
    const { data } = await this.db
      .from("drafts")
      .update(payload)
      .eq("id", id)
      .eq("user_id", userId)
      .select("*")
      .maybeSingle();
    return (data as Draft) ?? null;
  }
  async deleteDraft(userId: string, id: string): Promise<boolean> {
    const { error } = await this.db
      .from("drafts")
      .delete()
      .eq("id", id)
      .eq("user_id", userId);
    return !error;
  }
  async recordPublished(input: {
    userId: string;
    draftId: string | null;
    threadsPostId: string;
    permalink?: string;
  }): Promise<PublishedPost> {
    const { data, error } = await this.db
      .from("published_posts")
      .insert({
        user_id: input.userId,
        draft_id: input.draftId,
        threads_post_id: input.threadsPostId,
        permalink: input.permalink,
      })
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    return data as PublishedPost;
  }
  async getAuthUser(userId: string): Promise<AuthUser | null> {
    const { data } = await this.db
      .from("users")
      .select("access_token, threads_user_id, username, token_expires_at")
      .eq("id", userId)
      .maybeSingle();
    if (!data || !data.access_token) return null;
    return data as AuthUser;
  }
  async saveAuthUser(userId: string, data: AuthUser): Promise<void> {
    const { error } = await this.db.from("users").upsert(
      {
        id: userId,
        access_token: data.access_token,
        threads_user_id: data.threads_user_id,
        username: data.username,
        token_expires_at: data.token_expires_at,
      },
      { onConflict: "id" },
    );
    if (error) throw new Error(error.message);
  }
  async clearAuthUser(userId: string): Promise<void> {
    await this.db
      .from("users")
      .update({ access_token: null, token_expires_at: null })
      .eq("id", userId);
  }
}

let _store: Store | null = null;
export function getStore(): Store {
  if (!_store) {
    _store = config.supabase.enabled ? new SupabaseStore() : new MemoryStore();
  }
  return _store;
}
