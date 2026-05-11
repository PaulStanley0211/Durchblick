import type { ComparisonResponse, Etf } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function getComparison(isinA: string, isinB: string): Promise<ComparisonResponse> {
  const url = `${API_BASE}/comparison?isin_a=${encodeURIComponent(isinA)}&isin_b=${encodeURIComponent(isinB)}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Comparison API returned ${res.status}`);
  }
  return res.json();
}

export async function listEtfs(): Promise<Etf[]> {
  const url = `${API_BASE}/etfs`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Etfs API returned ${res.status}`);
  }
  return res.json();
}
