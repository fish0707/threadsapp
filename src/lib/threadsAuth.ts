import { config, SELF_USER_ID } from "./config";
import { encryptToken, decryptToken } from "./crypto";
import { getStore } from "./store";

const OAUTH_BASE = "https://threads.net";
const GRAPH_BASE = "https://graph.threads.net";

// 長效 token 約 60 天；剩餘少於這天數就提前續期。
const REFRESH_THRESHOLD_DAYS = 7;

/** 組授權頁網址 */
export function buildAuthorizeUrl(redirectUri: string, state: string): string {
  const url = new URL(`${OAUTH_BASE}/oauth/authorize`);
  url.searchParams.set("client_id", config.threads.appId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("scope", config.threads.scopes.join(","));
  url.searchParams.set("response_type", "code");
  url.searchParams.set("state", state);
  return url.toString();
}

/** 由 origin 推導 redirect uri（可被 env 覆寫） */
export function resolveRedirectUri(origin: string): string {
  return config.threads.redirectUri || `${origin}/api/auth/threads/callback`;
}

/** 用授權碼換短效 token（含 user_id） */
async function exchangeCode(
  code: string,
  redirectUri: string,
): Promise<{ accessToken: string; userId: string }> {
  const body = new URLSearchParams({
    client_id: config.threads.appId,
    client_secret: config.threads.appSecret,
    grant_type: "authorization_code",
    redirect_uri: redirectUri,
    code,
  });
  const res = await fetch(`${GRAPH_BASE}/oauth/access_token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error(`換取 token 失敗 (${res.status}): ${await res.text()}`);
  const json = (await res.json()) as { access_token: string; user_id: string };
  return { accessToken: json.access_token, userId: String(json.user_id) };
}

/** 短效 → 長效（約 60 天） */
async function exchangeLongLived(
  shortToken: string,
): Promise<{ accessToken: string; expiresIn: number }> {
  const url = new URL(`${GRAPH_BASE}/access_token`);
  url.searchParams.set("grant_type", "th_exchange_token");
  url.searchParams.set("client_secret", config.threads.appSecret);
  url.searchParams.set("access_token", shortToken);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`換取長效 token 失敗 (${res.status}): ${await res.text()}`);
  const json = (await res.json()) as { access_token: string; expires_in: number };
  return { accessToken: json.access_token, expiresIn: json.expires_in };
}

/** 續期長效 token */
async function refreshLongLived(
  longToken: string,
): Promise<{ accessToken: string; expiresIn: number }> {
  const url = new URL(`${GRAPH_BASE}/refresh_access_token`);
  url.searchParams.set("grant_type", "th_refresh_token");
  url.searchParams.set("access_token", longToken);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`續期 token 失敗 (${res.status}): ${await res.text()}`);
  const json = (await res.json()) as { access_token: string; expires_in: number };
  return { accessToken: json.access_token, expiresIn: json.expires_in };
}

async function fetchUsername(token: string, userId: string): Promise<string | null> {
  try {
    const url = new URL(`${GRAPH_BASE}/${config.threads.apiVersion}/${userId}`);
    url.searchParams.set("fields", "username");
    url.searchParams.set("access_token", token);
    const res = await fetch(url.toString());
    if (!res.ok) return null;
    return ((await res.json()) as { username?: string }).username ?? null;
  } catch {
    return null;
  }
}

/** 完成 OAuth：用授權碼換長效 token 並（加密）存入 DB */
export async function completeOAuth(code: string, redirectUri: string): Promise<void> {
  const short = await exchangeCode(code, redirectUri);
  const long = await exchangeLongLived(short.accessToken);
  const username = await fetchUsername(long.accessToken, short.userId);
  await getStore().saveAuthUser(SELF_USER_ID, {
    access_token: encryptToken(long.accessToken),
    threads_user_id: short.userId,
    username,
    token_expires_at: new Date(Date.now() + long.expiresIn * 1000).toISOString(),
  });
}

/**
 * 取得可用的 access token + userId。
 * 優先用 DB 的長效 token（必要時自動續期）；沒有就退回 env token；都沒有則 null。
 */
export async function resolveThreadsToken(): Promise<{ token: string; userId: string } | null> {
  const store = getStore();
  const auth = await store.getAuthUser(SELF_USER_ID);

  if (auth?.access_token) {
    let token = decryptToken(auth.access_token);
    // 快到期 → 嘗試續期
    if (auth.token_expires_at) {
      const msLeft = new Date(auth.token_expires_at).getTime() - Date.now();
      if (msLeft < REFRESH_THRESHOLD_DAYS * 86_400_000 && msLeft > 0) {
        try {
          const refreshed = await refreshLongLived(token);
          token = refreshed.accessToken;
          await store.saveAuthUser(SELF_USER_ID, {
            access_token: encryptToken(token),
            threads_user_id: auth.threads_user_id,
            username: auth.username,
            token_expires_at: new Date(
              Date.now() + refreshed.expiresIn * 1000,
            ).toISOString(),
          });
        } catch {
          // 續期失敗就先用舊的，下次再試
        }
      }
    }
    return { token, userId: auth.threads_user_id || config.threads.userId };
  }

  // 後備：手動 env token
  if (config.threads.accessToken) {
    return { token: config.threads.accessToken, userId: config.threads.userId };
  }
  return null;
}

/** 給 status 用的連線狀態（不發網路請求） */
export async function getThreadsConnection(): Promise<{
  connected: boolean;
  username: string | null;
  source: "oauth" | "env" | null;
}> {
  const auth = await getStore().getAuthUser(SELF_USER_ID);
  if (auth?.access_token) {
    return { connected: true, username: auth.username, source: "oauth" };
  }
  if (config.threads.accessToken) {
    return { connected: true, username: null, source: "env" };
  }
  return { connected: false, username: null, source: null };
}
