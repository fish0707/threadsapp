import { NextResponse } from "next/server";
import { completeOAuth, resolveRedirectUri } from "@/lib/threadsAuth";

export const runtime = "nodejs";
export const maxDuration = 30;

// GET /api/auth/threads/callback?code=...&state=...
export async function GET(req: Request) {
  const url = new URL(req.url);
  const origin = url.origin;
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const error = url.searchParams.get("error_description") ?? url.searchParams.get("error");

  if (error) {
    return NextResponse.redirect(`${origin}/?threads_error=${encodeURIComponent(error)}`);
  }
  if (!code) {
    return NextResponse.redirect(`${origin}/?threads_error=missing_code`);
  }

  // 驗證 state
  const cookieState = req.headers
    .get("cookie")
    ?.split(";")
    .map((c) => c.trim())
    .find((c) => c.startsWith("threads_oauth_state="))
    ?.split("=")[1];
  if (!state || !cookieState || state !== cookieState) {
    return NextResponse.redirect(`${origin}/?threads_error=state_mismatch`);
  }

  try {
    await completeOAuth(code, resolveRedirectUri(origin));
    const res = NextResponse.redirect(`${origin}/?threads_connected=1`);
    res.cookies.delete("threads_oauth_state");
    return res;
  } catch (e) {
    const msg = e instanceof Error ? e.message : "授權失敗";
    return NextResponse.redirect(`${origin}/?threads_error=${encodeURIComponent(msg)}`);
  }
}
