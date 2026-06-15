"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/client";
import type { ThreadsPost } from "@/lib/types";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return `${Math.max(1, Math.floor(diff / 60_000))} 分鐘前`;
  if (h < 24) return `${h} 小時前`;
  return `${Math.floor(h / 24)} 天前`;
}

export default function FeedPage() {
  const [topic, setTopic] = useState("");
  const [posts, setPosts] = useState<ThreadsPost[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    if (!topic.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.search(topic.trim());
      setPosts(res.posts);
      setSearched(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "搜尋失敗");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">靈感動態</h1>
        <Link href="/" className="btn-ghost">
          到聚集搜尋生成 →
        </Link>
      </div>
      <p className="text-sm text-gray-500">瀏覽某主題當天的 Threads 熱門貼文，找靈感。</p>

      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          className="input"
          placeholder="輸入主題，例：職場"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <button className="btn-primary sm:w-28" onClick={search} disabled={loading}>
          {loading ? "搜尋中…" : "搜尋"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700">{error}</div>
      )}

      {searched && posts.length === 0 && (
        <div className="card p-5 text-sm text-gray-600">
          沒有搜尋到貼文（keyword_search 審核通過前只搜得到自己帳號的貼文）。
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {posts.map((p) => (
          <a
            key={p.id}
            href={p.permalink}
            target="_blank"
            rel="noopener noreferrer"
            className="card p-4 transition hover:border-gray-300"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-bold text-gray-600">
                {p.username.slice(0, 2).toUpperCase()}
              </span>
              <div>
                <div className="text-sm font-semibold">@{p.username}</div>
                <div className="text-xs text-gray-400">{timeAgo(p.timestamp)} · 🔥 TOP</div>
              </div>
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm text-gray-700">{p.text}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
