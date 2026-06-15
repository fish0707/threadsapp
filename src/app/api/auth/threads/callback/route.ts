import { NextResponse } from "next/server";
import { completeOAuth, resolveRedirectUri } from "@/lib/threadsAuth";

export const runtime = "nodejs";
export const maxDuration = 30;

function fail(origin: string, msg: string) {
  return NextResponse.redirect(`${origin}/?threads_error=${encodeURIComponent(msg)}`);
}

// GET /api/auth/threads/callback?code=...&state=...
export async function GET(req: Request) {
  const url = new URL(req.url);
  const origin = url.origin;
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");

  // Threads 把錯誤丟回時帶的參數
  const errDesc = url.searchParams.get("error_description");
  const errReason = url.searchParams.get("error_reason");
  const errCode = url.searchParams.get("error_code");
  const err = url.searchParams.get("error");
  if (errDesc || err || errCode) {
    console.error("[threads-oauth] authorize error:", {
      err,
      errReason,
      errCode,
      errDesc,
    });
    return fail(
      origin,
      `[授權階段] ${errDesc ?? err ?? ""}${errCode ? ` (code ${errCode})` : ""}`,
    );
  }

  if (!code) return fail(origin, "missing_code");

  // 驗證 state
  const cookieState = req.headers
    .get("cookie")
    ?.split(";")
    .map((c) => c.trim())
    .find((c) => c.startsWith("threads_oauth_state="))
    ?.split("=")[1];
  if (!state || !cookieState || state !== cookieState) {
    return fail(origin, "state_mismatch（請重新整理頁面後再試一次）");
  }

  try {
    await completeOAuth(code, resolveRedirectUri(origin));
    const res = NextResponse.redirect(`${origin}/?threads_connected=1`);
    res.cookies.delete("threads_oauth_state");
    return res;
  } catch (e) {
    const msg = e instanceof Error ? e.message : "授權失敗";
    console.error("[threads-oauth] exchange error:", msg);
    return fail(origin, msg);
  }
}
