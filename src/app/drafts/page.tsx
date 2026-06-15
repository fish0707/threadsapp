"use client";

import { useEffect, useState } from "react";
import MockBanner from "@/components/MockBanner";
import PublishModal from "@/components/PublishModal";
import { api } from "@/lib/client";
import { DRAFT_STYLES, type Draft } from "@/lib/types";

const styleLabel = (v: string) =>
  DRAFT_STYLES.find((s) => s.value === v)?.label ?? v;

export default function DraftsPage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [publishTarget, setPublishTarget] = useState<Draft | null>(null);

  async function load() {
    setLoading(true);
    try {
      const res = await api.listDrafts();
      setDrafts(res.drafts);
    } catch (e) {
      setError(e instanceof Error ? e.message : "讀取失敗");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function flash(m: string) {
    setMsg(m);
    setTimeout(() => setMsg(null), 2000);
  }

  async function save(id: string, content: string) {
    await api.updateDraft(id, { content });
    flash("已儲存");
    load();
  }

  async function remove(id: string) {
    await api.deleteDraft(id);
    setDrafts((d) => d.filter((x) => x.id !== id));
    flash("已刪除");
  }

  return (
    <div className="space-y-4">
      <MockBanner />
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">草稿匣</h1>
        <span className="text-sm text-gray-500">{drafts.length} 篇</span>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">讀取中…</p>
      ) : drafts.length === 0 ? (
        <div className="card p-8 text-center text-gray-500">
          目前沒有草稿。到「生成」頁產生草稿後，點「存入草稿匣」即可在這裡管理。
        </div>
      ) : (
        <div className="space-y-3">
          {drafts.map((d) => (
            <DraftRow
              key={d.id}
              draft={d}
              onSave={save}
              onDelete={remove}
              onCopy={() => flash("已複製")}
              onPublish={() => setPublishTarget(d)}
            />
          ))}
        </div>
      )}

      {msg && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 rounded-full bg-gray-900 px-4 py-2 text-sm text-white shadow-lg">
          {msg}
        </div>
      )}

      {publishTarget && (
        <PublishModal
          content={publishTarget.content}
          draftId={publishTarget.id}
          onClose={() => setPublishTarget(null)}
          onPublished={() => load()}
        />
      )}
    </div>
  );
}

function DraftRow({
  draft,
  onSave,
  onDelete,
  onCopy,
  onPublish,
}: {
  draft: Draft;
  onSave: (id: string, content: string) => void;
  onDelete: (id: string) => void;
  onCopy: () => void;
  onPublish: () => void;
}) {
  const [text, setText] = useState(draft.content);
  const dirty = text !== draft.content;

  return (
    <div className="card p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-gray-500">
        <span className="rounded-full bg-gray-100 px-2 py-0.5">{styleLabel(draft.style)}</span>
        {draft.topic && <span className="rounded-full bg-gray-100 px-2 py-0.5">#{draft.topic}</span>}
        {draft.status === "published" && (
          <span className="rounded-full bg-green-100 px-2 py-0.5 text-green-700">已發佈</span>
        )}
        <span className="ml-auto">{[...text].length} 字</span>
      </div>
      <textarea
        className="input min-h-[100px] resize-y"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="mt-2 flex flex-wrap gap-2">
        <button
          className="btn-ghost"
          onClick={() => {
            navigator.clipboard.writeText(text);
            onCopy();
          }}
        >
          複製
        </button>
        <button
          className="btn-ghost"
          disabled={!dirty}
          onClick={() => onSave(draft.id, text)}
        >
          儲存修改
        </button>
        <button
          className="btn-ghost text-red-600"
          onClick={() => onDelete(draft.id)}
        >
          刪除
        </button>
        <button className="btn-primary ml-auto" onClick={onPublish}>
          發佈
        </button>
      </div>
    </div>
  );
}
