import { NextResponse } from "next/server";
import { searchTopic } from "@/lib/threads";
import { getStore } from "@/lib/store";

export const runtime = "nodejs";

// POST /api/search  { topic, mode?: "KEYWORD"|"TAG", force?: boolean }
export async function POST(req: Request) {
  try {
    const { topic, mode, force } = (await req.json()) as {
      topic?: string;
      mode?: "KEYWORD" | "TAG";
      force?: boolean;
    };
    const trimmed = (topic ?? "").trim();
    if (!trimmed) {
      return NextResponse.json({ error: "請輸入主題" }, { status: 400 });
    }

    const store = getStore();

    // 1) 先查快取（省 Threads 額度：滾動 24h / 2,200 次）
    if (!force) {
      const cached = await store.getTopicCache(trimmed);
      if (cached) {
        return NextResponse.json({ posts: cached, cached: true, mocked: false });
      }
    }

    // 2) 呼叫 Threads keyword_search（或 mock）
    const { posts, mocked } = await searchTopic(trimmed, { mode });
    await store.setTopicCache(trimmed, posts);

    return NextResponse.json({ posts, cached: false, mocked });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "搜尋失敗" },
      { status: 500 },
    );
  }
}
