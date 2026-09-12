import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://winboost.vercel.app"),
  title: {default: "WinBoost 4.0 — ваш Windows в лучшей форме", template: "%s — WinBoost"},
  description: "Анализ, сценарии настройки и контроль изменений Windows. WinBoost 4.0 — бесплатное локальное приложение с проверкой действий и снимками для отката.",
  openGraph: {type: "website",locale: "ru_RU",siteName: "WinBoost",title: "WinBoost 4.0 — ваш Windows в лучшей форме",description: "Меньше фонового шума. Больше контроля. Бесплатно для Windows 10 и 11.",images: [{url: "/og-card.svg",width:1200,height:630,alt:"WinBoost 4.0"}]},
  twitter: {card:"summary_large_image",title:"WinBoost 4.0",images:["/og-card.svg"]},
};
export const viewport: Viewport = {width:"device-width",initialScale:1,themeColor:"#111113",colorScheme:"dark"};
export default function RootLayout({children}: Readonly<{children:React.ReactNode}>) {
  return <html lang="ru"><body><a className="skip-link" href="#main">Перейти к содержимому</a>{children}</body></html>;
}
