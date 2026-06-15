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
    <button
      onClick={onToggle}
      className={`card w-full p-4 text-left transition ${
        selected ? "ring-2 ring-gray-900" : "hover:border-gray-300"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-bold text-gray-600">
          {post.username.slice(0, 2).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold">@{post.username}</div>
          <div className="text-xs text-gray-400">{timeAgo(post.timestamp)} · 🔥 TOP</div>
        </div>
        <span
          className={`flex h-5 w-5 items-center justify-center rounded-full border text-xs ${
            selected
              ? "border-gray-900 bg-gray-900 text-white"
              : "border-gray-300 text-transparent"
          }`}
        >
          ✓
        </span>
      </div>

      <p className="mt-2 line-clamp-6 whitespace-pre-wrap text-sm text-gray-700">
        {post.text}
      </p>

      <a
        href={post.permalink}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className="mt-2 inline-block text-xs text-gray-400 hover:text-gray-900 hover:underline"
      >
        在 Threads 上查看 ↗
      </a>
    </button>
  );
}
