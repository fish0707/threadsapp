import { NextResponse } from "next/server";
import { generateDrafts } from "@/lib/ai";
import type { AiMode, DraftStyle, ThreadsPost } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

// POST /api/generate  { topic, references, style, mode, count? }
export async function POST(req: Request) {
  try {
    const body = (await req.json()) as {
      topic?: string;
      references?: ThreadsPost[];
      style?: DraftStyle;
      mode?: AiMode;
      count?: number;
    };
    const topic = (body.topic ?? "").trim();
    if (!topic) {
      return NextResponse.json({ error: "請輸入主題" }, { status: 400 });
    }

    const result = await generateDrafts({
      topic,
      references: body.references ?? [],
      style: body.style ?? "story",
      mode: body.mode ?? "gemini",
      count: Math.min(Math.max(body.count ?? 3, 1), 5),
    });

    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "生成失敗" },
      { status: 500 },
    );
  }
}
