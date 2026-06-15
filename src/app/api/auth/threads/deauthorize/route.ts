import { NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { SELF_USER_ID } from "@/lib/config";
import { parseSignedRequest } from "@/lib/threadsAuth";

export const runtime = "nodejs";

// POST /api/auth/threads/deauthorize
// 使用者在 Threads 取消授權時，Meta 會 ping 這裡（帶 signed_request）。
export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const signed = form.get("signed_request");
    if (typeof signed === "string") {
      const data = parseSignedRequest(signed);
      if (data) {
        // 自用單帳號：清除存的 token
        await getStore().clearAuthUser(SELF_USER_ID);
      }
    }
  } catch {
    // 即使解析失敗也回 200，避免 Meta 重試風暴
  }
  return NextResponse.json({ ok: true });
}
