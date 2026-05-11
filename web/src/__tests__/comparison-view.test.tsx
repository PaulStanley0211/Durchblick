import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ComparisonView } from "@/components/ComparisonView";

const mockData = {
  horizon_years: 10,
  investment_eur: 10000,
  etfs: [
    {
      isin: "IE00B4L5Y983",
      name: "iShares Core MSCI World UCITS ETF",
      issuer: "iShares (BlackRock)",
      ter: 0.002,
      replication_method: "physical",
      distribution_policy: "accumulating",
      domicile: "IE",
      aum_eur: 85000000000,
      inception_date: "2009-09-25",
      index_tracked: "MSCI World",
      teilfreistellung_class: "equity",
    },
    {
      isin: "IE00BK5BQT80",
      name: "Vanguard FTSE All-World UCITS ETF",
      issuer: "Vanguard",
      ter: 0.0022,
      replication_method: "physical (sampling)",
      distribution_policy: "accumulating",
      domicile: "IE",
      aum_eur: 15000000000,
      inception_date: "2019-07-23",
      index_tracked: "FTSE All-World",
      teilfreistellung_class: "equity",
    },
  ],
  after_tax_eur: [
    { isin: "IE00B4L5Y983", value_eur: 14823.45 },
    { isin: "IE00BK5BQT80", value_eur: 14752.1 },
  ],
};

const enDict = {
  compare: {
    horizon_value: "{years} years",
    investment_label: "Lump-sum investment",
    after_tax_label: "Value after taxes",
    info_label: "Learn more",
    metric: {
      ter: "Total expense ratio (TER)",
      replication: "Replication method",
      distribution: "Distribution policy",
      domicile: "Fund domicile",
      aum: "Fund size",
      inception: "Inception date",
      index: "Index",
      teilfreistellung: "Teilfreistellung class",
    },
    explanation: {
      ter: "The TER explanation goes here.",
      replication: "Replication explanation.",
      distribution: "Distribution explanation.",
      domicile: "Domicile explanation.",
      aum: "AUM explanation.",
      inception: "Inception explanation.",
      index: "Index explanation.",
      teilfreistellung: "Teilfreistellung explanation.",
      after_tax: "After-tax outcome explanation.",
    },
    domicile_value: { IE: "Ireland", LU: "Luxembourg", DE: "Germany" },
    replication_value: {
      physical: "physical",
      "physical (sampling)": "physical (sampling)",
      synthetic: "synthetic",
    },
    distribution_value: { accumulating: "accumulating", distributing: "distributing" },
    teilfreistellung_value: {
      equity: "equity fund (30 percent)",
      mixed: "mixed fund (15 percent)",
      none: "none",
    },
  },
};

describe("ComparisonView", () => {
  it("renders both ETF names as headings", () => {
    // @ts-expect-error - test uses minimal Dictionary subset
    render(<ComparisonView data={mockData} dict={enDict} locale="en" />);
    expect(
      screen.getByRole("heading", { name: "iShares Core MSCI World UCITS ETF" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Vanguard FTSE All-World UCITS ETF" }),
    ).toBeInTheDocument();
  });

  it("renders metric labels for both cards", () => {
    // @ts-expect-error - test uses minimal Dictionary subset
    render(<ComparisonView data={mockData} dict={enDict} locale="en" />);
    expect(screen.getAllByText("Total expense ratio (TER)")).toHaveLength(2);
    expect(screen.getAllByText("Replication method")).toHaveLength(2);
    expect(screen.getAllByText("Fund domicile")).toHaveLength(2);
  });

  it("formats TER as a percentage and domicile via the value dictionary", () => {
    // @ts-expect-error - test uses minimal Dictionary subset
    render(<ComparisonView data={mockData} dict={enDict} locale="en" />);
    expect(screen.getByText("0.20%")).toBeInTheDocument();
    expect(screen.getByText("0.22%")).toBeInTheDocument();
    expect(screen.getAllByText("Ireland")).toHaveLength(2);
  });

  it("renders tap-to-learn explanations in the DOM (details closed by default)", () => {
    // @ts-expect-error - test uses minimal Dictionary subset
    render(<ComparisonView data={mockData} dict={enDict} locale="en" />);
    expect(screen.getAllByText("The TER explanation goes here.")).toHaveLength(2);
    expect(screen.getAllByText("Learn more").length).toBeGreaterThanOrEqual(2);
  });

  it("shows the after-tax outcome formatted as currency", () => {
    // @ts-expect-error - test uses minimal Dictionary subset
    render(<ComparisonView data={mockData} dict={enDict} locale="en" />);
    expect(screen.getByText("€14,823.45")).toBeInTheDocument();
    expect(screen.getByText("€14,752.10")).toBeInTheDocument();
  });
});
