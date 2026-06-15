-- ════════════════════════════════════════════════════════════════
-- 脈脈 Threads 助手 — Supabase 初版 schema
-- 在 Supabase SQL Editor 直接執行即可建表。
-- ════════════════════════════════════════════════════════════════

-- 啟用 UUID 產生器
create extension if not exists "pgcrypto";

-- ── 使用者與授權 ────────────────────────────────────────────────
-- Phase 1 自用時可只放一筆 id='self'。Phase 2 改成 OAuth 多使用者。
create table if not exists users (
  id              text primary key,
  threads_user_id text,
  -- access_token 屬敏感資料：請用 Supabase Vault 或應用層加密後再存，
  -- 絕不可放進前端或 URL。此欄位僅存密文。
  access_token    text,
  created_at      timestamptz not null default now()
);

-- ── 熱門文快取（依 主題 + 日期）────────────────────────────────
create table if not exists topic_cache (
  id           uuid primary key default gen_random_uuid(),
  topic        text not null,
  fetched_date date not null default current_date,
  posts        jsonb not null default '[]'::jsonb,
  cached_at    timestamptz not null default now(),
  unique (topic, fetched_date)
);

create index if not exists topic_cache_lookup
  on topic_cache (topic, fetched_date);

-- ── 草稿匣 ──────────────────────────────────────────────────────
create table if not exists drafts (
  id         uuid primary key default gen_random_uuid(),
  user_id    text not null,
  topic      text not null default '',
  content    text not null,
  style      text not null default 'story',
  char_count integer not null default 0,
  status     text not null default 'draft', -- draft | published
  created_at timestamptz not null default now()
);

create index if not exists drafts_by_user on drafts (user_id, created_at desc);

-- ── 已發佈紀錄 ──────────────────────────────────────────────────
create table if not exists published_posts (
  id              uuid primary key default gen_random_uuid(),
  user_id         text not null,
  draft_id        uuid references drafts (id) on delete set null,
  threads_post_id text not null,
  permalink       text,
  published_at    timestamptz not null default now()
);

create index if not exists published_by_user on published_posts (user_id, published_at desc);

-- ════════════════════════════════════════════════════════════════
-- Row Level Security（Phase 2 多使用者時啟用）
-- 後端目前用 service_role key 存取（繞過 RLS）。導入使用者登入後，
-- 改用 anon key + 下列政策，讓每位使用者只能看自己的資料。
-- ════════════════════════════════════════════════════════════════
-- alter table drafts enable row level security;
-- alter table published_posts enable row level security;
-- create policy "own drafts" on drafts
--   for all using (auth.uid()::text = user_id) with check (auth.uid()::text = user_id);
-- create policy "own published" on published_posts
--   for all using (auth.uid()::text = user_id) with check (auth.uid()::text = user_id);
