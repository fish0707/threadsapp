"use client";

import { useEffect, useState } from "react";

interface ThreadsStatus {
  connected: boolean;
  username: string | null;
  source: "oauth" | "env" | null;
  oauthAvailable: boolean;
}

export default function ThreadsConnect() {
  const [status, setStatus] = useState<ThreadsStatus | null>(null);
  const [notice, setNotice] = useState<{ type: "ok" | "err"; msg: string } | null>(null);

  async function load() {
    try {
      const r = await fetch("/api/status").then((x) => x.json());
      setStatus(r.threads);
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    load();
    // 讀取 callback 帶回的結果
    const sp = new URLSearchParams(window.location.search);
    if (sp.get("threads_connected")) {
      setNotice({ type: "ok", msg: "Threads 帳號已連結成功！" });
    } else if (sp.get("threads_error")) {
      setNotice({ type: "err", msg: `連結失敗：${sp.get("threads_error")}` });
    }
    if (sp.get("threads_connected") || sp.get("threads_error")) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  async function disconnect() {
    await fetch("/api/auth/threads/disconnect", { method: "POST" });
    setNotice({ type: "ok", msg: "已解除 Threads 連結" });
    load();
  }

  if (!status) return null;

  return (
    <section className="card flex flex-wrap items-center justify-between gap-3 p-4">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-lg">🧵</span>
        {status.connected ? (
          <span>
            已連結 Threads
            {status.username && <b className="ml-1">@{status.username}</b>}
            {status.source === "env" && (
              <span className="ml-1 text-gray-400">（env token）</span>
            )}
            <span className="ml-1 text-green-600">●</span>
          </span>
        ) : (
          <span className="text-gray-600">尚未連結 Threads 帳號（搜尋與發佈為 mock）</span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {notice && (
          <span
            className={`text-xs ${notice.type === "ok" ? "text-green-600" : "text-red-600"}`}
          >
            {notice.msg}
          </span>
        )}
        {status.connected ? (
          status.source === "oauth" && (
            <button className="btn-ghost" onClick={disconnect}>
              解除連結
            </button>
          )
        ) : status.oauthAvailable ? (
          <a className="btn-primary" href="/api/auth/threads/login">
            連結 Threads 帳號
          </a>
        ) : (
          <span className="text-xs text-amber-600">
            尚未設定 THREADS_APP_ID / SECRET，無法 OAuth
          </span>
        )}
      </div>
    </section>
  );
}
