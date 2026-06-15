import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "脈脈 — Threads 經營助手",
  description: "輸入主題、爬熱門文、AI 生成草稿、一鍵發佈到 Threads。",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-Hant">
      <body>
        <div className="min-h-screen">
          <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/80 backdrop-blur">
            <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
              <Link href="/" className="flex items-center gap-2 font-bold">
                <span className="text-xl">🧵</span>
                <span>脈脈 Threads 助手</span>
              </Link>
              <nav className="flex items-center gap-1 text-sm">
                <Link href="/" className="rounded-lg px-3 py-1.5 hover:bg-gray-100">
                  生成
                </Link>
                <Link href="/drafts" className="rounded-lg px-3 py-1.5 hover:bg-gray-100">
                  草稿匣
                </Link>
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
