import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { ProductDemo, MotionScene, Reveal } from "@/components/experience";

const modules = [
  ["01", "Приватность", "Телеметрия, рекламный ID и фоновые разрешения."],
  ["02", "Игровой режим", "Game DVR, план питания и параметры CS2."],
  ["03", "Система и сеть", "Службы, DNS и настройки подключения."],
  ["04", "Порядок в Windows", "Автозагрузка, временные файлы и приложения."],
];
const faqs = [
  ["Насколько быстрее станет мой компьютер?", "Результат зависит от оборудования, фоновых процессов и исходных настроек Windows. WinBoost помогает убрать лишнюю нагрузку, но не обещает конкретный прирост FPS. Анализ показывает состояние системы, а не результат бенчмарка."],
  ["Можно ли отменить изменения?", "Перед применением создаётся снимок затрагиваемых настроек: реестра, служб, задач, плана питания и DNS. Их можно восстановить из раздела «Снимки». Удаление файлов и приложений необратимо; такие действия не выбираются автоматически."],
  ["Нужны ли права администратора?", "Для изменения системных настроек — да. Программа запросит права через стандартное окно Windows. Сам сайт показывает только демонстрационные данные и не получает доступ к вашему компьютеру."],
  ["Программа работает без интернета?", "Анализ и большинство настроек выполняются локально. Отдельным действиям Windows может понадобиться сеть. WinBoost не требует регистрации; исходный код открыт под лицензией MIT."],
  ["Где скачать новую версию?", "На этой странице доступна локальная сборка WinBoost 4.0 для Windows 10/11 x64. Это новая сборка из исходного кода, без цифровой подписи издателя. История публичных релизов доступна на GitHub."],
];

export default function Home() {
  return <>
    <SiteHeader />
    <main id="main">
      <section className="hero shell">
        <div className="hero-copy">
          <div className="release-label"><span className="status-dot" /> WINBOOST 4.0 <span className="release-divider" /> НОВАЯ ВЕРСИЯ</div>
          <h1>Ваш Windows.<br />В лучшей <span>форме.</span></h1>
          <p className="hero-description">Меньше фонового шума. Больше пространства для важного. Настройте систему под себя — с пониманием каждого изменения.</p>
          <div className="hero-actions"><a className="primary-button" href="#download">Получить WinBoost <span aria-hidden="true">↗</span></a><a className="text-button" href="#demo"><span className="play-icon" aria-hidden="true">▷</span> Посмотреть в действии</a></div>
          <div className="hero-platform"><svg viewBox="0 0 20 22" aria-hidden="true"><path d="M1 3l8-1v8H1zm10-1l8-1v9h-8zM1 12h8v7l-8-1zm10 0h8v9l-8-1z" fill="currentColor" /></svg> Windows 10 / 11 <span>·</span> Бесплатно <span>·</span> Open source</div>
        </div>
        <MotionScene />
        <div className="hero-bottom"><span>СИСТЕМА ПОД ВАШИМ КОНТРОЛЕМ</span><a href="#demo">Прокрутите, чтобы исследовать <span aria-hidden="true">↓</span></a></div>
      </section>
      <section className="principles shell" aria-label="Принципы программы">{[["↗", "Точная настройка", "Под ваш сценарий"], ["◎", "Всё прозрачно", "Проверка перед применением"], ["↶", "Есть путь назад", "Снимок перед запуском"], ["⌘", "Полностью ваш", "Без подписок и аккаунта"]].map(([icon,title,copy]) => <div key={title}><span className="principle-icon" aria-hidden="true">{icon}</span><span>{title}<small>{copy}</small></span></div>)}</section>
      <section id="demo" className="section shell">
        <Reveal><div className="section-heading"><div><span className="eyebrow">01 / ЦЕНТР УПРАВЛЕНИЯ</span><h2>Сложное внутри.<br /><span>Понятное снаружи.</span></h2></div><p>Одна точка входа для анализа, настройки и восстановления. Попробуйте интерфейс прямо здесь.</p></div></Reveal>
        <Reveal><ProductDemo /></Reveal>
        <div className="demo-caption"><span><span className="status-dot" /> ИНТЕРАКТИВНОЕ ПРЕВЬЮ</span><p>Демонстрационные данные. Настройки вашего компьютера не меняются.</p></div>
      </section>
      <section id="features" className="section shell features-section">
        <Reveal><div className="section-heading"><div><span className="eyebrow">02 / ВОЗМОЖНОСТИ</span><h2>Уберите лишнее.<br /><span>Оставьте своё.</span></h2></div><p>10 модулей настройки — от приватности до игровых параметров. Вы решаете, что действительно нужно.</p></div></Reveal>
        <div className="feature-layout"><Reveal className="feature-visual"><div className="feature-visual-top"><span className="eyebrow">МЕНЬШЕ ФОНОВОГО ШУМА</span><span className="status-dot" /></div><div className="signal-art" aria-hidden="true">{Array.from({length: 35}, (_, i) => <i key={i} style={{"--i": i, "--bar": `${18 + Math.sin(i * .65) ** 2 * 80}%`} as React.CSSProperties} />)}</div><div className="feature-visual-bottom"><h3>Ресурсы —<br />вашим задачам.</h3><p>Контролируйте фоновые процессы,<br />а не подстраивайтесь под них.</p></div></Reveal><div className="module-list">{modules.map(([n,title,desc]) => <Reveal key={n}><a href="#demo" className="module-row"><span className="module-number">{n}</span><div><h3>{title}</h3><p>{desc}</p></div><span className="module-arrow" aria-hidden="true">↗</span></a></Reveal>)}</div></div>
      </section>
      <section id="how" className="workflow-section"><div className="shell section"><Reveal><div className="section-heading"><div><span className="eyebrow">03 / ПОНЯТНЫЙ ПРОЦЕСС</span><h2>Три шага.<br /><span>Никакой магии.</span></h2></div><p>Вместо одной загадочной кнопки — последовательный процесс, в котором решение всегда за вами.</p></div></Reveal><div className="workflow-grid">{[
        ["01", "Изучите систему", "Глубокий анализ оборудования, служб, автозагрузки и параметров Windows.", "CPU / RAM / DISK"],
        ["02", "Соберите свой набор", "Готовые сценарии или точный выбор. У каждого действия — описание и уровень риска.", "ВЫБОР → ПРОВЕРКА"],
        ["03", "Примените с контролем", "Сначала снимок, затем изменения. Ход выполнения, остановка и результат — на одном экране.", "СНИМОК → ПРИМЕНЕНИЕ"],
      ].map(([n,title,desc,label]) => <Reveal key={n} className="workflow-step"><span className="step-number">{n}<span aria-hidden="true">↗</span></span><h3>{title}</h3><p>{desc}</p><span className="step-label">{label}</span></Reveal>)}</div></div></section>
      <section id="safety" className="section shell"><Reveal className="safety-layout"><div className="snapshot-art" aria-hidden="true"><div className="snapshot-card back"><span>ПРЕДЫДУЩЕЕ СОСТОЯНИЕ</span><i /><i /><i /></div><div className="snapshot-card front"><div className="snapshot-symbol">↶</div><span>СНИМОК СИСТЕМЫ</span><strong>Можно вернуться.</strong><div className="snapshot-line"><span className="status-dot" /> Настройки сохранены</div></div></div><div className="safety-copy"><span className="eyebrow">КОНТРОЛЬ, А НЕ СЛЕПАЯ ВЕРА</span><h2>План Б.<br /><span>Уже в комплекте.</span></h2><p>Перед изменениями WinBoost сохраняет затрагиваемые настройки. Если что-то не подошло, восстановите их из снимка.</p><ul><li>Первичный снимок хранится отдельно</li><li>Риски видны до запуска</li><li>Необратимые действия выбираете только вы</li></ul><p className="fine-print">Снимок настроек не заменяет резервную копию файлов. Удалённые файлы и приложения автоматически не восстанавливаются.</p></div></Reveal></section>
      <section id="faq" className="section shell faq-section"><Reveal><div><span className="eyebrow">ЕЩЁ ПАРА ДЕТАЛЕЙ</span><h2>Хорошие<br /><span>вопросы.</span></h2><a className="text-button" href="https://github.com/imalisherbekenov/winboost/issues">Обсудить на GitHub <span aria-hidden="true">↗</span></a></div></Reveal><div className="faq-list">{faqs.map(([q,a],i) => <details key={q}><summary><span className="faq-index">0{i+1}</span>{q}<span className="faq-plus" aria-hidden="true">+</span></summary><p>{a}</p></details>)}</div></section>
      <section id="download" className="download-section shell"><Reveal><div className="download-panel"><div><span className="eyebrow">WINBOOST 4.0 / WINDOWS X64</span><h2>Компьютер ваш.<br /><span>Правила тоже.</span></h2><p>Начните с анализа. Измените только то, что нужно.</p><a className="primary-button" href="/downloads/WinBoost-4.0.exe" download>Скачать WinBoost 4.0 <span aria-hidden="true">↓</span></a><p className="download-note">Windows 10 / 11 · Бесплатно · Локальная сборка без подписи</p></div><div className="download-mark" aria-hidden="true">W<span>↗</span></div></div></Reveal></section>
    </main><SiteFooter />
  </>;
}
