import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Home } from "@/components/Home";

const deDict = {
  home: { title: "Durchblick", tagline: "ETF-Vergleich mit deutscher Steuer." },
};

const enDict = {
  home: { title: "Durchblick", tagline: "ETF comparison with German tax." },
};

describe("Home", () => {
  it("renders the German title and tagline", () => {
    render(<Home dict={deDict} />);
    expect(screen.getByRole("heading", { name: "Durchblick" })).toBeInTheDocument();
    expect(screen.getByText("ETF-Vergleich mit deutscher Steuer.")).toBeInTheDocument();
  });

  it("renders the English title and tagline", () => {
    render(<Home dict={enDict} />);
    expect(screen.getByRole("heading", { name: "Durchblick" })).toBeInTheDocument();
    expect(screen.getByText("ETF comparison with German tax.")).toBeInTheDocument();
  });
});
