import { config } from "./config";
import { buildGenerationPrompt, splitDrafts, STYLE_INSTRUCTIONS } from "./prompts";
import type { AiMode, GenerateRequest } from "./types";

export interface GenerateResult {
  drafts: string[];
  usedMode: AiMode | "mock";
}

/**
 * 生成草稿主入口。依 mode 與金鑰狀態挑選實作：
 *  - claude：有 ANTHROPIC_API_KEY → Claude；否則退回 gemini。
 *  - gemini：有 GEMINI_API_KEY → Gemini；否則 mock。
 */
export async function generateDrafts(req: GenerateRequest): Promise<GenerateResult> {
  const count = req.count ?? 3;
  const { system, user } = buildGenerationPrompt({
    topic: req.topic,
    references: req.references,
    style: req.style,
    count,
  });

  // 高品質模式：Claude
  if (req.mode === "claude" && config.claude.enabled) {
    const raw = await callClaude(system, user);
    return { drafts: ensureCount(splitDrafts(raw), req, count), usedMode: "claude" };
  }

  // 主力：Gemini
  if (config.gemini.enabled) {
    const raw = await callGemini(system, user);
    return { drafts: ensureCount(splitDrafts(raw), req, count), usedMode: "gemini" };
  }

  // 無金鑰：mock
  return { drafts: mockDrafts(req, count), usedMode: "mock" };
}

async function callGemini(system: string, user: string): Promise<string> {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${config.gemini.model}:generateContent?key=${config.gemini.apiKey}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: system }] },
      contents: [{ role: "user", parts: [{ text: user }] }],
      generationConfig: { temperature: 0.9, maxOutputTokens: 2048 },
    }),
  });
  if (!res.ok) throw new Error(`Gemini 失敗 (${res.status}): ${await res.text()}`);
  const json = (await res.json()) as {
    candidates?: { content?: { parts?: { text?: string }[] } }[];
  };
  return json.candidates?.[0]?.content?.parts?.map((p) => p.text ?? "").join("") ?? "";
}

async function callClaude(system: string, user: string): Promise<string> {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": config.claude.apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: config.claude.model,
      max_tokens: 2048,
      temperature: 0.9,
      system,
      messages: [{ role: "user", content: user }],
    }),
  });
  if (!res.ok) throw new Error(`Claude 失敗 (${res.status}): ${await res.text()}`);
  const json = (await res.json()) as { content?: { type: string; text?: string }[] };
  return json.content?.map((c) => c.text ?? "").join("") ?? "";
}

/** 模型偶爾少給幾篇時，補足數量（用 mock 補） */
function ensureCount(drafts: string[], req: GenerateRequest, count: number): string[] {
  if (drafts.length >= count) return drafts.slice(0, count);
  return [...drafts, ...mockDrafts(req, count - drafts.length)];
}

function mockDrafts(req: GenerateRequest, count: number): string[] {
  const hint = STYLE_INSTRUCTIONS[req.style];
  const refHook = req.references[0]?.text.split("\n")[0]?.slice(0, 18);
  const base = [
    `（範例草稿）關於「${req.topic}」，我最近想通一件事。\n\n${hint}\n\n以前總覺得要等準備好，後來發現「先開始」本身就是準備。\n\n你也在等什麼嗎？`,
    `（範例草稿）${req.topic}這件事，分享我的三個小心得：\n\n1. 先做能立刻做的\n2. 把成果記下來\n3. 隔天再優化一點\n\n${refHook ? `（靈感來自當天熱門：${refHook}…）` : ""}`,
    `（範例草稿）大多數人對「${req.topic}」的想像太完美了。\n\n真實情況通常很狼狽，但能持續走下去的，往往就是這些不完美的人。\n\n慢慢來，比較快。`,
    `（範例草稿）今天的${req.topic}小紀錄：做得不多，但有做。\n\n有時候維持節奏，比衝刺更重要。`,
  ];
  return Array.from({ length: count }, (_, i) => base[i % base.length]);
}
