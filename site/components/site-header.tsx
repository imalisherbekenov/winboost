"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const downloadUrl = "https://github.com/imalisherbekenov/winboost/releases/latest";

const navItems = [
  { href: "/#how", label: "Как это работает" },
  { href: "/#analysis", label: "Анализ" },
  { href: "/#modes", label: "Режимы" },
  { href: "/#review", label: "Проверка" },
  { href: "/#backup", label: "Бэкапы" },
  { href: "/#faq", label: "FAQ" },
];

function Mark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 32 32" width="28" height="28">
      <rect x="1" y="1" width="30" height="30" rx="6" fill="none" stroke="currentColor" />
      <path d="M8 10l4 12 4-8 4 8 4-12" fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const panel = panelRef.current;
    const focusable = panel?.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
    );
    const first = focusable?.[0];
    const last = focusable?.[focusable.length - 1];
    const previousOverflow = document.body.style.overflow;

    document.body.style.overflow = "hidden";
    first?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }

      if (event.key !== "Tab" || !first || !last) return;

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <header className="site-header">
      <div className="nav-shell">
        <Link className="brand" href="/" aria-label="WinBoost, главная">
          <Mark />
          <span>WinBoost</span>
        </Link>

        <nav className="desktop-nav" aria-label="Основная навигация">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>

        <a className="ghost-button nav-download" href={downloadUrl}>
          Скачать
          <span aria-hidden="true">↗</span>
        </a>

        <button
          ref={triggerRef}
          className="menu-trigger"
          type="button"
          aria-expanded={open}
          aria-controls="mobile-navigation"
          aria-label={open ? "Закрыть меню" : "Открыть меню"}
          onClick={() => setOpen((current) => !current)}
        >
          <span aria-hidden="true" className={open ? "menu-icon is-open" : "menu-icon"}>
            <i />
            <i />
          </span>
        </button>
      </div>

      {open ? (
        <div ref={panelRef} id="mobile-navigation" className="mobile-panel">
          <nav aria-label="Мобильная навигация">
            {navItems.map((item, index) => (
              <Link key={item.href} href={item.href} onClick={close}>
                <span className="nav-index">0{index + 1}</span>
                {item.label}
              </Link>
            ))}
          </nav>
          <a className="ghost-button mobile-download" href={downloadUrl} onClick={close}>
            Скачать WinBoost
            <span aria-hidden="true">↗</span>
          </a>
          <p>Windows 10 / 11 · бесплатно · без регистрации</p>
        </div>
      ) : null}
    </header>
  );
}
