import type { Dictionary } from "@/dictionaries";
import type { ComparisonResponse, Etf } from "@/lib/types";

type ComparisonViewProps = {
  data: ComparisonResponse;
  dict: Dictionary;
  locale: string;
};

function formatPercent(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatCurrency(value: number, locale: string, maximumFractionDigits = 0): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits,
  }).format(value);
}

function formatCompactCurrency(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatDate(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(iso));
}

type MetricRowProps = {
  label: string;
  value: string;
  explanation: string;
  infoLabel: string;
};

function MetricRow({ label, value, explanation, infoLabel }: MetricRowProps) {
  return (
    <div className="border-b border-zinc-200 py-3 last:border-b-0 dark:border-zinc-800">
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-sm text-zinc-600 dark:text-zinc-400">{label}</span>
        <span className="text-right font-medium">{value}</span>
      </div>
      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200">
          {infoLabel}
        </summary>
        <p className="mt-1 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
          {explanation}
        </p>
      </details>
    </div>
  );
}

type EtfCardProps = {
  etf: Etf;
  afterTax: number;
  investment: number;
  horizonYears: number;
  dict: Dictionary;
  locale: string;
};

function EtfCard({ etf, afterTax, investment, horizonYears, dict, locale }: EtfCardProps) {
  const c = dict.compare;
  const domicileLabel =
    c.domicile_value[etf.domicile as keyof typeof c.domicile_value] ?? etf.domicile;
  const replicationLabel =
    c.replication_value[etf.replication_method as keyof typeof c.replication_value] ??
    etf.replication_method;
  const distributionLabel =
    c.distribution_value[etf.distribution_policy as keyof typeof c.distribution_value] ??
    etf.distribution_policy;
  const teilfreistellungLabel =
    c.teilfreistellung_value[etf.teilfreistellung_class as keyof typeof c.teilfreistellung_value] ??
    etf.teilfreistellung_class;
  const horizonLabel = c.horizon_value.replace("{years}", String(horizonYears));

  return (
    <article className="flex flex-col rounded-xl border border-zinc-200 p-6 dark:border-zinc-800">
      <header className="mb-2 border-b border-zinc-200 pb-3 dark:border-zinc-800">
        <h2 className="text-lg leading-tight font-semibold">{etf.name}</h2>
        <p className="mt-1 text-xs text-zinc-500">
          {etf.isin} - {etf.issuer}
        </p>
      </header>

      <MetricRow
        label={c.metric.ter}
        value={formatPercent(etf.ter, locale)}
        explanation={c.explanation.ter}
        infoLabel={c.info_label}
      />
      <MetricRow
        label={c.metric.replication}
        value={replicationLabel}
        explanation={c.explanation.replication}
        infoLabel={c.info_label}
      />
      <MetricRow
        label={c.metric.distribution}
        value={distributionLabel}
        explanation={c.explanation.distribution}
        infoLabel={c.info_label}
      />
      <MetricRow
        label={c.metric.domicile}
        value={domicileLabel}
        explanation={c.explanation.domicile}
        infoLabel={c.info_label}
      />
      <MetricRow
        label={c.metric.aum}
        value={formatCompactCurrency(etf.aum_eur, locale)}
        explanation={c.explanation.aum}
        infoLabel={c.info_label}
      />
      <MetricRow
        label={c.metric.inception}
        value={formatDate(etf.inception_date, locale)}
        explanation={c.explanation.inception}
        infoLabel={c.info_label}
      />
      <MetricRow
        label={c.metric.index}
        value={etf.index_tracked}
        explanation={c.explanation.index}
        infoLabel={c.info_label}
      />
      <MetricRow
        label={c.metric.teilfreistellung}
        value={teilfreistellungLabel}
        explanation={c.explanation.teilfreistellung}
        infoLabel={c.info_label}
      />

      <div className="mt-4 rounded-lg bg-zinc-100 p-4 dark:bg-zinc-900">
        <div className="mb-1 text-xs text-zinc-500">
          {c.after_tax_label} - {horizonLabel}
        </div>
        <div className="text-2xl font-semibold">{formatCurrency(afterTax, locale, 2)}</div>
        <div className="mt-1 text-xs text-zinc-500">
          {c.investment_label}: {formatCurrency(investment, locale)}
        </div>
        <details className="mt-3">
          <summary className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200">
            {c.info_label}
          </summary>
          <p className="mt-1 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
            {c.explanation.after_tax}
          </p>
        </details>
      </div>
    </article>
  );
}

export function ComparisonView({ data, dict, locale }: ComparisonViewProps) {
  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {data.etfs.map((etf, idx) => (
        <EtfCard
          key={etf.isin}
          etf={etf}
          afterTax={data.after_tax_eur[idx]?.value_eur ?? 0}
          investment={data.investment_eur}
          horizonYears={data.horizon_years}
          dict={dict}
          locale={locale}
        />
      ))}
    </section>
  );
}
