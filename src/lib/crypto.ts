import { createCipheriv, createDecipheriv, createHash, randomBytes } from "crypto";
import { config } from "./config";

// Token 靜態加密：設了 TOKEN_ENCRYPTION_KEY → AES-256-GCM；沒設則明文（dev）。
// 格式：enc:v1:<iv_b64>:<tag_b64>:<cipher_b64>

const PREFIX = "enc:v1:";

function key(): Buffer {
  return createHash("sha256").update(config.tokenEncryptionKey).digest();
}

export function encryptToken(plain: string): string {
  if (!config.tokenEncryptionKey) return plain;
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key(), iv);
  const enc = Buffer.concat([cipher.update(plain, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return `${PREFIX}${iv.toString("base64")}:${tag.toString("base64")}:${enc.toString("base64")}`;
}

export function decryptToken(stored: string): string {
  if (!stored.startsWith(PREFIX)) return stored; // 明文（未加密時存的）
  if (!config.tokenEncryptionKey) {
    throw new Error("資料庫中的 token 已加密，但未設定 TOKEN_ENCRYPTION_KEY 無法解密。");
  }
  const [, , ivB64, tagB64, dataB64] = stored.split(":");
  const decipher = createDecipheriv("aes-256-gcm", key(), Buffer.from(ivB64, "base64"));
  decipher.setAuthTag(Buffer.from(tagB64, "base64"));
  const dec = Buffer.concat([
    decipher.update(Buffer.from(dataB64, "base64")),
    decipher.final(),
  ]);
  return dec.toString("utf8");
}
