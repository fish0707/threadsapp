import type { DraftStyle, ThreadsPost } from "./types";

const STYLE_INSTRUCTIONS: Record<DraftStyle, string> = {
  story:
    "用「故事情緒型」風格：以第一人稱講一個小經歷或場景，帶出情緒與共鳴，結尾收斂到一個感受或提問。避免說教。",
  humor:
    "用「幽默有梗型」風格：語氣輕鬆、有自嘲或反差梗，節奏短促，容易讓人會心一笑並想轉發。不要硬鬧。",
  listicle:
    "用「條列乾貨型」風格：開頭一句點題，中間用 3～5 個短條列（可用數字或符號），資訊密度高、好讀好收藏。",
  insight:
    "用「觀點洞察型」風格：提出一個和多數人不同、但有道理的觀點，先講常見想法、再給你的反轉與理由，引發討論。",
};

/**
 * 組出給 AI 的 prompt。重點：參考風格與結構、不抄原文、台灣口語、第一人稱、純文字輸出。
 */
export function buildGenerationPrompt(params: {
  topic: string;
  references: ThreadsPost[];
  style: DraftStyle;
  count: number;
}): { system: string; user: string } {
  const { topic, references, style, count } = params;

  const system = [
    "你是專寫繁體中文 Threads 貼文的社群文案高手，熟悉台灣社群語感。",
    "你的任務：參考使用者提供的熱門貼文「風格與結構」，為指定主題生成全新貼文草稿。",
    "嚴格規則：",
    "1. 只參考風格與結構，絕對不要抄襲或改寫原文句子。",
    "2. 使用繁體中文、台灣口語、第一人稱。",
    "3. 輸出純文字貼文，不要加標題、不要加「草稿一」之類前綴、不要用 markdown。",
    "4. 適合 Threads 的長度（約 80～280 字），可適度使用換行與少量 emoji。",
    "5. 不要加任何說明或註解，只輸出貼文本身。",
  ].join("\n");

  const refBlock =
    references.length > 0
      ? references
          .map(
            (p, i) =>
              `【參考 ${i + 1}｜@${p.username}】\n${p.text.trim()}`,
          )
          .join("\n\n")
      : "（使用者沒有勾選參考文，請依主題自由發揮，仍維持熱門貼文常見的鉤子開頭。）";

  const user = [
    `主題：${topic}`,
    `風格要求：${STYLE_INSTRUCTIONS[style]}`,
    "",
    "以下是當天該主題的熱門貼文，供你參考其鉤子、節奏與結構：",
    "",
    refBlock,
    "",
    `請生成 ${count} 篇不同切角的貼文草稿。`,
    `用「<<<DRAFT>>>」這一行分隔每一篇，前後不要有多餘文字。`,
  ].join("\n");

  return { system, user };
}

/** 把模型輸出依分隔符拆成多篇草稿 */
export function splitDrafts(raw: string): string[] {
  return raw
    .split(/<<<DRAFT>>>/g)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export { STYLE_INSTRUCTIONS };
