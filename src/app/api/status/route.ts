import { NextResponse } from "next/server";
import { getMockStatus } from "@/lib/config";

export const runtime = "nodejs";

// GET /api/status — 回報哪些功能目前在 mock 模式，給前端顯示提示。
export async function GET() {
  return NextResponse.json({ mock: getMockStatus() });
}
