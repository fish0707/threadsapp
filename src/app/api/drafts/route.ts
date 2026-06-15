import { NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { SELF_USER_ID } from "@/lib/config";
import type { DraftStyle } from "@/lib/types";

export const runtime = "nodejs";

// GET /api/drafts — 列出草稿
export async function GET() {
  const drafts = await getStore().listDrafts(SELF_USER_ID);
  return NextResponse.json({ drafts });
}

// POST /api/drafts — 新增草稿  { topic, content, style }
export async function POST(req: Request) {
  try {
    const { topic, content, style } = (await req.json()) as {
      topic?: string;
      content?: string;
      style?: DraftStyle;
    };
    if (!content?.trim()) {
      return NextResponse.json({ error: "草稿內容不可為空" }, { status: 400 });
    }
    const draft = await getStore().createDraft({
      userId: SELF_USER_ID,
      topic: topic ?? "",
      content,
      style: style ?? "story",
    });
    return NextResponse.json({ draft });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "儲存失敗" },
      { status: 500 },
    );
  }
}
