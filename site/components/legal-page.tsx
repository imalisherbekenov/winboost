import type { ReactNode } from "react";
import Link from "next/link";
import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";

type LegalPageProps = {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
};

export function LegalPage({ eyebrow, title, subtitle, children }: LegalPageProps) {
  return (
    <>
      <SiteHeader />
      <main className="legal-main">
        <div className="legal-shell">
          <Link className="back-link" href="/">
            <span aria-hidden="true">←</span> На главную
          </Link>
          <header className="legal-heading">
            <span className="eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </header>
          <article className="legal-copy">{children}</article>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
