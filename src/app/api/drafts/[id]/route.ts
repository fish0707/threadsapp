import { NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { SELF_USER_ID } from "@/lib/config";
import type { DraftStatus } from "@/lib/types";

export const runtime = "nodejs";

// PATCH /api/drafts/:id  { content?, status? }
export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const { content, status } = (await req.json()) as {
    content?: string;
    status?: DraftStatus;
  };
  const draft = await getStore().updateDraft(SELF_USER_ID, id, { content, status });
  if (!draft) return NextResponse.json({ error: "找不到草稿" }, { status: 404 });
  return NextResponse.json({ draft });
}

// DELETE /api/drafts/:id
export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const ok = await getStore().deleteDraft(SELF_USER_ID, id);
  if (!ok) return NextResponse.json({ error: "找不到草稿" }, { status: 404 });
  return NextResponse.json({ ok: true });
}
