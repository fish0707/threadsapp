"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

interface ThreadsStatus {
  connected: boolean;
  username: string | null;
  oauthAvailable: boolean;
}

const TABS = [
  { href: "/", label: "聚集搜尋" },
  { href: "/feed", label: "靈感動態" },
  { href: "/dashboard", label: "工作儀表板" },
];

export default function Header() {
  const pathname = usePathname();
  const [draftCount, setDraftCount] = useState<number | null>(null);
  const [threads, setThreads] = useState<ThreadsStatus | null>(null);

  useEffect(() => {
    fetch("/api/drafts")
      .then((r) => r.json())
      .then((d) => setDraftCount(d.drafts?.length ?? 0))
      .catch(() => {});
    fetch("/api/status")
      .then((r) => r.json())
      .then((d) => setThreads(d.threads))
      .catch(() => {});
  }, [pathname]);

  return (
    <header className="sticky top-0 z-20 border-b border-gray-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
        {/* 品牌 */}
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl">🧵</span>
          <span className="leading-tight">
            <span className="block text-sm font-bold">脈脈</span>
            <span className="block text-[11px] text-gray-400">Threads 經營助手</span>
          </span>
        </Link>

        {/* 中央分頁 */}
        <nav className="ml-2 hidden items-center gap-1 sm:flex">
          {TABS.map((t) => {
            const active = pathname === t.href;
            return (
              <Link
                key={t.href}
                href={t.href}
                className={`navtab ${active ? "navtab-active" : ""}`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>

        {/* 右側 */}
        <div className="ml-auto flex items-center gap-2">
          <Link href="/drafts" className="btn-ghost">
            草稿匣
            {draftCount !== null && (
              <span className="ml-1 rounded-full bg-gray-900 px-1.5 text-xs text-white">
                {draftCount}
              </span>
            )}
          </Link>

          {threads?.connected ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-green-200 bg-green-50 px-3 py-1.5 text-sm text-green-700">
              <span className="h-2 w-2 rounded-full bg-green-500" />
              {threads.username ? `@${threads.username}` : "已連結"}
            </span>
          ) : threads?.oauthAvailable ? (
            <a href="/api/auth/threads/login" className="btn-primary">
              + 連結 Threads
            </a>
          ) : null}
        </div>
      </div>

      {/* 手機版分頁 */}
      <nav className="flex items-center gap-1 overflow-x-auto px-4 pb-2 sm:hidden">
        {TABS.map((t) => {
          const active = pathname === t.href;
          return (
            <Link
              key={t.href}
              href={t.href}
              className={`navtab whitespace-nowrap ${active ? "navtab-active" : ""}`}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
