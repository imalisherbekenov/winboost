import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-shell">
        <div>
          <Link className="footer-brand" href="/">
            WinBoost
          </Link>
          <p>Осознанная настройка Windows с возможностью отката.</p>
        </div>
        <nav aria-label="Юридическая информация">
          <Link href="/privacy/">Конфиденциальность</Link>
          <Link href="/terms/">Соглашение</Link>
          <Link href="/contacts/">Контакты</Link>
          <a href="https://github.com/imalisherbekenov/winboost">GitHub</a>
        </nav>
        <p className="copyright">© {new Date().getFullYear()} WinBoost</p>
      </div>
    </footer>
  );
}
