import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

const downloadUrl = "https://github.com/imalisherbekenov/winboost/releases/latest";

const steps = [
  {
    title: "Анализ системы",
    text: "WinBoost читает конфигурацию, состояние служб и ключевых параметров, чтобы рекомендации учитывали именно ваш компьютер.",
  },
  {
    title: "Выберите путь",
    text: "Ответьте на понятные вопросы в режиме новичка или откройте полный каталог параметров в экспертном режиме.",
  },
  {
    title: "Проверка изменений",
    text: "До запуска вы увидите каждое действие, его эффект и возможный компромисс. Ненужные пункты можно исключить.",
  },
  {
    title: "Применение за один запуск",
    text: "Выбранные настройки применяются последовательно в одной сессии, а резервная копия создаётся автоматически.",
  },
  {
    title: "Откат в любой момент",
    text: "Если результат не подошёл, верните большинство системных твиков к сохранённому состоянию через WinBoost.",
  },
];

const analysisPoints = [
  ["Узкое место", "Сопоставляет CPU, GPU, память и накопитель"],
  ["Потенциал", "Показывает, есть ли смысл менять настройки"],
  ["Состояние", "Проверяет службы и системные параметры"],
  ["Приватность", "Находит активную телеметрию и сбор данных"],
  ["Устойчивость", "Отмечает настройки, влияющие на стабильность"],
];

const reviewItems = [
  {
    level: "Высокое влияние",
    tone: "danger",
    title: "Отключить Windows Search",
    text: "Индексатор перестанет работать в фоне, но поиск файлов в Проводнике может стать медленнее.",
  },
  {
    level: "Высокое влияние",
    tone: "danger",
    title: "Отключить Xbox Game Bar",
    text: "Освобождает фоновые ресурсы, но отключает оверлей и запись экрана по Win+G.",
  },
  {
    level: "Требует решения",
    tone: "warning",
    title: "Отключить SysMain",
    text: "На SSD эффект обычно невелик; на HDD предзагрузка приложений может оставаться полезной.",
  },
  {
    level: "Требует решения",
    tone: "warning",
    title: "Удалить предустановленные приложения",
    text: "Освобождает место, но удалённые приложения придётся устанавливать заново через Microsoft Store.",
  },
  {
    level: "Обратимое действие",
    tone: "safe",
    title: "Включить производительный план питания",
    text: "Меняет профиль энергопотребления. Исходный план сохраняется и доступен для восстановления.",
  },
];

const faqs = [
  {
    question: "Что такое WinBoost?",
    answer:
      "Это локальное приложение для анализа и настройки Windows. Оно объединяет системные твики в понятный процесс: диагностика, выбор, проверка, применение и откат.",
  },
  {
    question: "Увеличит ли WinBoost FPS в играх?",
    answer:
      "Иногда — за счёт меньшей фоновой нагрузки и более ровного времени кадра. Итог зависит от железа, драйверов, игры и исходного состояния Windows; приложение не обещает одинаковый прирост на всех системах.",
  },
  {
    question: "Это безопасно?",
    answer:
      "WinBoost сначала показывает список изменений и создаёт резервную копию перед применением. При этом системные настройки всегда требуют осознанного выбора — внимательно читайте предупреждения в проверке.",
  },
  {
    question: "Может ли WinBoost сломать Windows?",
    answer:
      "Большинство твиков обратимы, но некоторые действия по своей природе необратимы, например очистка файлов или удаление приложений. Такие пункты отмечаются до запуска; важные данные всё равно стоит резервировать отдельно.",
  },
  {
    question: "Нужно ли знать технические термины?",
    answer:
      "Нет. Режим новичка задаёт практические вопросы о вашем сценарии. Экспертный режим остаётся доступен тем, кому нужен контроль над каждым параметром.",
  },
  {
    question: "Можно ли отменить изменения?",
    answer:
      "Да, для большинства системных твиков. WinBoost сохраняет исходное состояние перед применением и позволяет выбрать резервную копию для восстановления.",
  },
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "WinBoost",
  applicationCategory: "UtilitiesApplication",
  operatingSystem: "Windows 10, Windows 11",
  description:
    "Приложение для анализа, осознанной оптимизации и отката системных настроек Windows.",
  downloadUrl,
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
};

function SectionIntro({ label, title, copy }: { label: string; title: string; copy: string }) {
  return (
    <header className="section-intro">
      <span className="eyebrow">{label}</span>
      <h2>{title}</h2>
      <p>{copy}</p>
    </header>
  );
}

function TerminalHeader({ title }: { title: string }) {
  return (
    <div className="terminal-header">
      <div className="terminal-controls" aria-hidden="true">
        <i />
        <i />
        <i />
      </div>
      <span>{title}</span>
      <span aria-hidden="true">—</span>
    </div>
  );
}

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main>
        <section className="hero" aria-labelledby="hero-title">
          <div className="page-shell hero-grid">
            <div className="hero-copy">
              <span className="eyebrow hero-kicker">Оптимизация без догадок</span>
              <h1 id="hero-title">Настройте Windows под свою систему</h1>
              <p>
                WinBoost анализирует компьютер, объясняет каждое действие и сохраняет путь назад.
                Вы решаете, что менять — приложение аккуратно выполняет выбранное.
              </p>
              <div className="hero-actions">
                <a className="ghost-button" href={downloadUrl}>
                  Скачать WinBoost <span aria-hidden="true">↗</span>
                </a>
                <a className="text-link" href="#how">
                  Посмотреть процесс <span aria-hidden="true">↓</span>
                </a>
              </div>
            </div>

            <div className="hero-object" aria-hidden="true">
              <div className="object-axis axis-x" />
              <div className="object-axis axis-y" />
              <div className="wire-cube">
                <div className="cube-face cube-front" />
                <div className="cube-face cube-back" />
                <div className="cube-link link-a" />
                <div className="cube-link link-b" />
                <div className="cube-link link-c" />
                <div className="cube-link link-d" />
              </div>
              <span className="object-label label-top">SYSTEM / READY</span>
              <span className="object-label label-bottom">SAFE STATE / 01</span>
            </div>
          </div>

          <div className="page-shell hero-stats" aria-label="Возможности WinBoost">
            <div><strong>10</strong><span>модулей оптимизации</span></div>
            <div><strong>55</strong><span>действий и твиков</span></div>
            <div><strong>откат</strong><span>включён по умолчанию</span></div>
          </div>
        </section>

        <section className="section" id="how">
          <div className="page-shell">
            <SectionIntro
              label="01 / Процесс"
              title="Пять шагов. Ни одного скрытого действия."
              copy="Оптимизация начинается с фактов, проходит через ваш выбор и заканчивается сохранённым состоянием для восстановления."
            />
            <ol className="steps-list">
              {steps.map((step, index) => (
                <li key={step.title}>
                  <span className="step-number">0{index + 1}</span>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="section" id="analysis">
          <div className="page-shell">
            <SectionIntro
              label="02 / Диагностика"
              title="Сначала — анализ системы"
              copy="WinBoost собирает локальный снимок конфигурации и отмечает параметры, которые действительно заслуживают внимания."
            />
            <div className="feature-split">
              <ol className="analysis-points">
                {analysisPoints.map(([title, text], index) => (
                  <li key={title}>
                    <span>{index + 1}</span>
                    <div><h3>{title}</h3><p>{text}</p></div>
                  </li>
                ))}
              </ol>

              <div className="terminal" aria-label="Пример анализа системы в WinBoost">
                <TerminalHeader title="winboost / analyze" />
                <div className="terminal-body">
                  <p><span className="terminal-prompt">$</span> winboost --analyze <span className="syntax-id">--local</span></p>
                  <p className="terminal-muted">Чтение конфигурации Windows...</p>
                  <p><span className="status-success">OK</span> CPU <span className="syntax-id">AMD Ryzen 7 5800X</span></p>
                  <p><span className="status-success">OK</span> GPU <span className="syntax-id">NVIDIA RTX 3070</span></p>
                  <p><span className="status-success">OK</span> RAM <span className="syntax-id">32 GB DDR4</span></p>
                  <p><span className="status-warning">WARN</span> DiagTrack активен</p>
                  <p><span className="status-warning">WARN</span> SysMain использует 284 MB</p>
                  <p><span className="status-error">CHECK</span> 7 действий требуют решения</p>
                  <p className="terminal-rule">────────────────────────────</p>
                  <p><span className="status-success">READY</span> найдено 18 рекомендаций</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section" id="modes">
          <div className="page-shell">
            <SectionIntro
              label="03 / Два режима"
              title="Понятный выбор или полный контроль"
              copy="Оба пути используют один анализ и одну проверку. Отличается только глубина ручной настройки."
            />
            <div className="modes-grid">
              <article className="mode-card">
                <div className="mode-meta"><span>Режим 01</span><span>Для новичка</span></div>
                <h3>Ответьте на обычные вопросы</h3>
                <p>Используете Bluetooth? Нужен Xbox Game Bar? Важнее анимации или отзывчивость? WinBoost переведёт ответы в настройки.</p>
                <ul>
                  <li>Без системного жаргона</li>
                  <li>Рекомендации по сценарию</li>
                  <li>Все компромиссы видны до запуска</li>
                </ul>
              </article>
              <article className="mode-card">
                <div className="mode-meta"><span>Режим 02</span><span>Для эксперта</span></div>
                <h3>Управляйте каждым параметром</h3>
                <p>Откройте каталог модулей, изучите описание и отдельно включите только те действия, которые нужны вашей конфигурации.</p>
                <ul>
                  <li>Полный список действий</li>
                  <li>Группировка по модулям</li>
                  <li>Ручное включение и исключение</li>
                </ul>
              </article>
            </div>
          </div>
        </section>

        <section className="section" id="review">
          <div className="page-shell">
            <SectionIntro
              label="04 / Проверка"
              title="Вы видите последствия до применения"
              copy="Каждое действие раскрывает не только пользу, но и то, что может измениться в привычной работе Windows."
            />
            <div className="review-list">
              {reviewItems.map((item) => (
                <article key={item.title} className="review-row">
                  <span className={`risk-dot ${item.tone}`} aria-hidden="true" />
                  <div className="review-level">{item.level}</div>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section" id="backup">
          <div className="page-shell">
            <SectionIntro
              label="05 / Бэкапы"
              title="Исходное состояние остаётся рядом"
              copy="Перед применением WinBoost фиксирует настройки реестра, служб и питания. Резервные копии остаются локально на вашем компьютере."
            />
            <div className="backup-split">
              <div className="backup-copy">
                <div><span>01</span><h3>Автоматически</h3><p>Бэкап создаётся до того, как меняется первый параметр.</p></div>
                <div><span>02</span><h3>Локально</h3><p>Файлы восстановления не отправляются на внешние серверы.</p></div>
                <div><span>03</span><h3>Выборочно</h3><p>Можно открыть сохранённое состояние и восстановить поддерживаемые настройки.</p></div>
              </div>
              <div className="terminal" aria-label="Пример создания резервной копии в WinBoost">
                <TerminalHeader title="winboost / backup" />
                <div className="terminal-body">
                  <p><span className="terminal-prompt">$</span> winboost --backup <span className="syntax-id">--before-apply</span></p>
                  <p><span className="status-success">SAVED</span> реестр</p>
                  <p><span className="status-success">SAVED</span> состояние служб</p>
                  <p><span className="status-success">SAVED</span> схема электропитания</p>
                  <p><span className="status-success">SAVED</span> системные параметры</p>
                  <p className="terminal-rule">────────────────────────────</p>
                  <p>Путь: <span className="syntax-id">C:\WinBoost\Backups\state-01.wbb</span></p>
                  <p><span className="status-success">READY</span> можно применять 18 действий</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section faq-section" id="faq">
          <div className="page-shell faq-shell">
            <SectionIntro
              label="06 / FAQ"
              title="Коротко о важном"
              copy="Что делает приложение, чего от него ожидать и где сохраняется контроль."
            />
            <div className="faq-list">
              {faqs.map((faq, index) => (
                <details key={faq.question}>
                  <summary><span className="faq-number">0{index + 1}</span><span>{faq.question}</span><span className="faq-toggle" aria-hidden="true" /></summary>
                  <p>{faq.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="cta-section" aria-labelledby="cta-title">
          <div className="page-shell cta-shell">
            <span className="eyebrow">Начните с анализа</span>
            <h2 id="cta-title">Настройте Windows с пониманием каждого шага.</h2>
            <p>Бесплатно · без регистрации · для Windows 10 и 11</p>
            <a className="ghost-button" href={downloadUrl}>
              Скачать последнюю версию <span aria-hidden="true">↗</span>
            </a>
          </div>
        </section>
      </main>
      <SiteFooter />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
    </>
  );
}
