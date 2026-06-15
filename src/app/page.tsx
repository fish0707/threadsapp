"use client";

import { useState } from "react";
import MockBanner from "@/components/MockBanner";
import PostCard from "@/components/PostCard";
import PublishModal from "@/components/PublishModal";
import { api } from "@/lib/client";
import { DRAFT_STYLES, type AiMode, type DraftStyle, type ThreadsPost } from "@/lib/types";

const QUICK_TOPICS = ["理財", "健身", "AI 工具", "職場", "親子", "美食"];

export default function HomePage() {
  // ── 搜尋 ──
  const [topic, setTopic] = useState("");
  const [searchMode, setSearchMode] = useState<"KEYWORD" | "TAG">("KEYWORD");
  const [posts, setPosts] = useState<ThreadsPost[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [searchMeta, setSearchMeta] = useState<{ cached: boolean; mocked: boolean } | null>(null);

  // ── 生成設定 ──
  const [style, setStyle] = useState<DraftStyle>("story");
  const [mode, setMode] = useState<AiMode>("gemini");
  const [count, setCount] = useState(3);
  const [generating, setGenerating] = useState(false);
  const [drafts, setDrafts] = useState<{ content: string; style: DraftStyle }[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [publishTarget, setPublishTarget] = useState<string | null>(null);

  async function handleSearch(t?: string, force = false) {
    const q = (t ?? topic).trim();
    if (!q) return;
    if (t) setTopic(t);
    setSearching(true);
    setError(null);
    setSelected(new Set());
    try {
      const res = await api.search(q, searchMode, force);
      setPosts(res.posts);
      setSearched(true);
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
      setDrafts(res.drafts.map((content) => ({ content, style })));
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失敗");
    } finally {
      setGenerating(false);
    }
  }

  async function saveDraft(content: string, s: DraftStyle) {
    try {
      await api.saveDraft({ topic: topic.trim(), content, style: s });
      flash("已存入草稿匣");
    } catch (e) {
      setError(e instanceof Error ? e.message : "儲存失敗");
    }
  }

  function flash(msg: string) {
    setSavedMsg(msg);
    setTimeout(() => setSavedMsg(null), 2000);
  }

  // ───────────────────────── Hero（尚未搜尋）─────────────────────────
  if (!searched) {
    return (
      <div className="space-y-6">
        <MockBanner />
        <section className="mx-auto max-w-2xl pt-10 text-center">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-500">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            今日 Threads 熱度・即時追蹤
          </p>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            今天想經營什麼主題？
          </h1>
          <p className="mx-auto mt-4 max-w-md text-gray-500">
            輸入主題，我幫你抓今天的熱門貼文，再換句話說生成屬於你的貼文。
          </p>

          <div className="mx-auto mt-8 flex max-w-xl flex-col gap-2 sm:flex-row">
            <input
              className="input"
              placeholder="例：職場、理財、健身、AI 工具"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              autoFocus
            />
            <select
              className="input sm:w-28"
              value={searchMode}
              onChange={(e) => setSearchMode(e.target.value as "KEYWORD" | "TAG")}
            >
              <option value="KEYWORD">關鍵字</option>
              <option value="TAG">標籤</option>
            </select>
            <button
              className="btn-primary sm:w-32"
              onClick={() => handleSearch()}
              disabled={searching}
            >
              {searching ? "搜尋中…" : "搜尋熱門"}
            </button>
          </div>

          <div className="mt-8">
            <p className="mb-3 text-xs text-gray-400">或從你的主題開始</p>
            <div className="flex flex-wrap justify-center gap-2">
              {QUICK_TOPICS.map((t) => (
                <button key={t} className="chip" onClick={() => handleSearch(t)}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="mx-auto mt-6 max-w-xl rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700">
              {error}
            </div>
          )}
        </section>
      </div>
    );
  }

  // ───────────────────────── 搜尋後：雙欄 ─────────────────────────
  return (
    <div className="space-y-5">
      <MockBanner />

      {/* 緊湊搜尋列 */}
      <section className="card flex flex-col gap-2 p-4 sm:flex-row sm:items-center">
        <input
          className="input"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <select
          className="input sm:w-28"
          value={searchMode}
          onChange={(e) => setSearchMode(e.target.value as "KEYWORD" | "TAG")}
        >
          <option value="KEYWORD">關鍵字</option>
          <option value="TAG">標籤</option>
        </select>
        <button
          className="btn-primary sm:w-28"
          onClick={() => handleSearch()}
          disabled={searching}
        >
          {searching ? "搜尋中…" : "搜尋"}
        </button>
      </section>

      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700">{error}</div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {/* 左：靈感動態（熱門文） */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold">靈感動態</h2>
            <span className="text-xs text-gray-400">
              已選 {selected.size} 篇 · 點卡片加入參考
            </span>
          </div>

          {searchMeta && (
            <p className="flex items-center gap-2 text-xs text-gray-400">
              {searchMeta.cached ? "📦 來自今日快取（省 API 額度）" : "🔄 即時查詢"}
              {searchMeta.mocked && " · 範例資料"}
              {searchMeta.cached && (
                <button
                  className="text-brand-accent hover:underline"
                  onClick={() => handleSearch(undefined, true)}
                >
                  略過快取重查
                </button>
              )}
            </p>
          )}

          {posts.length > 0 ? (
            <div className="space-y-3">
              {posts.map((p) => (
                <PostCard
                  key={p.id}
                  post={p}
                  selected={selected.has(p.id)}
                  onToggle={() => toggle(p.id)}
                />
              ))}
            </div>
          ) : (
            <div className="card p-5 text-sm text-gray-600">
              <p className="font-medium">沒有搜尋到貼文</p>
              <p className="mt-1 text-gray-500">
                keyword_search 在通過 Meta 審核前，只會搜到你自己帳號的貼文。
                審核通過後即可搜到公開熱門文。不影響右側直接生成草稿。
              </p>
            </div>
          )}
        </section>

        {/* 右：AI 生成 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold">AI 生成</h2>

          <div className="card space-y-3 p-4">
            <div className="grid grid-cols-2 gap-2">
              {DRAFT_STYLES.map((s) => (
                <button
                  key={s.value}
                  onClick={() => setStyle(s.value)}
                  className={`rounded-xl border p-2.5 text-left transition ${
                    style === s.value
                      ? "border-gray-900 bg-gray-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="text-sm font-medium">{s.label}</div>
                  <div className="mt-0.5 text-[11px] text-gray-500">{s.hint}</div>
                </button>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <select
                className="input w-36"
                value={mode}
                onChange={(e) => setMode(e.target.value as AiMode)}
              >
                <option value="gemini">Gemini（快）</option>
                <option value="claude">Claude（高品質）</option>
              </select>
              <select
                className="input w-24"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n} 篇
                  </option>
                ))}
              </select>
              <button
                className="btn-primary flex-1"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? "生成中…" : "✨ 生成草稿"}
              </button>
            </div>
          </div>

          {drafts.map((d, i) => (
            <DraftResult
              key={i}
              content={d.content}
              styleValue={d.style}
              onSave={saveDraft}
              onCopy={() => flash("已複製")}
              onPublish={(edited) => setPublishTarget(edited)}
            />
          ))}

          {drafts.length === 0 && !generating && (
            <div className="card p-8 text-center text-sm text-gray-400">
              選好風格後按「生成草稿」，結果會顯示在這裡。
            </div>
          )}
        </section>
      </div>

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
  content,
  styleValue,
  onSave,
  onCopy,
  onPublish,
}: {
  content: string;
  styleValue: DraftStyle;
  onSave: (content: string, style: DraftStyle) => void;
  onCopy: () => void;
  onPublish: (content: string) => void;
}) {
  const [text, setText] = useState(content);
  const label = DRAFT_STYLES.find((s) => s.value === styleValue)?.label ?? styleValue;

  return (
    <div className="card p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="badge">{label}</span>
        <span className="text-xs text-gray-400">{[...text].length} 字</span>
      </div>
      <textarea
        className="input min-h-[120px] resize-y"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="btn-primary" onClick={() => onPublish(text)}>
          發佈到 Threads
        </button>
        <button className="btn-ghost" onClick={() => onSave(text, styleValue)}>
          存草稿
        </button>
        <button
          className="btn-ghost"
          onClick={() => {
            navigator.clipboard.writeText(text);
            onCopy();
          }}
        >
          複製
        </button>
      </div>
    </div>
  );
}
