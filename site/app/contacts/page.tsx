import type { Metadata } from "next";
import { LegalPage } from "@/components/legal-page";

export const metadata: Metadata = {
  title: "Контакты",
  description: "Связь с автором WinBoost: Telegram, email и GitHub.",
  alternates: { canonical: "/contacts/" },
};

export default function ContactsPage() {
  return (
    <LegalPage
      eyebrow="Обратная связь"
      title="Контакты"
      subtitle="Сообщите об ошибке, предложите улучшение или задайте вопрос."
    >
      <div className="contact-grid">
        <article className="contact-card">
          <span>Быстрый ответ</span>
          <h2>Telegram</h2>
          <p><a href="https://t.me/hageshii_kaze">@hageshii_kaze</a></p>
        </article>
        <article className="contact-card">
          <span>Деловые вопросы</span>
          <h2>Email</h2>
          <p><a href="mailto:wannabemugetsu@gmail.com">wannabemugetsu@gmail.com</a></p>
        </article>
        <article className="contact-card">
          <span>Код и ошибки</span>
          <h2>GitHub</h2>
          <p><a href="https://github.com/imalisherbekenov">imalisherbekenov</a></p>
        </article>
      </div>
      <section>
        <h2>Нашли баг?</h2>
        <p>Создайте Issue в GitHub-репозитории или напишите в Telegram. Укажите версию Windows, версию WinBoost, выбранные действия и что произошло после запуска.</p>
      </section>
      <section>
        <h2>Хотите предложить функцию?</h2>
        <p>Опишите сценарий, который хотите решить, и почему текущего процесса недостаточно. Конкретный пример помогает быстрее оценить предложение.</p>
      </section>
      <section>
        <h2>Коммерческое сотрудничество</h2>
        <p>Для партнёрств и других деловых вопросов используйте email.</p>
      </section>
    </LegalPage>
  );
}
