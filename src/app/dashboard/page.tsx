"use client";

import { useEffect, useState } from "react";

interface Stats {
  draftCount: number;
  publishedCount: number;
  byStyle: { style: string; label: string; count: number }[];
  recentPublished: {
    id: string;
    threads_post_id: string;
    permalink?: string;
    published_at: string;
  }[];
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});
  }, []);

  const maxStyle = Math.max(1, ...(stats?.byStyle.map((s) => s.count) ?? [1]));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">工作儀表板</h1>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard label="累積草稿" value={stats?.draftCount ?? "—"} icon="📝" />
        <StatCard label="已發佈貼文" value={stats?.publishedCount ?? "—"} icon="🚀" />
      </div>

      <section className="card p-5">
        <h2 className="mb-4 text-lg font-bold">各風格草稿數</h2>
        <div className="space-y-3">
          {stats?.byStyle.map((s) => (
            <div key={s.style} className="flex items-center gap-3">
              <span className="w-24 shrink-0 text-sm text-gray-600">{s.label}</span>
              <div className="h-3 flex-1 overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full rounded-full bg-gray-900"
                  style={{ width: `${(s.count / maxStyle) * 100}%` }}
                />
              </div>
              <span className="w-8 text-right text-sm tabular-nums">{s.count}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-5">
        <h2 className="mb-4 text-lg font-bold">最近發佈</h2>
        {stats && stats.recentPublished.length > 0 ? (
          <ul className="divide-y divide-gray-100">
            {stats.recentPublished.map((p) => (
              <li key={p.id} className="flex items-center justify-between py-2.5 text-sm">
                <span className="text-gray-500">
                  {new Date(p.published_at).toLocaleString("zh-TW")}
                </span>
                {p.permalink ? (
                  <a
                    href={p.permalink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-brand-accent hover:underline"
                  >
                    查看貼文 ↗
                  </a>
                ) : (
                  <span className="text-gray-400">{p.threads_post_id}</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">尚無發佈紀錄。</p>
        )}
      </section>

      <p className="text-xs text-gray-400">
        備註：Threads keyword_search 不提供互動數（讚 / 回覆 / 轉發），成效細項追蹤將於
        Phase 2 評估第三方資料源後加入。
      </p>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number | string;
  icon: string;
}) {
  return (
    <div className="card flex items-center gap-4 p-5">
      <span className="text-3xl">{icon}</span>
      <div>
        <div className="text-3xl font-extrabold tabular-nums">{value}</div>
        <div className="text-sm text-gray-500">{label}</div>
      </div>
    </div>
  );
}
