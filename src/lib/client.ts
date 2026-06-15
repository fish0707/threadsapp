// 前端用的 fetch 封裝
import type {
  AiMode,
  Draft,
  DraftStatus,
  DraftStyle,
  ThreadsPost,
} from "./types";

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? "請求失敗");
  return data as T;
}

export const api = {
  status: () =>
    jsonFetch<{ mock: Record<string, boolean> }>("/api/status"),

  search: (topic: string, mode: "KEYWORD" | "TAG" = "KEYWORD", force = false) =>
    jsonFetch<{ posts: ThreadsPost[]; cached: boolean; mocked: boolean }>(
      "/api/search",
      { method: "POST", body: JSON.stringify({ topic, mode, force }) },
    ),

  generate: (input: {
    topic: string;
    references: ThreadsPost[];
    style: DraftStyle;
    mode: AiMode;
    count?: number;
  }) =>
    jsonFetch<{ drafts: string[]; usedMode: string }>("/api/generate", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  listDrafts: () => jsonFetch<{ drafts: Draft[] }>("/api/drafts"),

  saveDraft: (input: { topic: string; content: string; style: DraftStyle }) =>
    jsonFetch<{ draft: Draft }>("/api/drafts", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updateDraft: (id: string, patch: { content?: string; status?: DraftStatus }) =>
    jsonFetch<{ draft: Draft }>(`/api/drafts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  deleteDraft: (id: string) =>
    jsonFetch<{ ok: boolean }>(`/api/drafts/${id}`, { method: "DELETE" }),

  publish: (input: { content: string; draftId?: string }) =>
    jsonFetch<{ threads_post_id: string; permalink?: string; mocked: boolean }>(
      "/api/publish",
      { method: "POST", body: JSON.stringify(input) },
    ),
};
