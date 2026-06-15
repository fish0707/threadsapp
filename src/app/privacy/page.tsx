import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "隱私政策 — 脈脈 Threads 經營助手",
};

const UPDATED = "2026-06-15";
const CONTACT = "fishchen0707@gmail.com";

export default function PrivacyPage() {
  return (
    <article className="prose-sm mx-auto max-w-3xl space-y-6 text-gray-700">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">隱私政策</h1>
        <p className="mt-1 text-sm text-gray-400">最後更新：{UPDATED}</p>
      </header>

      <p>
        「脈脈 Threads 經營助手」（以下稱「本服務」）協助使用者經營自己的 Threads
        帳號：輸入主題後參考當天熱門公開貼文，由 AI 生成原創貼文草稿，並可發佈到使用者本人的
        Threads 帳號。本政策說明我們蒐集、使用與保護資料的方式。
      </p>

      <Section title="一、我們蒐集的資料">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <b>Threads 授權資料</b>：經你 OAuth 授權後取得的存取權杖（access token）、
            你的 Threads 使用者 ID 與使用者名稱，用於代你搜尋與發佈。
          </li>
          <li>
            <b>你建立的內容</b>：你輸入的主題、AI 生成的草稿、發佈紀錄。
          </li>
          <li>
            <b>公開貼文（僅顯示用）</b>：透過 Threads keyword_search 取得的公開熱門貼文，
            僅作為你創作時的靈感參考顯示，我們不轉售、不重新發佈他人內容。
          </li>
        </ul>
      </Section>

      <Section title="二、資料用途">
        <ul className="list-disc space-y-1 pl-5">
          <li>提供搜尋熱門文、AI 生成草稿、發佈到 Threads 等核心功能。</li>
          <li>暫存同主題查詢結果以節省 API 額度。</li>
          <li>我們不會將你的資料用於廣告或建立跨站使用者輪廓，也不販售你的資料。</li>
        </ul>
      </Section>

      <Section title="三、資料儲存與保護">
        <ul className="list-disc space-y-1 pl-5">
          <li>存取權杖採加密後儲存（AES-256-GCM），不會出現在前端或網址中。</li>
          <li>資料儲存於 Supabase（PostgreSQL）。</li>
          <li>採最小權限原則，僅存取提供功能所需之資料。</li>
        </ul>
      </Section>

      <Section title="四、第三方服務">
        <p>本服務使用下列第三方處理者，資料於提供功能所需範圍內傳輸：</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Meta（Threads API）— 搜尋與發佈</li>
          <li>Vercel — 應用程式代管</li>
          <li>Supabase — 資料庫</li>
          <li>Google Gemini／Anthropic Claude — AI 生成草稿</li>
        </ul>
      </Section>

      <Section title="五、資料保存與刪除">
        <p>
          你可隨時在本服務中點「解除連結」移除已儲存的 Threads
          權杖；或於 Threads 帳號設定中移除本應用程式授權，我們會在收到 Meta
          通知後刪除對應權杖。你也可寄信至下方信箱要求刪除你的所有資料。
          詳見{" "}
          <a className="text-brand-accent underline" href="/data-deletion">
            資料刪除說明
          </a>
          。
        </p>
      </Section>

      <Section title="六、聯絡方式">
        <p>
          資料控管者（個人）。如有任何隱私相關問題或資料刪除需求，請聯絡：
          <br />
          <a className="text-brand-accent underline" href={`mailto:${CONTACT}`}>
            {CONTACT}
          </a>
        </p>
      </Section>

      <Section title="七、政策更新">
        <p>本政策若有重大變更，將於本頁更新「最後更新」日期。</p>
      </Section>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-bold text-gray-900">{title}</h2>
      {children}
    </section>
  );
}
