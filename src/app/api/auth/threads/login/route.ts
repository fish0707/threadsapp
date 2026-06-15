import { NextResponse } from "next/server";
import { randomBytes } from "crypto";
import { config } from "@/lib/config";
import { buildAuthorizeUrl, resolveRedirectUri } from "@/lib/threadsAuth";

export const runtime = "nodejs";

// GET /api/auth/threads/login — 導向 Threads 授權頁
export async function GET(req: Request) {
  if (!config.threads.oauthEnabled) {
    return NextResponse.json(
      { error: "尚未設定 THREADS_APP_ID / THREADS_APP_SECRET" },
      { status: 400 },
    );
  }
  const origin = new URL(req.url).origin;
  const redirectUri = resolveRedirectUri(origin);
  const state = randomBytes(16).toString("hex");

  const res = NextResponse.redirect(buildAuthorizeUrl(redirectUri, state));
  // 用 cookie 存 state 防 CSRF
  res.cookies.set("threads_oauth_state", state, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 600,
    path: "/",
  });
  return res;
}
