import type { ThreadsPost } from "./types";

// mock 熱門文：沒有 Threads token 時，讓整個流程仍可走通。
// 內容會帶入使用者主題，看起來像當天的熱門貼文。
const TEMPLATES: { username: string; build: (topic: string) => string }[] = [
  {
    username: "career_notes",
    build: (t) =>
      `今天才發現，原來大家對「${t}」的誤會這麼深。\n\n我以前也以為要一次做到滿，後來才懂，先求穩再求快才是真的。\n\n你是哪一派？`,
  },
  {
    username: "daily_growth",
    build: (t) =>
      `關於${t}，我整理了三個這週實測有用的點：\n\n1. 先定義你要的結果\n2. 把大目標拆到「今天就能做」\n3. 做完馬上記錄一句心得\n\n簡單但有效，分享給你。`,
  },
  {
    username: "real_talk_tw",
    build: (t) =>
      `講個沒人想承認的事：多數人在${t}上卡關，不是不夠努力，是方向錯了。\n\n方向對，慢慢走都會到；方向錯，再拼也是繞圈。`,
  },
  {
    username: "tiny_habits",
    build: (t) =>
      `我用一個超小的習慣改善了${t}：每天只花五分鐘。\n\n別小看五分鐘，重點不是時間長短，是「每天都有發生」。\n\n你今天的五分鐘要給什麼？`,
  },
  {
    username: "mindset_lab",
    build: (t) =>
      `${t}最難的從來不是方法，而是「開始之後還願意繼續」。\n\n方法網路上一抓一大把，能撐住的人才稀有。\n\n一起撐住好嗎 🙌`,
  },
  {
    username: "side_project_diary",
    build: (t) =>
      `分享一個關於${t}的小故事。\n\n上週我差點放棄，結果隔天就出現轉機。\n\n很多時候我們只是停在「再撐一下就成功」的前一步。`,
  },
];

export function getMockPosts(topic: string): ThreadsPost[] {
  const now = Date.now();
  return TEMPLATES.map((tpl, i) => ({
    id: `mock_${i}_${Buffer.from(topic).toString("hex").slice(0, 8)}`,
    text: tpl.build(topic),
    username: tpl.username,
    permalink: "https://www.threads.net/",
    // 散開在過去幾小時，模擬「當天熱門」
    timestamp: new Date(now - i * 37 * 60 * 1000).toISOString(),
    media_type: "TEXT_POST",
  }));
}
