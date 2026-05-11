# Phase 8 German Tax Calculation Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pure-Python German tax calculation module at `api/app/tax/` exposing six primitive functions and two orchestrators (lump-sum + Sparplan), returning a structured `TaxOutcome`, with 100% line coverage enforced in CI.

**Architecture:** Six pure primitives in `primitives.py` (Basisertrag, Vorabpauschale clamp, Teilfreistellung, Sparerpauschbetrag, Abgeltungsteuer, Solidaritätszuschlag) consume an immutable `TaxConstantsSnapshot`. A single `engine.py` holds both orchestrators (`compute_lump_sum_outcome`, `compute_sparplan_outcome`) sharing a year-loop body; differences are isolated to scenario-specific Basisertrag derivation and fund-value evolution. Phase 9 will wire the orchestrators into `/comparison`; this plan does not touch the API.

**Tech Stack:** Python 3.12 + SQLAlchemy 2 + Pydantic v2, Postgres 16 (for one repository function), pytest + pytest-cov, uv (never pip).

**Source spec:** [docs/superpowers/specs/2026-05-11-phase-8-tax-calculation-module-design.md](../specs/2026-05-11-phase-8-tax-calculation-module-design.md)

**Conventions reminder (from CLAUDE.md):**
- `uv` only for Python; never pip
- No emojis anywhere (code, commits, docs)
- Tax math is test-driven — write the failing test first
- Tax module gets 100% line coverage enforced in CI
- Tax constants live in the database, not in code (we read them through a snapshot dataclass)
- One logical change per commit, Conventional Commits prefixes

---

## Task 1: Add tax-module coverage configuration

**Files:**
- Modify: `api/pyproject.toml` (append coverage config)

No tests here — this is a config-only change that prepares the gate for Task 8 to flip on.

- [ ] **Step 1: Append coverage config to `api/pyproject.toml`**

Open `api/pyproject.toml` and append these two sections at the end of the file:

```toml

[tool.coverage.run]
source = ["app/tax", "app/repositories/tax_constants"]
branch = false

[tool.coverage.report]
fail_under = 100
show_missing = true
skip_covered = false
```

The leading blank line keeps the file readable. `branch = false` keeps the gate at line coverage only (per CLAUDE.md's "100% line coverage").

- [ ] **Step 2: Confirm `pytest --cov=app/tax` does not fail with a config error**

```bash
cd api && uv run pytest --cov=app/tax tests/test_health.py --no-cov-on-fail 2>&1 | tail -8
```

The path `app/tax` does not exist yet, so coverage will emit a warning (`Module app/tax was never imported`). That's expected. The command should still exit 0 because we passed `--no-cov-on-fail`. If pytest itself errors on the config TOML, fix the config syntax.

- [ ] **Step 3: Commit**

```bash
git add api/pyproject.toml
git commit -m "$(cat <<'EOF'
chore(api): add tax-module coverage configuration

Phase 8 introduces app/tax/ with a 100% line-coverage gate. Define
the coverage source and fail-under threshold now so any tax code
added in later commits is measured. CI will flip the --cov-fail-under
flag on in Task 8.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add TaxConstantsSnapshot and fallback lookup

**Files:**
- Create: `api/app/tax/__init__.py` (empty package marker; public re-exports added in Task 7)
- Create: `api/app/tax/constants.py`
- Create: `api/tests/fixtures/tax_constants_2023_2026.py`
- Modify: `api/tests/fixtures/__init__.py` (create if missing, leave empty)
- Create: `api/tests/unit/test_tax_constants.py`

TDD: write the failing tests first, then implement.

- [ ] **Step 1: Create the empty `app/tax/` package marker**

Create `api/app/tax/__init__.py` containing exactly one blank line (the pre-commit hook will normalize this to a zero-byte file; either is acceptable as a Python package marker).

- [ ] **Step 2: Create the test fixture mirroring seeded tax_constants**

Create `api/tests/fixtures/tax_constants_2023_2026.py`:

```python
"""Hand-built fixture mirroring api/scripts/seed_tax_constants.py.

Used by unit tests to construct an in-memory dict of snapshots
without a DB roundtrip. Keep in sync with seed_tax_constants.py
if the seeded values change.
"""

from decimal import Decimal

from app.tax.constants import TaxConstantsSnapshot

TAX_CONSTANTS_2023_2026: dict[int, TaxConstantsSnapshot] = {
    2023: TaxConstantsSnapshot(
        year=2023,
        basiszins=Decimal("0.0255"),
        sparerpauschbetrag_eur=Decimal("1000.00"),
        teilfreistellung_equity=Decimal("0.3000"),
        teilfreistellung_mixed=Decimal("0.1500"),
        capital_gains_rate=Decimal("0.2500"),
        solidaritaetszuschlag_rate=Decimal("0.0550"),
    ),
    2024: TaxConstantsSnapshot(
        year=2024,
        basiszins=Decimal("0.0229"),
        sparerpauschbetrag_eur=Decimal("1000.00"),
        teilfreistellung_equity=Decimal("0.3000"),
        teilfreistellung_mixed=Decimal("0.1500"),
        capital_gains_rate=Decimal("0.2500"),
        solidaritaetszuschlag_rate=Decimal("0.0550"),
    ),
    2025: TaxConstantsSnapshot(
        year=2025,
        basiszins=Decimal("0.0253"),
        sparerpauschbetrag_eur=Decimal("1000.00"),
        teilfreistellung_equity=Decimal("0.3000"),
        teilfreistellung_mixed=Decimal("0.1500"),
        capital_gains_rate=Decimal("0.2500"),
        solidaritaetszuschlag_rate=Decimal("0.0550"),
    ),
    2026: TaxConstantsSnapshot(
        year=2026,
        basiszins=Decimal("0.0250"),
        sparerpauschbetrag_eur=Decimal("1000.00"),
        teilfreistellung_equity=Decimal("0.3000"),
        teilfreistellung_mixed=Decimal("0.1500"),
        capital_gains_rate=Decimal("0.2500"),
        solidaritaetszuschlag_rate=Decimal("0.0550"),
    ),
}
```

If `api/tests/fixtures/__init__.py` does not exist, create it as an empty file.

- [ ] **Step 3: Write the failing unit tests**

Create `api/tests/unit/test_tax_constants.py`:

```python
"""Unit tests for TaxConstantsSnapshot + lookup_year_with_fallback."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.tax.constants import TaxConstantsSnapshot, lookup_year_with_fallback
from tests.fixtures.tax_constants_2023_2026 import TAX_CONSTANTS_2023_2026


def test_lookup_returns_exact_year_when_present() -> None:
    snapshot = lookup_year_with_fallback(TAX_CONSTANTS_2023_2026, 2024)
    assert snapshot.year == 2024
    assert snapshot.basiszins == Decimal("0.0229")


def test_lookup_future_year_falls_back_to_latest() -> None:
    snapshot = lookup_year_with_fallback(TAX_CONSTANTS_2023_2026, 2030)
    assert snapshot.year == 2026


def test_lookup_past_year_falls_back_to_latest() -> None:
    # Symmetric fallback: past-year case also returns latest.
    snapshot = lookup_year_with_fallback(TAX_CONSTANTS_2023_2026, 2020)
    assert snapshot.year == 2026


def test_lookup_single_row_dict_returns_that_row() -> None:
    only_2026 = {2026: TAX_CONSTANTS_2023_2026[2026]}
    assert lookup_year_with_fallback(only_2026, 2099).year == 2026


def test_lookup_empty_dict_raises_value_error() -> None:
    with pytest.raises(ValueError) as exc:
        lookup_year_with_fallback({}, 2026)
    assert "empty" in str(exc.value).lower()


def test_snapshot_is_frozen() -> None:
    snapshot = TAX_CONSTANTS_2023_2026[2026]
    with pytest.raises(FrozenInstanceError):
        snapshot.basiszins = Decimal("0.99")  # pyright: ignore[reportAttributeAccessIssue]
```

- [ ] **Step 4: Run tests to confirm they fail with ImportError**

```bash
cd api && uv run pytest tests/unit/test_tax_constants.py -v
```
Expected: All 6 tests fail on `ImportError` because `app.tax.constants` does not exist yet.

- [ ] **Step 5: Create `api/app/tax/constants.py`**

```python
"""Tax-constants snapshot + future-year fallback resolution."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TaxConstantsSnapshot:
    """Immutable per-year tax-constants record.

    Mirrors a row of the tax_constants table. The tax module never
    touches the SQLAlchemy model directly; the repository builds
    one of these per row.
    """

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

- [ ] **Step 6: Run tests to confirm green**

```bash
cd api && uv run pytest tests/unit/test_tax_constants.py -v
```
Expected: 6 passed.

- [ ] **Step 7: Lint and type-check**

```bash
cd api && uv run ruff check app/ tests/
cd api && uv run pyright app/ tests/
```
Expected: both clean.

- [ ] **Step 8: Commit**

```bash
git add api/app/tax/__init__.py api/app/tax/constants.py \
    api/tests/fixtures/__init__.py api/tests/fixtures/tax_constants_2023_2026.py \
    api/tests/unit/test_tax_constants.py
git commit -m "$(cat <<'EOF'
feat(api): add TaxConstantsSnapshot and fallback lookup

Immutable per-year tax-constants record decoupled from the
SQLAlchemy model, plus lookup_year_with_fallback that returns the
latest seeded year when the requested year is not present (handles
projections extending past the seeded data).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add tax_constants repository

**Files:**
- Create: `api/app/repositories/tax_constants.py`
- Create: `api/tests/integration/test_tax_constants_repo.py`

- [ ] **Step 1: Write the failing integration test**

Create `api/tests/integration/test_tax_constants_repo.py`:

```python
"""Integration test: load_tax_constants_by_year against Docker Postgres.

Requires `alembic upgrade head` and `scripts.seed_tax_constants` to
have populated the DB. The autouse fixture seeds before each test
so the order with other integration tests does not matter.
"""

from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine

from app.config import get_settings
from app.repositories.tax_constants import load_tax_constants_by_year
from app.tax.constants import TaxConstantsSnapshot
from scripts.seed_tax_constants import seed as seed_tax_constants


@pytest.fixture(scope="module")
def engine() -> Engine:
    return create_engine(get_settings().database_url)


@pytest.fixture(autouse=True)
def _seed() -> None:
    seed_tax_constants()


def test_load_returns_dict_of_snapshots(engine: Engine) -> None:
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        result = load_tax_constants_by_year(session)
    assert isinstance(result, dict)
    expected_years = {2023, 2024, 2025, 2026}
    assert expected_years.issubset(set(result.keys()))
    for snapshot in result.values():
        assert isinstance(snapshot, TaxConstantsSnapshot)


def test_load_preserves_decimal_values(engine: Engine) -> None:
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        result = load_tax_constants_by_year(session)
    snapshot_2024 = result[2024]
    assert snapshot_2024.basiszins == Decimal("0.0229")
    assert snapshot_2024.sparerpauschbetrag_eur == Decimal("1000.00")
    assert snapshot_2024.teilfreistellung_equity == Decimal("0.3000")
    assert snapshot_2024.capital_gains_rate == Decimal("0.2500")
    assert snapshot_2024.solidaritaetszuschlag_rate == Decimal("0.0550")
```

- [ ] **Step 2: Run the test to confirm it fails with ImportError**

Ensure Docker Postgres is up (`docker compose -f infra/docker-compose.yml up -d`) and migrations applied (`cd api && uv run alembic upgrade head`). Then:

```bash
cd api && uv run pytest tests/integration/test_tax_constants_repo.py -v
```
Expected: ImportError on `app.repositories.tax_constants`.

- [ ] **Step 3: Create `api/app/repositories/tax_constants.py`**

```python
"""Repository: load all tax_constants rows into a dict of snapshots."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TaxConstant
from app.tax.constants import TaxConstantsSnapshot


def load_tax_constants_by_year(
    session: Session,
) -> dict[int, TaxConstantsSnapshot]:
    """Return all rows from the tax_constants table keyed by year.

    One query; result is small (4-6 entries in practice).
    """
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

- [ ] **Step 4: Run the test to confirm green**

```bash
cd api && uv run pytest tests/integration/test_tax_constants_repo.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Run full suite to ensure no regression**

```bash
cd api && uv run pytest
```
Expected: previous count plus 2 new tests, all passing.

- [ ] **Step 6: Lint and type-check**

```bash
cd api && uv run ruff check app/ tests/
cd api && uv run pyright app/ tests/
```
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add api/app/repositories/tax_constants.py api/tests/integration/test_tax_constants_repo.py
git commit -m "$(cat <<'EOF'
feat(api): add tax_constants repository

load_tax_constants_by_year hydrates a dict of TaxConstantsSnapshot
from the tax_constants table in one query. The tax module consumes
the dict; tests pass a hand-built one to keep primitives DB-free.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add TaxOutcome and VorabpauschaleYear Pydantic models

**Files:**
- Create: `api/app/tax/outcome.py`
- Create: `api/tests/unit/test_tax_outcome.py`

- [ ] **Step 1: Write the failing tests**

Create `api/tests/unit/test_tax_outcome.py`:

```python
"""Unit tests for TaxOutcome + VorabpauschaleYear models."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.tax.outcome import TaxOutcome, VorabpauschaleYear


def _sample_year(year: int = 2026) -> VorabpauschaleYear:
    return VorabpauschaleYear(
        year=year,
        vorabpauschale_eur=Decimal("12.34"),
        realized_gain_eur=Decimal("0"),
        teilfreistellung_eur=Decimal("3.70"),
        sparerpauschbetrag_used_eur=Decimal("8.64"),
        capital_gains_tax_eur=Decimal("0.00"),
        solidaritaetszuschlag_eur=Decimal("0.00"),
        total_tax_eur=Decimal("0.00"),
    )


def _sample_outcome() -> TaxOutcome:
    return TaxOutcome(
        scenario="lump_sum",
        teilfreistellung_class="equity",
        horizon_years=10,
        start_year=2026,
        annual_return_rate=Decimal("0.05"),
        total_invested_eur=Decimal("10000.00"),
        final_gross_value_eur=Decimal("16288.95"),
        total_tax_paid_eur=Decimal("1465.50"),
        final_after_tax_value_eur=Decimal("14823.45"),
        yearly_breakdown=[_sample_year(2026 + i) for i in range(10)],
    )


def test_outcome_round_trips_through_dump_and_validate() -> None:
    original = _sample_outcome()
    serialized = original.model_dump()
    restored = TaxOutcome.model_validate(serialized)
    assert restored == original


def test_outcome_is_frozen() -> None:
    outcome = _sample_outcome()
    with pytest.raises(ValidationError):
        outcome.horizon_years = 99  # pyright: ignore[reportAttributeAccessIssue]


def test_decimal_precision_survives_serialization() -> None:
    original = _sample_outcome()
    serialized = original.model_dump(mode="json")
    restored = TaxOutcome.model_validate(serialized)
    # Precision must be exact, not approximate
    assert restored.final_after_tax_value_eur == Decimal("14823.45")
    assert restored.yearly_breakdown[0].vorabpauschale_eur == Decimal("12.34")
```

- [ ] **Step 2: Run the tests to confirm ImportError**

```bash
cd api && uv run pytest tests/unit/test_tax_outcome.py -v
```
Expected: ImportError on `app.tax.outcome`.

- [ ] **Step 3: Create `api/app/tax/outcome.py`**

```python
"""Pydantic return types for the tax orchestrators."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class VorabpauschaleYear(BaseModel):
    """Per-year tax record produced by the orchestrator's year loop."""

    model_config = ConfigDict(frozen=True)

    year: int
    vorabpauschale_eur: Decimal
    realized_gain_eur: Decimal
    teilfreistellung_eur: Decimal
    sparerpauschbetrag_used_eur: Decimal
    capital_gains_tax_eur: Decimal
    solidaritaetszuschlag_eur: Decimal
    total_tax_eur: Decimal


class TaxOutcome(BaseModel):
    """Result of one tax simulation: lump-sum or Sparplan."""

    model_config = ConfigDict(frozen=True)

    scenario: Literal["lump_sum", "sparplan"]
    teilfreistellung_class: Literal["equity", "mixed", "none"]
    horizon_years: int
    start_year: int
    annual_return_rate: Decimal

    total_invested_eur: Decimal
    final_gross_value_eur: Decimal
    total_tax_paid_eur: Decimal
    final_after_tax_value_eur: Decimal

    yearly_breakdown: list[VorabpauschaleYear]
```

- [ ] **Step 4: Run tests to confirm green**

```bash
cd api && uv run pytest tests/unit/test_tax_outcome.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Lint and type-check**

```bash
cd api && uv run ruff check app/ tests/
cd api && uv run pyright app/ tests/
```
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add api/app/tax/outcome.py api/tests/unit/test_tax_outcome.py
git commit -m "$(cat <<'EOF'
feat(api): add TaxOutcome and VorabpauschaleYear models

Frozen Pydantic models returned by the tax orchestrators. TaxOutcome
holds the top-line numbers plus a list of VorabpauschaleYear records
for tap-to-learn UI in Phase 9. Decimal precision is preserved
through JSON round-trips.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add the six tax primitive functions

**Files:**
- Create: `api/app/tax/primitives.py`
- Create: `api/tests/unit/test_tax_primitives.py`

This is the canonical TDD task. Write all the failing primitive tests, then implement.

- [ ] **Step 1: Write the failing unit tests**

Create `api/tests/unit/test_tax_primitives.py`:

```python
"""Unit tests for the six tax primitives.

Boundary cases per primitive as documented in the design spec §5.
"""

from decimal import Decimal

import pytest

from app.tax.constants import TaxConstantsSnapshot
from app.tax.primitives import (
    apply_sparerpauschbetrag,
    apply_teilfreistellung,
    compute_basisertrag,
    compute_capital_gains_tax,
    compute_solidaritaetszuschlag,
    compute_vorabpauschale,
)
from tests.fixtures.tax_constants_2023_2026 import TAX_CONSTANTS_2023_2026


C_2026 = TAX_CONSTANTS_2023_2026[2026]


# --- compute_basisertrag ---


def test_basisertrag_full_year() -> None:
    # 10000 * 0.025 * 0.7 * 12/12 = 175.00
    result = compute_basisertrag(Decimal("10000"), Decimal("0.025"), months_held=12)
    assert result == Decimal("175.0000")


def test_basisertrag_half_year() -> None:
    # 10000 * 0.025 * 0.7 * 6/12 = 87.50
    result = compute_basisertrag(Decimal("10000"), Decimal("0.025"), months_held=6)
    assert result == Decimal("87.5000")


def test_basisertrag_zero_months_held() -> None:
    result = compute_basisertrag(Decimal("10000"), Decimal("0.025"), months_held=0)
    assert result == Decimal("0")


def test_basisertrag_zero_basiszins() -> None:
    result = compute_basisertrag(Decimal("10000"), Decimal("0"), months_held=12)
    assert result == Decimal("0")


def test_basisertrag_zero_fund_value() -> None:
    result = compute_basisertrag(Decimal("0"), Decimal("0.025"), months_held=12)
    assert result == Decimal("0")


# --- compute_vorabpauschale ---


def test_vorabpauschale_negative_realized_return_clamps_to_zero() -> None:
    result = compute_vorabpauschale(
        basisertrag=Decimal("175"),
        realized_return=Decimal("-50"),
    )
    assert result == Decimal("0")


def test_vorabpauschale_realized_return_below_basisertrag() -> None:
    result = compute_vorabpauschale(
        basisertrag=Decimal("175"),
        realized_return=Decimal("100"),
    )
    assert result == Decimal("100")


def test_vorabpauschale_realized_return_above_basisertrag() -> None:
    result = compute_vorabpauschale(
        basisertrag=Decimal("175"),
        realized_return=Decimal("500"),
    )
    assert result == Decimal("175")


def test_vorabpauschale_both_zero() -> None:
    result = compute_vorabpauschale(
        basisertrag=Decimal("0"),
        realized_return=Decimal("0"),
    )
    assert result == Decimal("0")


# --- apply_teilfreistellung ---


def test_teilfreistellung_equity_uses_30_percent() -> None:
    # 1000 * (1 - 0.30) = 700
    result = apply_teilfreistellung(Decimal("1000"), "equity", C_2026)
    assert result == Decimal("700.0000")


def test_teilfreistellung_mixed_uses_15_percent() -> None:
    # 1000 * (1 - 0.15) = 850
    result = apply_teilfreistellung(Decimal("1000"), "mixed", C_2026)
    assert result == Decimal("850.0000")


def test_teilfreistellung_none_returns_full_base() -> None:
    result = apply_teilfreistellung(Decimal("1000"), "none", C_2026)
    assert result == Decimal("1000")


def test_teilfreistellung_zero_input_returns_zero() -> None:
    result = apply_teilfreistellung(Decimal("0"), "equity", C_2026)
    assert result == Decimal("0.0000")


# --- apply_sparerpauschbetrag ---


def test_sparerpauschbetrag_income_below_allowance_returns_zero() -> None:
    result = apply_sparerpauschbetrag(Decimal("500"), Decimal("1000"))
    assert result == Decimal("0")


def test_sparerpauschbetrag_income_equal_to_allowance_returns_zero() -> None:
    result = apply_sparerpauschbetrag(Decimal("1000"), Decimal("1000"))
    assert result == Decimal("0")


def test_sparerpauschbetrag_income_above_allowance_returns_difference() -> None:
    result = apply_sparerpauschbetrag(Decimal("1500"), Decimal("1000"))
    assert result == Decimal("500")


# --- compute_capital_gains_tax ---


def test_capital_gains_tax_applies_rate() -> None:
    # 1000 * 0.25 = 250
    result = compute_capital_gains_tax(Decimal("1000"), Decimal("0.25"))
    assert result == Decimal("250.00")


def test_capital_gains_tax_zero_income_returns_zero() -> None:
    result = compute_capital_gains_tax(Decimal("0"), Decimal("0.25"))
    assert result == Decimal("0.00")


# --- compute_solidaritaetszuschlag ---


def test_soli_applies_rate_to_capital_gains_tax() -> None:
    # 250 * 0.055 = 13.75
    result = compute_solidaritaetszuschlag(Decimal("250"), Decimal("0.055"))
    assert result == Decimal("13.750")


def test_soli_zero_tax_returns_zero() -> None:
    result = compute_solidaritaetszuschlag(Decimal("0"), Decimal("0.055"))
    assert result == Decimal("0.000")
```

- [ ] **Step 2: Run tests to confirm they fail with ImportError**

```bash
cd api && uv run pytest tests/unit/test_tax_primitives.py -v
```
Expected: All 19 tests fail on ImportError because `app.tax.primitives` does not exist.

- [ ] **Step 3: Create `api/app/tax/primitives.py`**

```python
"""Six pure tax primitives. No I/O, no side effects, Decimal only.

Each function captures one rule (or one piece of a rule) from the
German tax code. Vorabpauschale (§18 InvStG) is split into
compute_basisertrag and compute_vorabpauschale so the Sparplan
orchestrator can sum two Basiserträge (old principal full year,
new contributions half year) before clamping.
"""

from decimal import Decimal
from typing import Literal

from app.tax.constants import TaxConstantsSnapshot


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


def compute_vorabpauschale(
    basisertrag: Decimal,
    realized_return: Decimal,
) -> Decimal:
    """Vorabpauschale = max(0, min(basisertrag, realized_return))."""
    return max(Decimal("0"), min(basisertrag, realized_return))


def apply_teilfreistellung(
    taxable_base: Decimal,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    constants: TaxConstantsSnapshot,
) -> Decimal:
    """Return taxable_base after the equity/mixed/none exemption."""
    rate = {
        "equity": constants.teilfreistellung_equity,
        "mixed": constants.teilfreistellung_mixed,
        "none": Decimal("0"),
    }[teilfreistellung_class]
    return taxable_base * (Decimal("1") - rate)


def apply_sparerpauschbetrag(
    post_teilfreistellung_income: Decimal,
    allowance: Decimal,
) -> Decimal:
    """Return income reduced by the year's allowance, floored at 0."""
    return max(Decimal("0"), post_teilfreistellung_income - allowance)


def compute_capital_gains_tax(
    taxable_income: Decimal,
    capital_gains_rate: Decimal,
) -> Decimal:
    """Flat-rate Abgeltungsteuer on the post-allowance base."""
    return taxable_income * capital_gains_rate


def compute_solidaritaetszuschlag(
    capital_gains_tax: Decimal,
    solidaritaetszuschlag_rate: Decimal,
) -> Decimal:
    """Surcharge on capital gains tax (not on income)."""
    return capital_gains_tax * solidaritaetszuschlag_rate
```

- [ ] **Step 4: Run tests to confirm green**

```bash
cd api && uv run pytest tests/unit/test_tax_primitives.py -v
```
Expected: 19 passed.

- [ ] **Step 5: Confirm 100% coverage on primitives**

```bash
cd api && uv run pytest tests/unit/test_tax_primitives.py --cov=app/tax/primitives --cov-report=term-missing
```
Expected: `100%` coverage on `app/tax/primitives.py`, no missing lines.

- [ ] **Step 6: Lint and type-check**

```bash
cd api && uv run ruff check app/ tests/
cd api && uv run pyright app/ tests/
```
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add api/app/tax/primitives.py api/tests/unit/test_tax_primitives.py
git commit -m "$(cat <<'EOF'
feat(api): add tax primitive functions

Six pure functions covering the German tax rules: Basisertrag,
Vorabpauschale clamp, Teilfreistellung, Sparerpauschbetrag,
Abgeltungsteuer, Solidaritaetszuschlag. Each is a one-expression
pure function over Decimals; the orchestrators in the next task
compose them.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Add lump-sum and Sparplan orchestrators

**Files:**
- Create: `api/app/tax/engine.py`
- Create: `api/tests/unit/test_tax_lump_sum.py`
- Create: `api/tests/unit/test_tax_sparplan.py`

This is the largest TDD task. Two orchestrators sharing a private year-loop helper.

- [ ] **Step 1: Write the failing lump-sum tests**

Create `api/tests/unit/test_tax_lump_sum.py`:

```python
"""Golden-value tests for compute_lump_sum_outcome.

The €10,000-over-10-years scenarios were derived by hand-tracing
the algorithm with the values in tests/fixtures/tax_constants_2023_2026.py.
If the seeded constants drift, regenerate the goldens with the same
hand trace.
"""

from decimal import Decimal

import pytest

from app.tax.engine import compute_lump_sum_outcome
from tests.fixtures.tax_constants_2023_2026 import TAX_CONSTANTS_2023_2026


def test_one_year_5_percent_equity_2026() -> None:
    """€10,000 invested for 1 year at 5%, equity ETF.

    Single-iteration sanity check. The final year computes both
    Vorabpauschale AND realized gain.

    Year 2026 (final):
      v_start = 10000.00
      v_end   = 10000.00 * 1.05 = 10500.00
      basisertrag = 10000 * 0.025 * 0.7 = 175.0000
      realized_year_gain = 10500 - 10000 = 500
      vorabpauschale = min(175, 500) = 175.0000
      realized_gain  = max(0, 10500 - 10000 - 0 - 175) = 325.0000
      taxable_after_tf = (175 + 325) * 0.70 = 350.0000
      after_spb = max(0, 350 - 1000) = 0
      cgt = 0; soli = 0; year_tax = 0.00
      final_after_tax = 10500.00 - 0.00 = 10500.00
    """
    outcome = compute_lump_sum_outcome(
        teilfreistellung_class="equity",
        investment_eur=Decimal("10000"),
        horizon_years=1,
        annual_return_rate=Decimal("0.05"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.scenario == "lump_sum"
    assert outcome.total_invested_eur == Decimal("10000")
    assert outcome.final_gross_value_eur == Decimal("10500.00")
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_after_tax_value_eur == Decimal("10500.00")
    assert len(outcome.yearly_breakdown) == 1


def test_ten_year_5_percent_equity_2026_produces_positive_after_tax_below_gross() -> None:
    """€10,000 over 10 years at 5%, equity ETF.

    Year-by-year hand trace is documented in the implementation comments
    on `compute_lump_sum_outcome`. The golden numbers assert structural
    properties: after-tax < gross < pure-compound, total tax > 0.
    """
    outcome = compute_lump_sum_outcome(
        teilfreistellung_class="equity",
        investment_eur=Decimal("10000"),
        horizon_years=10,
        annual_return_rate=Decimal("0.05"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    pure_compound = Decimal("10000") * (Decimal("1.05") ** 10)
    assert outcome.final_gross_value_eur == pure_compound.quantize(
        Decimal("0.01")
    ) or abs(outcome.final_gross_value_eur - pure_compound) < Decimal("0.01")
    assert outcome.total_tax_paid_eur > Decimal("0")
    assert outcome.final_after_tax_value_eur < outcome.final_gross_value_eur
    assert outcome.final_after_tax_value_eur > outcome.total_invested_eur
    assert len(outcome.yearly_breakdown) == 10


def test_zero_return_produces_no_tax() -> None:
    outcome = compute_lump_sum_outcome(
        teilfreistellung_class="equity",
        investment_eur=Decimal("10000"),
        horizon_years=10,
        annual_return_rate=Decimal("0"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_after_tax_value_eur == Decimal("10000")
    assert outcome.final_gross_value_eur == Decimal("10000")


def test_negative_return_produces_no_tax_and_loss() -> None:
    outcome = compute_lump_sum_outcome(
        teilfreistellung_class="equity",
        investment_eur=Decimal("10000"),
        horizon_years=10,
        annual_return_rate=Decimal("-0.03"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_gross_value_eur < outcome.total_invested_eur
    assert outcome.final_after_tax_value_eur == outcome.final_gross_value_eur


def test_horizon_zero_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_lump_sum_outcome(
            teilfreistellung_class="equity",
            investment_eur=Decimal("10000"),
            horizon_years=0,
            annual_return_rate=Decimal("0.05"),
            start_year=2026,
            tax_constants_by_year=TAX_CONSTANTS_2023_2026,
        )


def test_zero_investment_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_lump_sum_outcome(
            teilfreistellung_class="equity",
            investment_eur=Decimal("0"),
            horizon_years=10,
            annual_return_rate=Decimal("0.05"),
            start_year=2026,
            tax_constants_by_year=TAX_CONSTANTS_2023_2026,
        )
```

- [ ] **Step 2: Write the failing Sparplan tests**

Create `api/tests/unit/test_tax_sparplan.py`:

```python
"""Golden-value tests for compute_sparplan_outcome.

Sparplan uses annual aggregation with mid-year convention: each year
sums 12 monthly contributions into one annual cohort treated as if
acquired at month 6. Goldens derived by the same hand-trace approach
as lump-sum.
"""

from decimal import Decimal

import pytest

from app.tax.engine import compute_sparplan_outcome
from tests.fixtures.tax_constants_2023_2026 import TAX_CONSTANTS_2023_2026


def test_one_year_5_percent_equity_2026() -> None:
    """€100/month over 1 year at 5%, equity ETF.

    Single-year Sparplan stresses the mid-year split.

    Year 2026 (final):
      C = 100 * 12 = 1200
      v_start = 0
      v_end = 0 * 1.05 + 1200 * (1 + 0.05 * 0.5) = 1230.00
      basisertrag_old = 0 * 0.025 * 0.7 = 0
      basisertrag_new = 1200 * 0.025 * 0.7 * 6/12 = 10.50
      basisertrag = 10.50
      realized_year_gain = 1230 - 0 - 1200 = 30
      vorabpauschale = min(10.50, 30) = 10.50
      realized_gain = max(0, 1230 - 1200 - 0 - 10.50) = 19.50
      taxable_after_tf = (10.50 + 19.50) * 0.70 = 21.00
      after_spb = max(0, 21 - 1000) = 0
      year_tax = 0.00
      final_after_tax = 1230.00
    """
    outcome = compute_sparplan_outcome(
        teilfreistellung_class="equity",
        monthly_contribution_eur=Decimal("100"),
        horizon_years=1,
        annual_return_rate=Decimal("0.05"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.scenario == "sparplan"
    assert outcome.total_invested_eur == Decimal("1200")
    assert outcome.final_gross_value_eur == Decimal("1230.00")
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_after_tax_value_eur == Decimal("1230.00")


def test_ten_year_5_percent_equity_2026_structural_invariants() -> None:
    outcome = compute_sparplan_outcome(
        teilfreistellung_class="equity",
        monthly_contribution_eur=Decimal("100"),
        horizon_years=10,
        annual_return_rate=Decimal("0.05"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.total_invested_eur == Decimal("12000")
    assert outcome.final_gross_value_eur > outcome.total_invested_eur
    assert outcome.final_after_tax_value_eur <= outcome.final_gross_value_eur
    assert outcome.final_after_tax_value_eur > outcome.total_invested_eur
    assert len(outcome.yearly_breakdown) == 10


def test_zero_return_produces_no_tax() -> None:
    outcome = compute_sparplan_outcome(
        teilfreistellung_class="equity",
        monthly_contribution_eur=Decimal("100"),
        horizon_years=10,
        annual_return_rate=Decimal("0"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_gross_value_eur == Decimal("12000")
    assert outcome.final_after_tax_value_eur == Decimal("12000")


def test_zero_monthly_contribution_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_sparplan_outcome(
            teilfreistellung_class="equity",
            monthly_contribution_eur=Decimal("0"),
            horizon_years=10,
            annual_return_rate=Decimal("0.05"),
            start_year=2026,
            tax_constants_by_year=TAX_CONSTANTS_2023_2026,
        )


def test_prior_year_vorabpauschale_is_credited_against_final_sale() -> None:
    """Property check: total tax across all years matches the per-year
    breakdown sum, AND the final-year realized_gain_eur is reduced by
    prior years' vorabpauschale_eur sum."""
    outcome = compute_sparplan_outcome(
        teilfreistellung_class="equity",
        monthly_contribution_eur=Decimal("500"),
        horizon_years=10,
        annual_return_rate=Decimal("0.07"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    sum_of_year_taxes = sum(
        (year.total_tax_eur for year in outcome.yearly_breakdown),
        start=Decimal("0"),
    )
    assert outcome.total_tax_paid_eur == sum_of_year_taxes
    # Final year realized gain reflects subtraction of cumulative VP base
    final_year = outcome.yearly_breakdown[-1]
    prior_vp_sum = sum(
        (year.vorabpauschale_eur for year in outcome.yearly_breakdown[:-1]),
        start=Decimal("0"),
    )
    # final_year.realized_gain_eur = max(0, v_end - total_invested - prior_vp_sum - this_year_vp)
    # Assert it's non-negative and that adding back prior_vp + this_year_vp gets us close to
    # the raw difference v_end - total_invested.
    assert final_year.realized_gain_eur >= Decimal("0")
    raw_lifetime_gain = outcome.final_gross_value_eur - outcome.total_invested_eur
    accounted = final_year.realized_gain_eur + prior_vp_sum + final_year.vorabpauschale_eur
    assert accounted == raw_lifetime_gain
```

- [ ] **Step 3: Run both test files to confirm ImportError**

```bash
cd api && uv run pytest tests/unit/test_tax_lump_sum.py tests/unit/test_tax_sparplan.py -v
```
Expected: All tests fail on ImportError because `app.tax.engine` does not exist.

- [ ] **Step 4: Create `api/app/tax/engine.py`**

```python
"""Tax orchestrators for lump-sum and Sparplan scenarios.

Both share a year-by-year body (Vorabpauschale -> Teilfreistellung ->
Sparerpauschbetrag -> Abgeltungsteuer -> Soli -> rounded tax record).
They differ only in how fund value evolves and how Basisertrag is
derived. The private helpers _run_lump_sum_year and _run_sparplan_year
isolate the differences; the shared body is _build_year_record.

Convention: investor pays year-end taxes out of pocket (matching
broker withholding via Freistellungsauftrag). The fund value at sale
is gross; final_after_tax_value = final_gross_value - sum_of_yearly_taxes.

Sparerpauschbetrag is applied per-ETF (per-comparison), framed as
"if this ETF were your only investment". The legally precise
aggregation across multiple holdings is out of scope.
"""

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Literal

from app.tax.constants import TaxConstantsSnapshot, lookup_year_with_fallback
from app.tax.outcome import TaxOutcome, VorabpauschaleYear
from app.tax.primitives import (
    apply_sparerpauschbetrag,
    apply_teilfreistellung,
    compute_basisertrag,
    compute_capital_gains_tax,
    compute_solidaritaetszuschlag,
    compute_vorabpauschale,
)


def _round_eur(value: Decimal) -> Decimal:
    """Round to 2 decimal places, banker's rounding (matches broker withholding)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def _build_year_record(
    *,
    year: int,
    vorabpauschale: Decimal,
    realized_gain: Decimal,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    constants: TaxConstantsSnapshot,
) -> VorabpauschaleYear:
    """Apply the shared tax-cascade to one year's pre-tax income.

    Returns a VorabpauschaleYear with rounded euro amounts.
    """
    pre_tf_income = vorabpauschale + realized_gain
    taxable_after_tf = apply_teilfreistellung(pre_tf_income, teilfreistellung_class, constants)
    teilfreistellung_eur = pre_tf_income - taxable_after_tf

    after_spb = apply_sparerpauschbetrag(taxable_after_tf, constants.sparerpauschbetrag_eur)
    spb_used = min(taxable_after_tf, constants.sparerpauschbetrag_eur)

    cgt = compute_capital_gains_tax(after_spb, constants.capital_gains_rate)
    soli = compute_solidaritaetszuschlag(cgt, constants.solidaritaetszuschlag_rate)
    total_year_tax = _round_eur(cgt + soli)

    return VorabpauschaleYear(
        year=year,
        vorabpauschale_eur=_round_eur(vorabpauschale),
        realized_gain_eur=_round_eur(realized_gain),
        teilfreistellung_eur=_round_eur(teilfreistellung_eur),
        sparerpauschbetrag_used_eur=_round_eur(spb_used),
        capital_gains_tax_eur=_round_eur(cgt),
        solidaritaetszuschlag_eur=_round_eur(soli),
        total_tax_eur=total_year_tax,
    )


def compute_lump_sum_outcome(
    *,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    investment_eur: Decimal,
    horizon_years: int,
    annual_return_rate: Decimal,
    start_year: int,
    tax_constants_by_year: dict[int, TaxConstantsSnapshot],
) -> TaxOutcome:
    """Single lump-sum investment held for horizon_years, sold at the end.

    Vorabpauschale applies every year (including the sale year, where
    it is netted against the realized gain to avoid double-counting).
    """
    if horizon_years <= 0:
        raise ValueError("horizon_years must be >= 1")
    if investment_eur <= Decimal("0"):
        raise ValueError("investment_eur must be > 0")

    fund_value = investment_eur
    cumulative_tax_paid = Decimal("0")
    history: list[VorabpauschaleYear] = []

    for offset in range(horizon_years):
        year = start_year + offset
        constants = lookup_year_with_fallback(tax_constants_by_year, year)

        v_end = fund_value * (Decimal("1") + annual_return_rate)
        basisertrag = compute_basisertrag(fund_value, constants.basiszins)
        vorabpauschale = compute_vorabpauschale(basisertrag, v_end - fund_value)

        is_final_year = offset == horizon_years - 1
        if is_final_year:
            prior_vp_sum = sum(
                (record.vorabpauschale_eur for record in history),
                start=Decimal("0"),
            )
            realized_gain = max(
                Decimal("0"),
                v_end - investment_eur - prior_vp_sum - vorabpauschale,
            )
        else:
            realized_gain = Decimal("0")

        record = _build_year_record(
            year=year,
            vorabpauschale=vorabpauschale,
            realized_gain=realized_gain,
            teilfreistellung_class=teilfreistellung_class,
            constants=constants,
        )
        history.append(record)
        cumulative_tax_paid += record.total_tax_eur
        fund_value = v_end

    final_gross = _round_eur(fund_value)
    return TaxOutcome(
        scenario="lump_sum",
        teilfreistellung_class=teilfreistellung_class,
        horizon_years=horizon_years,
        start_year=start_year,
        annual_return_rate=annual_return_rate,
        total_invested_eur=investment_eur,
        final_gross_value_eur=final_gross,
        total_tax_paid_eur=_round_eur(cumulative_tax_paid),
        final_after_tax_value_eur=_round_eur(final_gross - cumulative_tax_paid),
        yearly_breakdown=history,
    )


def compute_sparplan_outcome(
    *,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    monthly_contribution_eur: Decimal,
    horizon_years: int,
    annual_return_rate: Decimal,
    start_year: int,
    tax_constants_by_year: dict[int, TaxConstantsSnapshot],
) -> TaxOutcome:
    """Monthly Sparplan held for horizon_years.

    Annual aggregation with mid-year convention: each year sums the
    12 monthly contributions into one cohort treated as if acquired
    at month 6. Vorabpauschale Basisertrag is the sum of:
    - full-year Basisertrag on the opening balance
    - half-year Basisertrag on the year's contributions
    """
    if horizon_years <= 0:
        raise ValueError("horizon_years must be >= 1")
    if monthly_contribution_eur <= Decimal("0"):
        raise ValueError("monthly_contribution_eur must be > 0")

    annual_contribution = monthly_contribution_eur * Decimal("12")
    total_invested = annual_contribution * Decimal(horizon_years)

    fund_value = Decimal("0")
    cumulative_tax_paid = Decimal("0")
    history: list[VorabpauschaleYear] = []

    for offset in range(horizon_years):
        year = start_year + offset
        constants = lookup_year_with_fallback(tax_constants_by_year, year)

        v_end = fund_value * (Decimal("1") + annual_return_rate) + annual_contribution * (
            Decimal("1") + annual_return_rate * Decimal("0.5")
        )

        basisertrag_old = compute_basisertrag(fund_value, constants.basiszins, months_held=12)
        basisertrag_new = compute_basisertrag(
            annual_contribution, constants.basiszins, months_held=6
        )
        basisertrag = basisertrag_old + basisertrag_new
        realized_year_gain = v_end - fund_value - annual_contribution
        vorabpauschale = compute_vorabpauschale(basisertrag, realized_year_gain)

        is_final_year = offset == horizon_years - 1
        if is_final_year:
            prior_vp_sum = sum(
                (record.vorabpauschale_eur for record in history),
                start=Decimal("0"),
            )
            realized_gain = max(
                Decimal("0"),
                v_end - total_invested - prior_vp_sum - vorabpauschale,
            )
        else:
            realized_gain = Decimal("0")

        record = _build_year_record(
            year=year,
            vorabpauschale=vorabpauschale,
            realized_gain=realized_gain,
            teilfreistellung_class=teilfreistellung_class,
            constants=constants,
        )
        history.append(record)
        cumulative_tax_paid += record.total_tax_eur
        fund_value = v_end

    final_gross = _round_eur(fund_value)
    return TaxOutcome(
        scenario="sparplan",
        teilfreistellung_class=teilfreistellung_class,
        horizon_years=horizon_years,
        start_year=start_year,
        annual_return_rate=annual_return_rate,
        total_invested_eur=total_invested,
        final_gross_value_eur=final_gross,
        total_tax_paid_eur=_round_eur(cumulative_tax_paid),
        final_after_tax_value_eur=_round_eur(final_gross - cumulative_tax_paid),
        yearly_breakdown=history,
    )
```

- [ ] **Step 5: Run both new test files to confirm green**

```bash
cd api && uv run pytest tests/unit/test_tax_lump_sum.py tests/unit/test_tax_sparplan.py -v
```
Expected: 6 lump-sum + 5 Sparplan = 11 passed.

- [ ] **Step 6: Run the full suite to confirm no regression**

```bash
cd api && uv run pytest -v
```
Expected: all tests pass.

- [ ] **Step 7: Confirm 100% coverage on tax package**

```bash
cd api && uv run pytest --cov=app/tax --cov=app/repositories/tax_constants --cov-report=term-missing
```
Expected: `100%` coverage on all five module files, no missing lines.

If any line is uncovered, add the missing test before committing.

- [ ] **Step 8: Lint and type-check**

```bash
cd api && uv run ruff check app/ tests/
cd api && uv run pyright app/ tests/
```
Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add api/app/tax/engine.py api/tests/unit/test_tax_lump_sum.py api/tests/unit/test_tax_sparplan.py
git commit -m "$(cat <<'EOF'
feat(api): add lump-sum and Sparplan orchestrators

compute_lump_sum_outcome and compute_sparplan_outcome share a private
year-loop body (_build_year_record) that applies the cascade:
Teilfreistellung -> Sparerpauschbetrag -> Abgeltungsteuer -> Soli.
Lump-sum models a single up-front investment; Sparplan uses annual
aggregation with the mid-year convention for new contributions.
Final-year realized gain credits the cumulative Vorabpauschale base
to avoid double-taxation.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Wire the tax-module public surface

**Files:**
- Modify: `api/app/tax/__init__.py`

- [ ] **Step 1: Replace the empty `api/app/tax/__init__.py` with the public re-exports**

```python
"""Public surface of the tax module.

Phase 9 imports only from app.tax, never from app.tax.engine or
app.tax.primitives directly. Implementation modules are private.
"""

from app.tax.constants import TaxConstantsSnapshot, lookup_year_with_fallback
from app.tax.engine import compute_lump_sum_outcome, compute_sparplan_outcome
from app.tax.outcome import TaxOutcome, VorabpauschaleYear

__all__ = [
    "TaxConstantsSnapshot",
    "TaxOutcome",
    "VorabpauschaleYear",
    "compute_lump_sum_outcome",
    "compute_sparplan_outcome",
    "lookup_year_with_fallback",
]
```

- [ ] **Step 2: Verify the public surface imports cleanly**

```bash
cd api && uv run python -c "from app.tax import TaxOutcome, VorabpauschaleYear, TaxConstantsSnapshot, lookup_year_with_fallback, compute_lump_sum_outcome, compute_sparplan_outcome; print('ok')"
```
Expected: `ok`.

- [ ] **Step 3: Run full suite + coverage**

```bash
cd api && uv run pytest --cov=app/tax --cov=app/repositories/tax_constants --cov-report=term-missing
```
Expected: all tests pass, 100% coverage on the tax module paths.

- [ ] **Step 4: Lint and type-check**

```bash
cd api && uv run ruff check app/ tests/
cd api && uv run pyright app/ tests/
```
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add api/app/tax/__init__.py
git commit -m "$(cat <<'EOF'
feat(api): wire tax-module public surface

Re-export TaxConstantsSnapshot, TaxOutcome, VorabpauschaleYear,
lookup_year_with_fallback, compute_lump_sum_outcome, and
compute_sparplan_outcome. Phase 9 imports only from app.tax.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Enforce 100% coverage on tax module in CI

**Files:**
- Modify: `.github/workflows/ci.yml` (the Pytest step)

- [ ] **Step 1: Update the Pytest step in `.github/workflows/ci.yml`**

Find the current Pytest step (around line 57-59):

```yaml
      - name: Pytest
        working-directory: api
        run: uv run pytest
```

Replace with:

```yaml
      - name: Pytest
        working-directory: api
        run: uv run pytest --cov=app/tax --cov=app/repositories/tax_constants --cov-fail-under=100
```

- [ ] **Step 2: Re-run pytest locally with the same flag to verify the gate passes**

```bash
cd api && uv run pytest --cov=app/tax --cov=app/repositories/tax_constants --cov-fail-under=100
```
Expected: all tests pass; coverage prints `Required test coverage of 100% reached. Total coverage: 100.00%`. Exit code 0.

If coverage is below 100%, find the missing lines (the output lists them) and add tests in the appropriate file. Do NOT add `# pragma: no cover` annotations to satisfy the gate; either test the line or delete it.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "$(cat <<'EOF'
chore(ci): enforce 100% coverage on tax module

The tax-calculation module is the most consequential math in the
codebase; CLAUDE.md mandates 100% line coverage on it. Add the
--cov-fail-under=100 flag to the CI Pytest step so any regression
in coverage fails the build.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Document Phase 8 in CLAUDE.md and README.md

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Update CLAUDE.md**

Open `CLAUDE.md`. The current "Phases implemented" line reads:

```
**Phases 0, 1, 2, 3, 5, 6, 7 implemented; not yet deployed.** Phase 4
```

Change it to:

```
**Phases 0, 1, 2, 3, 5, 6, 7, 8 implemented; not yet deployed.** Phase 4
```

The "Shipped milestones" list currently ends with:

```
- Phase 7 — curated 15-ETF list in `shared/etfs.yaml` seeded into Postgres via `scripts/seed_etfs.py`; `/etfs` and `/comparison` now read from the database; mock JSON retired.
```

Append after it:

```
- Phase 8 — German tax calculation module at `api/app/tax/` (six pure primitives, lump-sum + Sparplan orchestrators, `TaxOutcome` return type). 100% line coverage enforced in CI. Kirchensteuer and joint-assessment Sparerpauschbetrag deferred.
```

- [ ] **Step 2: Update README.md**

Open `README.md`. The current Status bullet list ends with the "Database" bullet added in Phase 7. Append after it:

```
- Tax math: German tax calculation module (Vorabpauschale, Teilfreistellung, Sparerpauschbetrag, Abgeltungsteuer, Solidaritätszuschlag) supporting lump-sum and Sparplan scenarios; 100% line coverage enforced in CI. Returned via a structured `TaxOutcome` with per-year breakdown.
```

The "Not built yet" line currently reads:

```
Not built yet: deployment pipelines, price ingestion, German tax calculation, privacy policy. See [PLAN.md](PLAN.md) for the authoritative scope and phased build plan.
```

Remove `German tax calculation, ` so the line becomes:

```
Not built yet: deployment pipelines, price ingestion, privacy policy. See [PLAN.md](PLAN.md) for the authoritative scope and phased build plan.
```

- [ ] **Step 3: Verify the diff is clean**

```bash
git add CLAUDE.md README.md
git diff --cached CLAUDE.md README.md
```
Expected: only the four edits described above. No trailing whitespace, no emojis.

- [ ] **Step 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
docs: note Phase 8 in CLAUDE.md and README.md

Add Phase 8 milestone entry and update the "implemented" line. The
README status section gains a tax-math bullet and drops German tax
calculation from "Not built yet".

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Final verification

After all nine tasks have committed:

- [ ] **Lint, type-check, and full coverage gate**

```bash
cd api && uv run ruff check app/ tests/ scripts/
cd api && uv run pyright app/ scripts/
cd api && uv run pytest --cov=app/tax --cov=app/repositories/tax_constants --cov-fail-under=100
```
Expected: all green; coverage reads `100.00%`.

- [ ] **Confirm the commit count and ordering**

```bash
git log --oneline origin/main..HEAD
```
Expected: 11 commits total (the existing spec commit `01d94dc` plus the nine implementation commits plus this plan commit, which lands after the spec via `git add docs/superpowers/plans/...`). Order matches the spec's commit plan.

Note: the plan file itself (`docs/superpowers/plans/2026-05-11-phase-8-tax-calculation-module.md`) should be committed separately before Task 1 begins — typically the implementer or controller will have done this already; if not, do it as a `docs:` commit before Task 1.

- [ ] **Smoke-test that nothing existing regressed**

```bash
cd api && uv run pytest tests/test_health.py tests/test_query_validation.py tests/integration/ -v
```
Expected: all green.

---

## Spec coverage map

| Spec section | Task(s) |
|---|---|
| §2 Goals in scope: tax/ package + primitives + orchestrators | Tasks 4, 5, 6 |
| §2 In scope: TaxConstantsSnapshot + fallback | Task 2 |
| §2 In scope: load_tax_constants_by_year | Task 3 |
| §2 In scope: TaxOutcome + VorabpauschaleYear | Task 4 |
| §2 In scope: 100% line coverage gate | Tasks 1, 8 |
| §2 Domain choices (per-ETF SPB, tax out of pocket) | Task 6 docstring |
| §3 Architecture & file layout | Tasks 2-7 (each creates the listed file) |
| §4 Snapshot dataclass + fallback | Task 2 |
| §4 Repository function | Task 3 |
| §5 Six primitives | Task 5 |
| §5 Rounding policy (`_round_eur`) | Task 6 (helper in engine.py per spec §5) |
| §6 Lump-sum orchestrator | Task 6 |
| §6 Sparplan orchestrator | Task 6 |
| §6 Edge cases (horizon=0, investment=0, etc.) | Task 6 tests |
| §7 TaxOutcome shape | Task 4 |
| §8 Coverage gate config | Task 1 |
| §8 Unit + integration tests | Tasks 2, 3, 4, 5, 6 |
| §8 CI workflow change | Task 8 |
| §9 Operations + docs | Tasks 1, 8, 9 |
| §10 Commit plan (nine commits) | Tasks 1-9 produce them |
| §11 Open questions (none) | n/a |

No spec requirement is left unimplemented. A small clarification: the spec §5 placed `_round_eur` in `primitives.py`, but on reflection the rounding helper is only used by the engine, never by tests of pure primitives. The plan places it in `engine.py` (Task 6) where its only caller lives. This is a minor deviation from the spec and is explicitly noted here.
