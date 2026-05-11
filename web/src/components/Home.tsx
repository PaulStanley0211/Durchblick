import type { Dictionary, Locale } from "@/dictionaries";

export function Home({ dict, locale }: { dict: Dictionary; locale: Locale }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 text-center">
      <h1 className="text-4xl font-semibold tracking-tight">{dict.home.title}</h1>
      <p className="mt-4 max-w-md text-lg text-zinc-600 dark:text-zinc-400">{dict.home.tagline}</p>
      <a
        href={`/${locale}/compare`}
        className="mt-8 rounded-md bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
      >
        {dict.home.compare_cta}
      </a>
    </main>
  );
}
