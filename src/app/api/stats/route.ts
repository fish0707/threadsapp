import { NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { SELF_USER_ID } from "@/lib/config";
import { DRAFT_STYLES } from "@/lib/types";

export const runtime = "nodejs";

// GET /api/stats — 工作儀表板用的彙總數據
export async function GET() {
  const store = getStore();
  const [drafts, published] = await Promise.all([
    store.listDrafts(SELF_USER_ID),
    store.listPublished(SELF_USER_ID),
  ]);

  const byStyle = DRAFT_STYLES.map((s) => ({
    style: s.value,
    label: s.label,
    count: drafts.filter((d) => d.style === s.value).length,
  }));

  return NextResponse.json({
    draftCount: drafts.length,
    publishedCount: published.length,
    byStyle,
    recentPublished: published.slice(0, 10),
  });
}
