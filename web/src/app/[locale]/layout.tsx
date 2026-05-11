import "../globals.css";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { notFound } from "next/navigation";

import { getDictionary, hasLocale, locales } from "@/dictionaries";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Durchblick",
  description: "ETF comparison with German tax.",
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function RootLayout({ children, params }: LayoutProps<"/[locale]">) {
  const { locale } = await params;
  if (!hasLocale(locale)) notFound();
  const dict = await getDictionary(locale);
  const otherLocale = locale === "de" ? "en" : "de";

  return (
    <html
      lang={locale}
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <header className="border-b border-zinc-200 dark:border-zinc-800">
          <nav className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
            <a href={`/${locale}`} className="text-sm font-semibold">
              {dict.home.title}
            </a>
            <a
              href={`/${otherLocale}`}
              className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
            >
              {dict.common.lang_switch_to}
            </a>
          </nav>
        </header>
        {children}
        <footer className="mt-auto border-t border-zinc-200 dark:border-zinc-800">
          <div className="mx-auto w-full max-w-5xl px-4 py-6 text-xs text-zinc-500 sm:px-6">
            {dict.common.disclaimer_not_advice}
          </div>
        </footer>
      </body>
    </html>
  );
}
