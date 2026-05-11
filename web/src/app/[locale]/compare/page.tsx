import { notFound } from "next/navigation";

import { ComparisonView } from "@/components/ComparisonView";
import { getDictionary, hasLocale } from "@/dictionaries";
import { getComparison, listEtfs } from "@/lib/api";
import type { ComparisonResponse } from "@/lib/types";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ a?: string; b?: string }>;
};

export default async function ComparePage({ params, searchParams }: Props) {
  const { locale } = await params;
  if (!hasLocale(locale)) notFound();
  const dict = await getDictionary(locale);

  const { a, b } = await searchParams;
  const etfs = await listEtfs();

  const isinA = typeof a === "string" && etfs.some((e) => e.isin === a) ? a : (etfs[0]?.isin ?? "");
  const isinB =
    typeof b === "string" && etfs.some((e) => e.isin === b) ? b : (etfs[1]?.isin ?? isinA);

  let comparison: ComparisonResponse | null;
  try {
    comparison = await getComparison(isinA, isinB);
  } catch {
    comparison = null;
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">{dict.compare.heading}</h1>
        <p className="mt-2 text-zinc-600 dark:text-zinc-400">{dict.compare.subheading}</p>
      </header>

      <form method="GET" className="mb-8 grid grid-cols-1 gap-3 sm:grid-cols-3 sm:items-end">
        <label className="flex flex-col text-sm">
          <span className="mb-1 text-zinc-600 dark:text-zinc-400">{dict.compare.select_a}</span>
          <select
            name="a"
            defaultValue={isinA}
            className="rounded-md border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950"
          >
            {etfs.map((etf) => (
              <option key={etf.isin} value={etf.isin}>
                {etf.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-sm">
          <span className="mb-1 text-zinc-600 dark:text-zinc-400">{dict.compare.select_b}</span>
          <select
            name="b"
            defaultValue={isinB}
            className="rounded-md border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950"
          >
            {etfs.map((etf) => (
              <option key={etf.isin} value={etf.isin}>
                {etf.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          {dict.compare.submit}
        </button>
      </form>

      {comparison ? (
        <ComparisonView data={comparison} dict={dict} locale={locale} />
      ) : (
        <p className="text-sm text-zinc-600">{dict.common.error_loading}</p>
      )}

      <p className="mt-6 text-xs text-zinc-500">{dict.common.disclaimer_past_returns}</p>
    </main>
  );
}
