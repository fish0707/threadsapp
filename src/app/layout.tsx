import type { Metadata } from "next";
import Header from "@/components/Header";
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
          <Header />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
          <footer className="mx-auto max-w-6xl px-4 py-8 text-xs text-gray-400">
            <div className="flex flex-wrap items-center gap-4 border-t border-gray-100 pt-6">
              <span>© 2026 脈脈 Threads 經營助手</span>
              <a href="/privacy" className="hover:text-gray-700 hover:underline">
                隱私政策
              </a>
              <a href="/data-deletion" className="hover:text-gray-700 hover:underline">
                資料刪除
              </a>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
