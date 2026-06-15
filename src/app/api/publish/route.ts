import { NextResponse } from "next/server";
import { publishTextPost } from "@/lib/threads";
import { getStore } from "@/lib/store";
import { SELF_USER_ID } from "@/lib/config";

export const runtime = "nodejs";
export const maxDuration = 60;

// POST /api/publish  { content, draftId? }
export async function POST(req: Request) {
  try {
    const { content, draftId } = (await req.json()) as {
      content?: string;
      draftId?: string;
    };
    const text = (content ?? "").trim();
    if (!text) {
      return NextResponse.json({ error: "貼文內容不可為空" }, { status: 400 });
    }

    const result = await publishTextPost(text);

    const store = getStore();
    await store.recordPublished({
      userId: SELF_USER_ID,
      draftId: draftId ?? null,
      threadsPostId: result.threads_post_id,
      permalink: result.permalink,
    });

    // 若來自草稿，標記為已發佈
    if (draftId) {
      await store.updateDraft(SELF_USER_ID, draftId, { status: "published" });
    }

    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "發佈失敗" },
      { status: 500 },
    );
  }
}
