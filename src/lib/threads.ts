import { config } from "./config";
import { getMockPosts } from "./mockData";
import { resolveThreadsToken } from "./threadsAuth";
import type { ThreadsPost } from "./types";

const GRAPH_BASE = "https://graph.threads.net";

/**
 * 以關鍵字搜尋當天熱門公開貼文（search_type=TOP）。
 * 無可用 token（OAuth / env）→ mock。
 *
 * 注意：Threads keyword_search 屬受限端點，需通過 Meta 權限審核。
 * 審核通過前只會搜到「自己帳號」的貼文。
 * 額度：每使用者滾動 24h 最多 2,200 次查詢（跨 app 共用）→ 用快取節流（見 store）。
 */
export async function searchTopic(
  topic: string,
  opts: { mode?: "KEYWORD" | "TAG" } = {},
): Promise<{ posts: ThreadsPost[]; mocked: boolean }> {
  const auth = await resolveThreadsToken();
  if (!auth) {
    return { posts: getMockPosts(topic), mocked: true };
  }

  const fields = "id,text,media_type,permalink,timestamp,username";
  const url = new URL(`${GRAPH_BASE}/${config.threads.apiVersion}/keyword_search`);
  url.searchParams.set("q", topic);
  url.searchParams.set("search_type", "TOP");
  url.searchParams.set("search_mode", opts.mode ?? "KEYWORD");
  url.searchParams.set("fields", fields);
  url.searchParams.set("access_token", auth.token);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Threads keyword_search 失敗 (${res.status}): ${body}`);
  }
  const json = (await res.json()) as { data?: ThreadsPost[] };
  // 敏感字詞會回空陣列，這是正常行為。
  return { posts: json.data ?? [], mocked: false };
}

/**
 * 發佈一篇純文字貼文。Threads 官方為兩步驟：
 *  1) 建立 media container
 *  2) publish container
 * 無可用 token → mock 回傳假 id。
 */
export async function publishTextPost(
  text: string,
): Promise<{ threads_post_id: string; permalink?: string; mocked: boolean }> {
  const auth = await resolveThreadsToken();
  if (!auth) {
    return {
      threads_post_id: `mock_post_${Date.now()}`,
      permalink: "https://www.threads.net/",
      mocked: true,
    };
  }

  const { token, userId } = auth;
  const { apiVersion } = config.threads;

  // Step 1: create container
  const createUrl = new URL(`${GRAPH_BASE}/${apiVersion}/${userId}/threads`);
  createUrl.searchParams.set("media_type", "TEXT");
  createUrl.searchParams.set("text", text);
  createUrl.searchParams.set("access_token", token);

  const createRes = await fetch(createUrl.toString(), { method: "POST" });
  if (!createRes.ok) {
    throw new Error(`建立貼文容器失敗 (${createRes.status}): ${await createRes.text()}`);
  }
  const { id: creationId } = (await createRes.json()) as { id: string };

  // Step 2: publish
  const publishUrl = new URL(`${GRAPH_BASE}/${apiVersion}/${userId}/threads_publish`);
  publishUrl.searchParams.set("creation_id", creationId);
  publishUrl.searchParams.set("access_token", token);

  const pubRes = await fetch(publishUrl.toString(), { method: "POST" });
  if (!pubRes.ok) {
    throw new Error(`發佈貼文失敗 (${pubRes.status}): ${await pubRes.text()}`);
  }
  const { id: postId } = (await pubRes.json()) as { id: string };

  // 取回 permalink（可選）
  let permalink: string | undefined;
  try {
    const infoUrl = new URL(`${GRAPH_BASE}/${apiVersion}/${postId}`);
    infoUrl.searchParams.set("fields", "permalink");
    infoUrl.searchParams.set("access_token", token);
    const infoRes = await fetch(infoUrl.toString());
    if (infoRes.ok) {
      permalink = ((await infoRes.json()) as { permalink?: string }).permalink;
    }
  } catch {
    // permalink 取不到不影響發佈成功
  }

  return { threads_post_id: postId, permalink, mocked: false };
}
