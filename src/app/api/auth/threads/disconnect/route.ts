import { NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { SELF_USER_ID } from "@/lib/config";

export const runtime = "nodejs";

// POST /api/auth/threads/disconnect — 解除連結（清除存的 token）
export async function POST() {
  await getStore().clearAuthUser(SELF_USER_ID);
  return NextResponse.json({ ok: true });
}
