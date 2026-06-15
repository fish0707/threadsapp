"use client";

import { useState } from "react";
import MockBanner from "@/components/MockBanner";
import ThreadsConnect from "@/components/ThreadsConnect";
import PostCard from "@/components/PostCard";
import PublishModal from "@/components/PublishModal";
import { api } from "@/lib/client";
import { DRAFT_STYLES, type AiMode, type DraftStyle, type ThreadsPost } from "@/lib/types";

export default function HomePage() {
  // ── 搜尋 ──
  const [topic, setTopic] = useState("");
  const [searchMode, setSearchMode] = useState<"KEYWORD" | "TAG">("KEYWORD");
  const [posts, setPosts] = useState<ThreadsPost[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [searching, setSearching] = useState(false);
  const [searchMeta, setSearchMeta] = useState<{ cached: boolean; mocked: boolean } | null>(null);

  // ── 生成設定 ──
  const [style, setStyle] = useState<DraftStyle>("story");
  const [mode, setMode] = useState<AiMode>("gemini");
  const [count, setCount] = useState(3);
  const [generating, setGenerating] = useState(false);
  const [drafts, setDrafts] = useState<string[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [publishTarget, setPublishTarget] = useState<string | null>(null);

  async function handleSearch() {
    if (!topic.trim()) return;
    setSearching(true);
    setError(null);
    setSelected(new Set());
    setDrafts([]);
    try {
      const res = await api.search(topic.trim(), searchMode);
      setPosts(res.posts);
      setSearchMeta({ cached: res.cached, mocked: res.mocked });
    } catch (e) {
      setError(e instanceof Error ? e.message : "搜尋失敗");
    } finally {
      setSearching(false);
    }
  }

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const references = posts.filter((p) => selected.has(p.id));
      const res = await api.generate({ topic: topic.trim(), references, style, mode, count });
      setDrafts(res.drafts);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失敗");
    } finally {
      setGenerating(false);
    }
  }

  async function saveDraft(content: string) {
    try {
      await api.saveDraft({ topic: topic.trim(), content, style });
      flash("已存入草稿匣");
    } catch (e) {
      setError(e instanceof Error ? e.message : "儲存失敗");
    }
  }

  function flash(msg: string) {
    setSavedMsg(msg);
    setTimeout(() => setSavedMsg(null), 2000);
  }

  return (
    <div className="space-y-6">
      <MockBanner />
      <ThreadsConnect />

      {/* 步驟一：輸入主題 */}
      <section className="card p-5">
        <h2 className="mb-3 text-lg font-bold">① 輸入主題，抓當天熱門文</h2>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input"
            placeholder="例：職場、理財、健身、AI 工具"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <select
            className="input sm:w-32"
            value={searchMode}
            onChange={(e) => setSearchMode(e.target.value as "KEYWORD" | "TAG")}
          >
            <option value="KEYWORD">關鍵字</option>
            <option value="TAG">主題標籤</option>
          </select>
          <button className="btn-primary sm:w-32" onClick={handleSearch} disabled={searching}>
            {searching ? "搜尋中…" : "搜尋熱門"}
          </button>
        </div>
        {searchMeta && (
          <p className="mt-2 text-xs text-gray-500">
            {searchMeta.cached ? "📦 來自今日快取（省 API 額度）" : "🔄 即時查詢"}
            {searchMeta.mocked && " · 範例資料"}
          </p>
        )}
      </section>

      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700">{error}</div>
      )}

      {/* 步驟二：勾選參考文 */}
      {posts.length > 0 && (
        <section className="card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-bold">② 勾選參考素材</h2>
            <span className="text-sm text-gray-500">已選 {selected.size} 篇</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {posts.map((p) => (
              <PostCard
                key={p.id}
                post={p}
                selected={selected.has(p.id)}
                onToggle={() => toggle(p.id)}
              />
            ))}
          </div>
        </section>
      )}

      {/* 步驟三：生成設定 */}
      {posts.length > 0 && (
        <section className="card p-5">
          <h2 className="mb-3 text-lg font-bold">③ 選風格，AI 生成草稿</h2>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {DRAFT_STYLES.map((s) => (
              <button
                key={s.value}
                onClick={() => setStyle(s.value)}
                className={`rounded-lg border p-3 text-left transition ${
                  style === s.value
                    ? "border-brand-accent bg-indigo-50"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="text-sm font-medium">{s.label}</div>
                <div className="mt-0.5 text-xs text-gray-500">{s.hint}</div>
              </button>
            ))}
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              模型
              <select
                className="input w-40"
                value={mode}
                onChange={(e) => setMode(e.target.value as AiMode)}
              >
                <option value="gemini">Gemini（主力・快）</option>
                <option value="claude">Claude（高品質）</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              生成數量
              <select
                className="input w-20"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <button className="btn-primary" onClick={handleGenerate} disabled={generating}>
              {generating ? "生成中…" : "✨ 生成草稿"}
            </button>
          </div>
        </section>
      )}

      {/* 步驟四：草稿結果 */}
      {drafts.length > 0 && (
        <section className="card p-5">
          <h2 className="mb-3 text-lg font-bold">④ 草稿結果</h2>
          <div className="space-y-3">
            {drafts.map((d, i) => (
              <DraftResult
                key={i}
                index={i}
                content={d}
                onSave={saveDraft}
                onCopy={() => flash("已複製")}
                onPublish={(edited) => setPublishTarget(edited)}
              />
            ))}
          </div>
        </section>
      )}

      {savedMsg && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 rounded-full bg-gray-900 px-4 py-2 text-sm text-white shadow-lg">
          {savedMsg}
        </div>
      )}

      {publishTarget !== null && (
        <PublishModal content={publishTarget} onClose={() => setPublishTarget(null)} />
      )}
    </div>
  );
}

function DraftResult({
  index,
  content,
  onSave,
  onCopy,
  onPublish,
}: {
  index: number;
  content: string;
  onSave: (content: string) => void;
  onCopy: () => void;
  onPublish: (content: string) => void;
}) {
  const [text, setText] = useState(content);
  return (
    <div className="rounded-lg border border-gray-200 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500">草稿 {index + 1}</span>
        <span className="text-xs text-gray-400">{[...text].length} 字</span>
      </div>
      <textarea
        className="input min-h-[120px] resize-y"
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
        <button className="btn-ghost" onClick={() => onSave(text)}>
          存入草稿匣
        </button>
        <button className="btn-primary" onClick={() => onPublish(text)}>
          發佈
        </button>
      </div>
    </div>
  );
}
