import { NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { SELF_USER_ID } from "@/lib/config";
import { parseSignedRequest } from "@/lib/threadsAuth";

export const runtime = "nodejs";

// POST /api/auth/threads/deletion
// 使用者要求刪除資料時，Meta ping 這裡（帶 signed_request）。
// 需回傳 { url, confirmation_code } 供 Meta 與使用者查核。
export async function POST(req: Request) {
  const origin = new URL(req.url).origin;
  let code = `del_${Date.now()}`;
  try {
    const form = await req.formData();
    const signed = form.get("signed_request");
    if (typeof signed === "string") {
      const data = parseSignedRequest(signed);
      if (data) {
        await getStore().clearAuthUser(SELF_USER_ID);
        if (data.user_id) code = `del_${data.user_id}`;
      }
    }
  } catch {
    // 解析失敗仍回標準格式
  }
  return NextResponse.json({
    url: `${origin}/?deletion=${code}`,
    confirmation_code: code,
  });
}
