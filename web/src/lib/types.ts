export type Etf = {
  isin: string;
  name: string;
  issuer: string;
  ter: number;
  replication_method: string;
  distribution_policy: string;
  domicile: string;
  aum_eur: number;
  inception_date: string;
  index_tracked: string;
  teilfreistellung_class: string;
};

export type AfterTaxOutcome = {
  isin: string;
  value_eur: number;
};

export type ComparisonResponse = {
  horizon_years: number;
  investment_eur: number;
  etfs: Etf[];
  after_tax_eur: AfterTaxOutcome[];
};
