import { NextResponse } from "next/server";
import { config } from "@/lib/config";
import { getThreadsConnection } from "@/lib/threadsAuth";

export const runtime = "nodejs";

// GET /api/status — 回報 mock 狀態與 Threads 連線狀態，給前端顯示。
export async function GET() {
  const threads = await getThreadsConnection();
  return NextResponse.json({
    mock: {
      search: !threads.connected,
      publish: !threads.connected,
      geminiGenerate: !config.gemini.enabled,
      claudeGenerate: !config.claude.enabled,
      storage: !config.supabase.enabled,
    },
    threads: {
      connected: threads.connected,
      username: threads.username,
      source: threads.source,
      oauthAvailable: config.threads.oauthEnabled,
    },
  });
}
