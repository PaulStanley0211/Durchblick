# Phase 8 — German tax calculation module

Date: 2026-05-11
Status: Approved (design)
Author: Paul Stanley with Claude Code

## §1. Context

Phase 7 retired the static ETF mock and seeded the curated 15-row
ETF universe into Postgres. `/etfs` and `/comparison` now read from
the database, but the after-tax outcome in `/comparison` is still
served by the placeholder `_HARDCODED_AFTER_TAX_EUR` map in
`api/app/api/comparison.py`. That map's docstring promises:
"Phase 8 tax module" and "Phase 9 replaces the hardcoded numbers
with real DB lookups and the Phase 8 tax module."

Phase 8 builds the tax module as a pure, self-contained calculation
layer. Phase 9 will wire it into the `/comparison` endpoint.

Five tax rules from CLAUDE.md's domain glossary appear: Vorabpauschale
(§18 InvStG), Teilfreistellung (§20 InvStG), Sparerpauschbetrag
(§20(9) EStG), Abgeltungsteuer / capital gains (§32d EStG), and
Solidaritätszuschlag. Kirchensteuer is documented in the glossary
but deliberately deferred (see §2).

The `tax_constants` table already exists from Phase 5 with year-keyed
rows for 2023-2026 (basiszins, sparerpauschbetrag_eur,
teilfreistellung_equity, teilfreistellung_mixed, capital_gains_rate,
solidaritaetszuschlag_rate). The seed pattern is established. This
phase builds the calculation that consumes those rows.

## §2. Goals and non-goals

In scope:

- A new `api/app/tax/` package with six pure primitive functions
  (Basisertrag, Vorabpauschale clamp, Teilfreistellung,
  Sparerpauschbetrag, Abgeltungsteuer, Solidaritätszuschlag) and
  two orchestrators (lump-sum, Sparplan). Vorabpauschale (§18 InvStG)
  splits into two primitives so the Sparplan can sum split bases
  before clamping.
- An immutable `TaxConstantsSnapshot` dataclass mirroring a row of
  `tax_constants`, plus a fallback helper that resolves any
  requested year to the latest available row.
- A `load_tax_constants_by_year` repository function that hydrates
  a dict of snapshots from the DB in one query.
- A `TaxOutcome` Pydantic model (with `VorabpauschaleYear` per-year
  records) returned by both orchestrators.
- Comprehensive unit tests, golden-value scenarios derived by
  hand-tracing, and 100% line-coverage enforcement on
  `api/app/tax/` and `api/app/repositories/tax_constants.py`.

Out of scope (deferred):

- Wiring the orchestrators into `/comparison`. That is Phase 9.
- Kirchensteuer (church tax). Adding it later is a non-breaking
  optional parameter on the orchestrators.
- Couple-vs-single Sparerpauschbetrag (€2,000 joint). Default is
  single (€1,000). Adding `is_jointly_assessed: bool = False`
  later is also non-breaking.
- Distribution-policy distinction inside Vorabpauschale (the formula
  reduces Basisertrag by distributions for distributing funds). For
  Phase 8 we use the accumulating-fund formula uniformly; distributing
  funds are slightly over-taxed. Documented limitation.
- Per-state Kirchensteuer rates (8% Bayern/BW, 9% elsewhere).
- Front-end changes. No web code is touched.
- Return-rate projection. The orchestrator takes a flat annual rate
  as input; Phase 9 picks the value.

Two domain choices worth flagging:

- **Sparerpauschbetrag applied per-ETF**: each comparison is framed
  as "if this ETF were your only investment". This is the honest
  side-by-side framing; legally accurate per-taxpayer aggregation
  would require summing both ETFs and is not representable in a
  comparison view.
- **Tax paid out of pocket**: the orchestrator models the investor
  paying year-end Vorabpauschale taxes from outside the fund (as
  German brokers actually do with the Freistellungsauftrag pipeline).
  Final after-tax value = `final_gross_value - sum_of_yearly_taxes`.

## §3. Architecture

```
api/
  app/
    tax/                                (new package)
      __init__.py                       (~10 lines) — re-exports
      constants.py                      (~25 lines) — snapshot + fallback
      primitives.py                     (~45 lines) — five rules
      outcome.py                        (~40 lines) — two Pydantic models
      engine.py                         (~100 lines) — orchestrators
    repositories/
      tax_constants.py                  (~20 lines) — DB loader

  tests/
    fixtures/
      tax_constants_2023_2026.py        — Python literal matching seeded rows
    unit/
      test_tax_constants.py             — fallback logic
      test_tax_primitives.py            — exhaustive rule cases
      test_tax_outcome.py               — serialization round-trips
      test_tax_lump_sum.py              — golden-value scenarios
      test_tax_sparplan.py              — golden-value scenarios
    integration/
      test_tax_constants_repo.py        — DB loader against Docker Postgres

  pyproject.toml                        — add [tool.coverage] gate
.github/workflows/ci.yml                — add --cov flags + 100% fail-under

CLAUDE.md                               — append Phase 8 milestone
README.md                               — add tax-math bullet to Status
```

Total ~240 lines of code, ~500-600 lines of tests.

**Public surface** (`api/app/tax/__init__.py` re-exports):
- `TaxOutcome`, `VorabpauschaleYear`
- `TaxConstantsSnapshot`, `lookup_year_with_fallback`
- `compute_lump_sum_outcome`, `compute_sparplan_outcome`

Phase 9 imports only from `app.tax`, never from `app.tax.engine` or
`app.tax.primitives` directly.

**Internal dependency graph:**

```
constants.py ─┐
primitives.py ├─→ engine.py ─→ __init__.py
outcome.py   ─┘
```

No cycles. `engine.py` is the only orchestration layer; the
primitives don't know about TaxOutcome and TaxOutcome doesn't know
about primitives.

**Why `engine.py` instead of separate `lump_sum.py` and `sparplan.py`:**
the two orchestrators share ~80% of their per-year body (Vorabpauschale
→ Teilfreistellung → Sparerpauschbetrag → Abgeltungsteuer → Soli →
record). Splitting them into two files duplicates that body; combining
them into one engine module with a private `_run_year_loop` helper
keeps each scenario function short (10-15 lines) and the shared math
in one place.

**Why a Python fixture rather than YAML for tax_constants_2023_2026.py:**
the seeded rows are short and already inlined in
`scripts/seed_tax_constants.py`. The fixture is essentially a literal
copy; Python lets tests reference exact Decimal values without YAML
parsing intermediates.

## §4. TaxConstantsSnapshot and fallback lookup

`api/app/tax/constants.py`:

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TaxConstantsSnapshot:
    year: int
    basiszins: Decimal
    sparerpauschbetrag_eur: Decimal
    teilfreistellung_equity: Decimal
    teilfreistellung_mixed: Decimal
    capital_gains_rate: Decimal
    solidaritaetszuschlag_rate: Decimal


def lookup_year_with_fallback(
    by_year: dict[int, TaxConstantsSnapshot],
    year: int,
) -> TaxConstantsSnapshot:
    """Return the snapshot for `year`. If absent, return the latest year present.

    Raises ValueError if the dict is empty.
    """
    if year in by_year:
        return by_year[year]
    if not by_year:
        raise ValueError("tax constants dict is empty")
    return by_year[max(by_year)]
```

Behavior:
- `year=2030` with seeded `{2023..2026}` → returns 2026 snapshot.
- `year=2022` with the same dict → returns 2026 snapshot. The
  fallback is symmetric (past- and future-year cases both fall back
  to the latest). The past-year case is a programming error, not a
  user scenario, so the asymmetry would buy nothing.
- Empty dict → `ValueError`. The orchestrator does not catch this;
  "tax constants not seeded" is a hard refusal.

`frozen=True` makes accidental mutation an error. `slots=True` is a
minor memory optimization and rejects typo-attribute writes.

Repository (`api/app/repositories/tax_constants.py`):

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TaxConstant
from app.tax.constants import TaxConstantsSnapshot


def load_tax_constants_by_year(
    session: Session,
) -> dict[int, TaxConstantsSnapshot]:
    rows = session.execute(select(TaxConstant)).scalars().all()
    return {
        row.year: TaxConstantsSnapshot(
            year=row.year,
            basiszins=row.basiszins,
            sparerpauschbetrag_eur=row.sparerpauschbetrag_eur,
            teilfreistellung_equity=row.teilfreistellung_equity,
            teilfreistellung_mixed=row.teilfreistellung_mixed,
            capital_gains_rate=row.capital_gains_rate,
            solidaritaetszuschlag_rate=row.solidaritaetszuschlag_rate,
        )
        for row in rows
    }
```

One DB roundtrip; the result is a small dict (4-6 entries). Phase 9
calls this once per request and passes the dict to the orchestrator,
which uses `lookup_year_with_fallback` per projection year.

Primitives stay pure: they take a snapshot, never a session. Unit
tests build a dict in-process, never touching the DB.

## §5. The primitives

`api/app/tax/primitives.py`. Each is a one-expression pure function
returning a Decimal. Vorabpauschale (§18 InvStG) is the only rule
that splits into two primitives — Basisertrag (the per-holding base)
and the min/max clamp itself — so the Sparplan can sum two Basiserträge
(old principal full year, new contributions half year) before clamping.

### Basisertrag (the Vorabpauschale base term)

```python
def compute_basisertrag(
    fund_value: Decimal,
    basiszins: Decimal,
    months_held: int = 12,
) -> Decimal:
    """Basisertrag: fund_value * basiszins * 0.7, pro-rated by months_held/12."""
    return (
        fund_value
        * basiszins
        * Decimal("0.7")
        * Decimal(months_held)
        / Decimal("12")
    )
```

### Vorabpauschale clamp

```python
def compute_vorabpauschale(
    basisertrag: Decimal,
    realized_return: Decimal,
) -> Decimal:
    """Vorabpauschale = max(0, min(basisertrag, realized_return))."""
    return max(Decimal("0"), min(basisertrag, realized_return))
```

The orchestrator builds `basisertrag` and `realized_return` for the
scenario it models, then calls this primitive. Lump-sum: one
Basisertrag from `fund_value * basiszins * 0.7`. Sparplan: sum of
two Basiserträge, one for the opening balance (full year) and one
for the year's contributions (half year on the mid-year convention).
This keeps each scenario's per-year derivation explicit and the
primitive trivially testable.

Boundary cases (in `test_tax_primitives.py`):

For `compute_basisertrag`:
- `months_held=12` → full Basisertrag.
- `months_held=6` → half Basisertrag.
- `months_held=0` → 0 cleanly (no division surprise).
- `basiszins=0` → 0.
- `fund_value=0` → 0.

For `compute_vorabpauschale`:
- Negative realized return → 0 (`min` selects the negative; `max(0)` clamps back).
- Realized return below Basisertrag → realized return.
- Realized return above Basisertrag → Basisertrag.
- Both zero → 0.

### Teilfreistellung (§20 InvStG)

```python
def apply_teilfreistellung(
    taxable_base: Decimal,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    constants: TaxConstantsSnapshot,
) -> Decimal:
    """Return the base after the equity/mixed/none exemption is applied."""
    rate = {
        "equity": constants.teilfreistellung_equity,
        "mixed": constants.teilfreistellung_mixed,
        "none": Decimal("0"),
    }[teilfreistellung_class]
    return taxable_base * (Decimal("1") - rate)
```

The `Literal` makes the choice exhaustive at the call site; pyright
catches typos.

### Sparerpauschbetrag

```python
def apply_sparerpauschbetrag(
    post_teilfreistellung_income: Decimal,
    allowance: Decimal,
) -> Decimal:
    """Return income reduced by the year's allowance, floored at 0."""
    return max(Decimal("0"), post_teilfreistellung_income - allowance)
```

Single-taxpayer convention: caller passes €1,000 (the year's
`constants.sparerpauschbetrag_eur`).

### Abgeltungsteuer

```python
def compute_capital_gains_tax(
    taxable_income: Decimal,
    capital_gains_rate: Decimal,
) -> Decimal:
    """Flat-rate capital gains tax."""
    return taxable_income * capital_gains_rate
```

### Solidaritätszuschlag

```python
def compute_solidaritaetszuschlag(
    capital_gains_tax: Decimal,
    solidaritaetszuschlag_rate: Decimal,
) -> Decimal:
    """Surcharge on capital gains tax (not on income)."""
    return capital_gains_tax * solidaritaetszuschlag_rate
```

The signature names the base explicitly — the easiest German tax
rule to get wrong is "5.5% on top of what".

### Rounding

Primitives return unrounded Decimals. The engine rounds once per
year at the end of the year's tax calculation:

```python
def _round_eur(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
```

Banker's rounding matches how German brokers report withholding.
Defining rounding at the boundary keeps primitive tests deterministic
and prevents round-off accumulation across composition.

## §6. The orchestrators

`api/app/tax/engine.py` holds both. They share a private year loop.

### Lump-sum

```python
def compute_lump_sum_outcome(
    *,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    investment_eur: Decimal,
    horizon_years: int,
    annual_return_rate: Decimal,
    start_year: int,
    tax_constants_by_year: dict[int, TaxConstantsSnapshot],
) -> TaxOutcome:
    ...
```

Keyword-only (six parameters; positional order would be a footgun).

Algorithm per year `offset` in `range(horizon_years)`:

1. `year = start_year + offset`; `constants = lookup_year_with_fallback(tax_constants_by_year, year)`.
2. `v_end = fund_value * (Decimal("1") + annual_return_rate)`.
3. `basisertrag = compute_basisertrag(fund_value, constants.basiszins)` (months_held defaults to 12).
4. `vorabpauschale = compute_vorabpauschale(basisertrag, v_end - fund_value)`.
5. `is_final_year = offset == horizon_years - 1`.
6. If final year:
   ```
   prior_vp_sum = sum(record.vorabpauschale_eur for record in history)
   realized_gain = max(0, v_end - investment_eur - prior_vp_sum - vorabpauschale)
   ```
   Else `realized_gain = 0`.
7. `taxable_after_tf = apply_teilfreistellung(vorabpauschale + realized_gain, teilfreistellung_class, constants)`.
8. `after_spb = apply_sparerpauschbetrag(taxable_after_tf, constants.sparerpauschbetrag_eur)`.
9. `cgt = compute_capital_gains_tax(after_spb, constants.capital_gains_rate)`.
10. `soli = compute_solidaritaetszuschlag(cgt, constants.solidaritaetszuschlag_rate)`.
11. `year_tax = _round_eur(cgt + soli)`.
12. Record the year, update `fund_value = v_end`, accumulate tax.

After the loop, return a `TaxOutcome` whose `final_after_tax_value_eur = v_end - cumulative_tax_paid`.

### Sparplan (annual aggregation, mid-year convention)

```python
def compute_sparplan_outcome(
    *,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    monthly_contribution_eur: Decimal,
    horizon_years: int,
    annual_return_rate: Decimal,
    start_year: int,
    tax_constants_by_year: dict[int, TaxConstantsSnapshot],
) -> TaxOutcome:
    ...
```

Same skeleton; only the per-year fund-value evolution differs.

Each year contributes `C = monthly_contribution_eur * Decimal("12")` of
new principal. With the mid-year convention:

- Year-end fund value: `v_end = fund_value * (1 + r) + C * (1 + r * Decimal("0.5"))`
- Basisertrag is the SUM of two calls to `compute_basisertrag`:
  - `compute_basisertrag(fund_value, basiszins, months_held=12)` for the opening balance held all year
  - `compute_basisertrag(C, basiszins, months_held=6)` for the year's contributions held an average of six months
- Realized year-gain for the Vorabpauschale clamp: `v_end - fund_value - C` (growth only, excluding new principal).
- `vorabpauschale = compute_vorabpauschale(basisertrag_old + basisertrag_new, realized_year_gain)`.

Final-year realized gain at sale:
```
total_invested = monthly_contribution_eur * Decimal("12") * Decimal(horizon_years)
prior_vp_sum   = sum(record.vorabpauschale_eur for record in history)
realized_gain  = max(0, v_end - total_invested - prior_vp_sum - vorabpauschale)
```

Everything from Teilfreistellung onward is identical to lump-sum and
lives in the shared `_run_year_loop` body.

### `start_year`

Phase 9 will pass `start_year = current_year`. Unit tests lock
`start_year` (typically 2026) so the constants resolved are
deterministic.

### Edge cases with deliberate behaviors

| Input | Behavior |
|---|---|
| `horizon_years = 0` | `ValueError` (zero-year hold is not meaningful) |
| `horizon_years = 1` | Works; one iteration, immediately final |
| `annual_return_rate = 0` | Vorabpauschale = 0 every year; total tax = 0 |
| `annual_return_rate < 0` | Vorabpauschale clamps to 0; realized gain clamps to 0; total tax = 0; after-tax value < invested principal |
| `investment_eur = 0` (lump-sum) | `ValueError` |
| `monthly_contribution_eur = 0` (Sparplan) | `ValueError` |
| `tax_constants_by_year = {}` | Propagates `ValueError` from `lookup_year_with_fallback` |

## §7. TaxOutcome shape

`api/app/tax/outcome.py`. Two Pydantic models, both frozen.

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class VorabpauschaleYear(BaseModel):
    model_config = ConfigDict(frozen=True)

    year: int
    vorabpauschale_eur: Decimal
    realized_gain_eur: Decimal               # 0 except in the final year
    teilfreistellung_eur: Decimal            # the exempted amount this year
    sparerpauschbetrag_used_eur: Decimal     # how much allowance was consumed
    capital_gains_tax_eur: Decimal
    solidaritaetszuschlag_eur: Decimal
    total_tax_eur: Decimal                   # rounded to 2dp


class TaxOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario: Literal["lump_sum", "sparplan"]
    teilfreistellung_class: Literal["equity", "mixed", "none"]
    horizon_years: int
    start_year: int
    annual_return_rate: Decimal

    total_invested_eur: Decimal
    final_gross_value_eur: Decimal           # before tax-paid subtraction
    total_tax_paid_eur: Decimal              # sum across all years
    final_after_tax_value_eur: Decimal       # final_gross - total_tax

    yearly_breakdown: list[VorabpauschaleYear]
```

Both `final_gross_value_eur` and `final_after_tax_value_eur` are
kept. Phase 9 shows the after-tax number prominently and discloses
the gross-vs-net delta in tap-to-learn.

`yearly_breakdown` is the per-year audit trail Phase 9 uses to
explain WHY one ETF taxes more. Size: one row per `horizon_years`
(typically 10-30 entries).

`scenario` and `teilfreistellung_class` are echoed back even though
the caller passed them. Self-describing JSON.

`frozen=True` together with the orchestrators always returning a
freshly built instance prevents accidental mutation of cached
results.

Decimal serialization: Pydantic v2 emits `Decimal` as a JSON string
by default (e.g. `"14823.45"`). The tax module never converts to
float. Phase 9 will convert at the API boundary (the existing
`/comparison` response model declares `float`); the conversion
happens there, not inside `app/tax/`.

`effective_tax_rate_pct` is deliberately NOT a field. It's derivable
and the divisor can be zero. Phase 9 can compute it for display;
the module doesn't owe consumers pre-computed ratios.

## §8. Testing

Coverage gate: `api/app/tax/` and `api/app/repositories/tax_constants.py`
must hit 100% line coverage. CI enforces with `pytest-cov`. New
`[tool.coverage.run]` and `[tool.coverage.report]` sections in
`api/pyproject.toml` with `fail_under = 100`. The CI Pytest step
gains one new line:

```yaml
run: uv run pytest --cov=app/tax --cov=app/repositories/tax_constants --cov-fail-under=100
```

This is the first place the project enforces coverage in CI. The
gate is local to the tax module — handlers, models, and other code
are unaffected.

### Test files

`tests/fixtures/tax_constants_2023_2026.py`: a Python literal
mirroring the seeded rows. Used by all unit tests to avoid a DB
dependency.

`tests/unit/test_tax_constants.py` (6 tests):
- year present
- year future → fallback to latest
- year past → fallback to latest
- single-row dict
- empty dict → `ValueError`
- mutation of a frozen snapshot raises

`tests/unit/test_tax_primitives.py` (~14 tests). Boundary cases per
primitive as documented in §5: 5 for `compute_basisertrag`, 4 for
`compute_vorabpauschale`, 4 for `apply_teilfreistellung`, 3 for
`apply_sparerpauschbetrag` (below/equal/above allowance), 2 each
for `compute_capital_gains_tax` and `compute_solidaritaetszuschlag`.

`tests/unit/test_tax_outcome.py` (3 tests):
- round-trip `.model_dump()` + `model_validate(...)`
- mutation raises (frozen)
- Decimal precision survives (e.g. `Decimal('14823.45')` does not
  become `14823.45000000001`)

`tests/unit/test_tax_lump_sum.py` (6 tests):
- €10,000 over 1 year at 5%, equity ETF, start_year 2026
- €10,000 over 10 years at 5%, equity ETF (canonical scenario)
- €10,000 over 10 years at 0% → after-tax == invested
- €10,000 over 10 years at -3% → no tax, after-tax < invested
- `horizon_years=0` raises `ValueError`
- `investment_eur=0` raises `ValueError`

`tests/unit/test_tax_sparplan.py` (5 tests):
- €100/month over 10 years at 5%, equity ETF
- €100/month over 1 year at 5% (single-year Sparplan stresses
  mid-year split)
- €100/month over 10 years at 0% → total invested == final, zero tax
- `monthly_contribution_eur=0` raises `ValueError`
- Verifies prior-year Vorabpauschale is fully credited against
  final-year realized gain

`tests/integration/test_tax_constants_repo.py` (1 test): seeded DB
roundtrip; asserts all four years present and snapshot Decimals
match the seed byte-for-byte.

### Golden-value derivation

Canonical-scenario test bodies include a comment block with the
year-by-year hand trace: Basiszins used, Basisertrag, Vorabpauschale,
Teilfreistellung, taxes. Without this trace, the golden numbers
become unmaintainable. The standard practice for tax math.

### What's NOT tested

- Symbolic equivalence to the BMF circular's formulas. (We use the
  same formulas; "matches official BMF Excel" is a manual
  verification task.)
- Float-vs-Decimal precision drift. Impossible by construction:
  nothing in the tax module imports `float`.
- Year-2050 hypothetical BMF rate changes. The fallback is
  deterministic; no point in testing hypotheticals.

### Test count

~34 unit + 1 integration = 35 added. Combined with existing 21 → ~56.

## §9. Operations and rollout

Dependencies: none new. `pytest-cov` is already in dev deps.

`pyproject.toml` additions:

```toml
[tool.coverage.run]
source = ["app/tax", "app/repositories/tax_constants"]
branch = false

[tool.coverage.report]
fail_under = 100
show_missing = true
skip_covered = false
```

`branch = false` keeps the gate at line coverage only (per
CLAUDE.md's "100% line coverage"). Branch coverage on tax math is
overkill for the size of the branch surface.

CI workflow change in `.github/workflows/ci.yml`:

```yaml
- name: Pytest
  working-directory: api
  run: uv run pytest --cov=app/tax --cov=app/repositories/tax_constants --cov-fail-under=100
```

Local rollout for a developer after pulling Phase 8:

1. `cd api && uv sync` (no-op; no new deps)
2. Existing Docker Postgres + migrations stay as-is
3. `make test` runs everything including the new tax suite
4. The web app is untouched; `/de/compare` still shows the
   `_HARDCODED_AFTER_TAX_EUR` map through Phase 9

No deployment impact. Phase 4 still deferred. No API surface change.
`_HARDCODED_AFTER_TAX_EUR` stays put.

Docs in the same PR:
- `CLAUDE.md`: append Phase 8 to "Shipped milestones"; update the
  "Phases implemented" line.
- `README.md`: add a tax-math bullet noting the German tax module
  exists with 100% line coverage.

## §10. Commit plan

One logical change per commit:

1. `chore(api): add tax-module coverage configuration`
2. `feat(api): add TaxConstantsSnapshot and fallback lookup`
3. `feat(api): add tax_constants repository`
4. `feat(api): add TaxOutcome and VorabpauschaleYear models`
5. `feat(api): add tax primitive functions`
6. `feat(api): add lump-sum and Sparplan orchestrators`
7. `feat(api): wire tax-module public surface`
8. `chore(ci): enforce 100% coverage on tax module`
9. `docs: note Phase 8 in CLAUDE.md and README.md`

Nine commits, ~240 lines of code, ~500-600 lines of tests.

Ordering rationale: coverage config (1) lands first so any tax code
added afterward is measured. Constants and repository (2-3) provide
data plumbing. Outcome models (4) define the return type. Primitives
(5) and orchestrators (6) consume both. The public surface (7) only
re-exports symbols that already exist. The CI gate (8) flips on after
the module self-tests at 100%. Docs (9) close.

## §11. Open questions and follow-ups

None for Phase 8 itself. Deliberate follow-ups for later phases:

- Phase 9 (DB + tax wiring): wire `compute_lump_sum_outcome` (and
  optionally `compute_sparplan_outcome`) into `/comparison`. Pick
  an `annual_return_rate` source. Add a Playwright spec.
- Later: introduce Kirchensteuer as an optional parameter on both
  orchestrators (non-breaking).
- Later: introduce `is_jointly_assessed: bool = False` for
  €2,000 Sparerpauschbetrag (non-breaking).
- Later: distribution-policy-aware Vorabpauschale (reduce
  Basisertrag by distributions for distributing funds).
- Later: per-ETF historical return data on the `etfs` table to
  replace user-supplied flat `annual_return_rate`.
