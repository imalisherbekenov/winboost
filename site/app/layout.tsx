import type { Metadata, Viewport } from "next";
import { Instrument_Serif, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["cyrillic", "latin"],
  variable: "--font-body",
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
  display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["cyrillic", "latin"],
  variable: "--font-mono",
  display: "swap",
});

const siteUrl = "https://winboost.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "WinBoost — безопасная оптимизация Windows",
    template: "%s — WinBoost",
  },
  description:
    "WinBoost анализирует Windows, помогает выбрать оптимизации, показывает изменения до применения и создаёт резервные копии для отката.",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "ru_RU",
    url: siteUrl,
    siteName: "WinBoost",
    title: "WinBoost — настройте Windows осознанно",
    description:
      "10 модулей, 56 действий и твиков, проверка перед применением и откат по умолчанию.",
    images: [
      {
        url: "/og-card.svg",
        width: 1200,
        height: 630,
        alt: "WinBoost — безопасная оптимизация Windows",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "WinBoost — настройте Windows осознанно",
    description:
      "Анализ системы, 56 действий и твиков, проверка и откат изменений.",
    images: ["/og-card.svg"],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#000000",
  colorScheme: "dark",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru" className={`${inter.variable} ${instrumentSerif.variable} ${jetBrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
