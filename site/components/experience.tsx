"use client";
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

export function Reveal({children, className = ""}: {children: ReactNode; className?: string}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {node.classList.remove("reveal-pending");observer.disconnect();}
    }, {threshold: .08});
    if (node.getBoundingClientRect().top > window.innerHeight) node.classList.add("reveal-pending");
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return <div ref={ref} className={`reveal ${className}`}>{children}</div>;
}

export function MotionScene() {
  const ref = useRef<HTMLDivElement>(null);
  return <div className="hero-scene" ref={ref} aria-label="Объёмная иллюстрация системного ядра WinBoost" onPointerMove={e => {
    if (e.pointerType !== "mouse" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const rect = e.currentTarget.getBoundingClientRect();
    ref.current?.style.setProperty("--tilt-x", `${(e.clientY - rect.top - rect.height / 2) / 55}deg`);
    ref.current?.style.setProperty("--tilt-y", `${(e.clientX - rect.left - rect.width / 2) / 55}deg`);
  }} onPointerLeave={() => {ref.current?.style.setProperty("--tilt-x", "0deg");ref.current?.style.setProperty("--tilt-y", "0deg");}}>
    <div className="scene-grid" /><div className="scene-coordinate top">WB / CORE ENGINE</div><div className="scene-coordinate bottom">DESIGNED FOR YOUR SYSTEM</div>
    <div className="chip-scene" aria-hidden="true"><div className="chip-orbit orbit-one" /><div className="chip-orbit orbit-two" /><div className="chip-base"><div className="circuit-lines">{Array.from({length: 8}, (_, i) => <i key={i} style={{"--i": i} as CSSProperties} />)}</div></div><div className="chip-middle" /><div className="chip-top"><div className="chip-border"><svg viewBox="0 0 160 120"><path d="M26 34l22 54 30-62 27 62 29-62" fill="none" stroke="currentColor" strokeWidth="13" strokeLinejoin="miter" /><path d="M108 16h35v35" fill="none" stroke="currentColor" strokeWidth="9" /></svg><span>WINBOOST</span><small>4.0</small></div></div><div className="chip-contact contact-left" /><div className="chip-contact contact-right" /></div>
    <div className="scene-badge badge-a"><span className="status-dot" /><span>Меньше лишнего<small>Больше контроля</small></span></div><div className="scene-badge badge-b"><span className="badge-symbol">↶</span><span>Сначала снимок<small>Затем изменения</small></span></div>
  </div>;
}
const demoActions = [
  {name: "Включить Game Mode", detail: "Приоритет игровым задачам Windows", risk: "Низкий риск"},
  {name: "Отключить рекламный ID", detail: "Ограничивает персонализацию рекламы", risk: "Низкий риск"},
  {name: "Производительный план питания", detail: "Может повысить энергопотребление", risk: "Требует решения"},
];

export function ProductDemo() {
  const [tab,setTab] = useState("overview");
  const [phase,setPhase] = useState<"idle"|"scanning"|"ready"|"review"|"done">("idle");
  const [selected,setSelected] = useState([true,true,false]);
  const [progress,setProgress] = useState(0);
  const [profile,setProfile] = useState("Повседневный");
  const [restored,setRestored] = useState(false);
  useEffect(() => {
    if (phase !== "scanning") return;
    const timer = window.setInterval(() => setProgress(p => Math.min(100,p+10)),160);
    return () => window.clearInterval(timer);
  }, [phase]);
  useEffect(() => {if(progress===100 && phase==="scanning") setPhase("ready");},[progress,phase]);
  const scan = () => {setProgress(0);setPhase("scanning");};
  const count = selected.filter(Boolean).length;
  return <div className="product-window">
    <div className="window-chrome"><span><i /><i /><i /></span><span>WinBoost 4.0</span><span className="demo-tag">ДЕМОНСТРАЦИЯ</span></div>
    <div className="product-body"><aside className="product-sidebar"><div className="product-logo">W<span>↗</span><strong>WinBoost<small>CONTROL CENTER</small></strong></div><div className="product-nav" aria-label="Разделы демонстрации">{[["overview","◉","Обзор системы"],["profiles","⌘","Сценарии"],["actions","≡","Все настройки"],["backups","↶","Снимки"]].map(([id,icon,title]) => <button aria-pressed={tab===id} key={id} className={tab===id ? "selected" : ""} onClick={() => setTab(id)}><span aria-hidden="true">{icon}</span>{title}</button>)}</div><div className="sidebar-bottom"><span className="status-dot" /> Локально. Под контролем.<small>Windows 11 Pro · x64</small></div></aside>
    <div className="product-content">
      <div className="product-heading"><div><span className="eyebrow">ВАШЕ РАБОЧЕЕ ПРОСТРАНСТВО</span><h3>{tab==="profiles" ? "Под ваш ритм." : tab==="actions" ? "Всё по полочкам." : tab==="backups" ? "Всегда есть план Б." : "Всё под контролем."}</h3></div><span className="device-label"><span className="status-dot" /> DESKTOP</span></div>
      {tab==="overview" && <div className="demo-panel-enter"><div className="demo-metrics">{[["ПРОЦЕССОР","12","%","AMD Ryzen 7 7800X3D"],["ПАМЯТЬ","6.4"," / 32 ГБ","20% используется"],["СИСТЕМНЫЙ ДИСК","284"," ГБ","Свободно из 1 ТБ"]].map(([label,value,unit,detail],i) => <div key={label} className="metric"><span>{label}</span><strong>{value}<small>{unit}</small></strong><div className="metric-track"><i style={{transform:`scaleX(${[.12,.2,.28][i]})`}} /></div><p>{detail}</p></div>)}</div><div className="scan-panel"><div className={`scan-orb ${phase==="scanning" ? "is-scanning" : ""}`} aria-hidden="true"><span>{phase==="scanning" ? `${progress}%` : phase==="idle" ? "W" : "✓"}</span></div><div><span className="eyebrow">{phase==="idle" ? "НАЧНИТЕ С ДИАГНОСТИКИ" : phase==="scanning" ? "ИЗУЧАЕМ СИСТЕМУ" : "АНАЛИЗ ЗАВЕРШЁН"}</span><h4>{phase==="idle" ? "Узнайте свою систему лучше" : phase==="scanning" ? "Проверяем параметры…" : "Есть что настроить под себя"}</h4><p>{phase==="idle" ? "Проверим основные параметры и подготовим обзор." : phase==="scanning" ? "Демонстрация сканирования Windows" : "Откройте настройки и выберите подходящие действия."}</p><button className="primary-button small-button" disabled={phase==="scanning"} onClick={phase==="idle" || phase==="scanning" ? scan : () => setTab("actions")}>{phase==="idle" ? "Анализировать систему" : phase==="scanning" ? "Выполняется анализ…" : "Посмотреть настройки"}<span aria-hidden="true">↗</span></button></div></div><div className="demo-bottom-note"><span>◎</span> Анализ читает настройки. Изменения начнутся только после вашего решения.</div></div>}
      {tab==="profiles" && <div className="demo-panel-enter"><p className="panel-description">Выберите сценарий — состав рекомендаций изменится.</p><div className="profile-options">{["Повседневный","Игровой","Приватность"].map((name,i) => <button className={profile===name ? "selected" : ""} key={name} onClick={() => setProfile(name)}><span>0{i+1}</span><strong>{name}</strong><small>{["Комфортная работа каждый день","Фокус на игровых настройках","Меньше фонового сбора данных"][i]}</small></button>)}</div><div className="profile-summary"><p>{profile==="Игровой" ? "В набор входят Game Mode и план питания. Компромиссы видны перед применением." : profile==="Приватность" ? "Начните с отключения рекламного ID. Остальные параметры можно выбрать в приложении." : "Умеренный набор для повседневной работы с Windows."}</p><button className="primary-button small-button" onClick={() => {setSelected(profile==="Игровой" ? [true,false,true] : profile==="Приватность" ? [false,true,false] : [true,true,false]);setPhase("ready");setTab("actions");}}>Посмотреть набор <span>↗</span></button></div></div>}
      {tab==="actions" && <div className="demo-panel-enter"><p className="panel-description">{phase==="review" ? "Проверьте выбранное. Перед применением будет создан демонстрационный снимок." : "Выберите нужные изменения. Сначала проверка, затем применение."}</p><div className="demo-action-list">{demoActions.map((action,i) => <label key={action.name} className={`demo-action ${phase==="review" && !selected[i] ? "dimmed" : ""}`}><input type="checkbox" checked={selected[i]} onChange={() => {setSelected(s => s.map((v,j) => j===i ? !v : v));setPhase("ready");}} /><span><strong>{action.name}</strong><small>{action.detail}</small></span><em className={i===2 ? "risk-warning" : ""}>{action.risk}</em></label>)}</div><div className="demo-review-bar"><span role="status">{phase==="done" ? "Готово. Демонстрационный снимок сохранён." : `Выбрано: ${count} · Необратимых: 0`}</span><button className="primary-button small-button" disabled={!count} onClick={() => {if(phase==="done") setTab("backups"); else if(phase==="review") {setPhase("done");setRestored(false);} else setPhase("review");}}>{phase==="done" ? "Открыть снимки" : phase==="review" ? "Применить в демо" : "Проверить выбор"} <span>↗</span></button></div></div>}
      {tab==="backups" && <div className="demo-panel-enter"><p className="panel-description">Сохранённое состояние настроек, к которому можно вернуться.</p><div className="backup-demo"><span className="backup-demo-icon">↶</span><div><strong>{phase==="done" ? "Перед выбранными изменениями" : "Первичный снимок"}</strong><small>Реестр · Службы · План питания · DNS</small></div><span className="backup-pill">{restored ? "Восстановлен" : "Доступен"}</span></div><div className="demo-review-bar"><span role="status">{restored ? "Демонстрация завершена. Реальная система не менялась." : "В демо восстановление не меняет Windows."}</span><button className="primary-button small-button" disabled={restored} onClick={() => setRestored(true)}>{restored ? "Готово" : "Восстановить в демо"}<span>↶</span></button></div></div>}
      <span className="sr-only" role="status">{phase==="scanning" ? `Анализ: ${progress}%` : phase==="ready" ? "Анализ завершён" : ""}</span>
    </div></div>
  </div>;
}
