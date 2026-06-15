import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "資料刪除說明 — 脈脈 Threads 經營助手",
};

const CONTACT = "fishchen0707@gmail.com";

export default function DataDeletionPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-6 text-gray-700">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">資料刪除說明</h1>
      </header>

      <p>你可以透過以下任一方式刪除本服務儲存的你的資料：</p>

      <section className="space-y-2">
        <h2 className="text-lg font-bold text-gray-900">方式一：在本服務中解除連結</h2>
        <p>於首頁點「解除連結」，即會刪除本服務儲存的 Threads 存取權杖。</p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-bold text-gray-900">方式二：於 Threads 移除授權</h2>
        <p>
          在 Threads 帳號 → 設定 → 網站權限中移除本應用程式。Meta 會通知本服務
          （經由 deauthorize / data deletion 回呼），我們將刪除對應的權杖資料。
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-bold text-gray-900">方式三：來信要求</h2>
        <p>
          寄信至{" "}
          <a className="text-brand-accent underline" href={`mailto:${CONTACT}`}>
            {CONTACT}
          </a>{" "}
          並註明你的 Threads 使用者名稱，我們將於合理期間內刪除你的所有相關資料
          （權杖、草稿、發佈紀錄）。
        </p>
      </section>

      <p className="text-sm text-gray-400">
        詳細資料處理方式請見{" "}
        <a className="underline" href="/privacy">
          隱私政策
        </a>
        。
      </p>
    </article>
  );
}
