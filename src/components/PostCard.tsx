"use client";

import type { ThreadsPost } from "@/lib/types";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return `${Math.max(1, Math.floor(diff / 60_000))} 分鐘前`;
  if (h < 24) return `${h} 小時前`;
  return `${Math.floor(h / 24)} 天前`;
}

export default function PostCard({
  post,
  selected,
  onToggle,
}: {
  post: ThreadsPost;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <label
      className={`card block cursor-pointer p-4 transition ${
        selected ? "ring-2 ring-brand-accent" : "hover:border-gray-300"
      }`}
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          className="mt-1 h-4 w-4 accent-brand-accent"
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-gray-900">@{post.username}</span>
            <span className="text-xs text-gray-400">{timeAgo(post.timestamp)}</span>
          </div>
          <p className="mt-1 whitespace-pre-wrap text-sm text-gray-700">{post.text}</p>
          <a
            href={post.permalink}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="mt-2 inline-block text-xs text-brand-accent hover:underline"
          >
            在 Threads 上查看 ↗
          </a>
        </div>
      </div>
    </label>
  );
}
