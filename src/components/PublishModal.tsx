"use client";

import { useState } from "react";
import { api } from "@/lib/client";

export default function PublishModal({
  content,
  draftId,
  onClose,
  onPublished,
}: {
  content: string;
  draftId?: string;
  onClose: () => void;
  onPublished?: (permalink?: string) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ permalink?: string; mocked: boolean } | null>(null);

  async function handlePublish() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.publish({ content, draftId });
      setDone({ permalink: res.permalink, mocked: res.mocked });
      onPublished?.(res.permalink);
    } catch (e) {
      setError(e instanceof Error ? e.message : "發佈失敗");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="card w-full max-w-lg p-5">
        <h3 className="text-lg font-bold">發佈前預覽</h3>
        <p className="mt-1 text-xs text-gray-500">
          請確認內容無誤再發佈，避免誤發。
        </p>

        <div className="mt-3 max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
          {content}
        </div>
        <div className="mt-1 text-right text-xs text-gray-400">
          {[...content].length} 字
        </div>

        {error && (
          <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {done ? (
          <div className="mt-3 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-700">
            ✅ {done.mocked ? "（mock）已模擬發佈成功" : "已發佈到 Threads"}
            {done.permalink && (
              <>
                {" — "}
                <a
                  href={done.permalink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                >
                  查看貼文 ↗
                </a>
              </>
            )}
          </div>
        ) : null}

        <div className="mt-4 flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>
            {done ? "關閉" : "取消"}
          </button>
          {!done && (
            <button className="btn-primary" onClick={handlePublish} disabled={loading}>
              {loading ? "發佈中…" : "確認發佈"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
