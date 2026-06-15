"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/client";

const LABELS: Record<string, string> = {
  search: "搜尋熱門文",
  publish: "發佈",
  geminiGenerate: "Gemini 生成",
  claudeGenerate: "Claude 生成",
  storage: "資料儲存",
};

export default function MockBanner() {
  const [mock, setMock] = useState<Record<string, boolean> | null>(null);

  useEffect(() => {
    api.status().then((r) => setMock(r.mock)).catch(() => {});
  }, []);

  if (!mock) return null;
  const active = Object.entries(mock).filter(([, v]) => v).map(([k]) => LABELS[k] ?? k);
  if (active.length === 0) return null;

  return (
    <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
      <span className="font-medium">🧪 Mock 模式：</span>
      以下功能尚未設定金鑰，目前使用範例資料 — {active.join("、")}。
      <span className="opacity-70">（在 .env.local 填入金鑰即會自動切換為真實串接）</span>
    </div>
  );
}
