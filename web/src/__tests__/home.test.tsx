import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Home } from "@/components/Home";

const deDict = {
  home: {
    title: "Durchblick",
    tagline: "ETF-Vergleich mit deutscher Steuer.",
    compare_cta: "Vergleich starten",
  },
};

const enDict = {
  home: {
    title: "Durchblick",
    tagline: "ETF comparison with German tax.",
    compare_cta: "Start comparison",
  },
};

describe("Home", () => {
  it("renders the German title, tagline, and a compare CTA linking to /de/compare", () => {
    // @ts-expect-error - the test passes a minimal subset of the Dictionary type
    render(<Home dict={deDict} locale="de" />);
    expect(screen.getByRole("heading", { name: "Durchblick" })).toBeInTheDocument();
    expect(screen.getByText("ETF-Vergleich mit deutscher Steuer.")).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: "Vergleich starten" });
    expect(cta).toHaveAttribute("href", "/de/compare");
  });

  it("renders the English title, tagline, and a compare CTA linking to /en/compare", () => {
    // @ts-expect-error - the test passes a minimal subset of the Dictionary type
    render(<Home dict={enDict} locale="en" />);
    expect(screen.getByRole("heading", { name: "Durchblick" })).toBeInTheDocument();
    expect(screen.getByText("ETF comparison with German tax.")).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: "Start comparison" });
    expect(cta).toHaveAttribute("href", "/en/compare");
  });
});
