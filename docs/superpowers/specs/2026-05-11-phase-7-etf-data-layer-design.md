# Phase 7 — ETF data layer: curated list, DB seed, DB-backed endpoints

Date: 2026-05-11
Status: Approved (design)
Author: Paul Stanley with Claude Code

## §1. Context

Phase 6 shipped a working static prototype: `GET /etfs` and
`GET /comparison` are served by `api/app/api/comparison.py` reading
three mock ETFs from `shared/mock_etfs.json` plus a hardcoded
after-tax map. The web `compare/page.tsx` consumes that contract
through `web/src/lib/api.ts`.

Phase 5 already laid the database groundwork: the `etfs` table exists
(see `api/app/models/etf.py`), Alembic is wired, and `make seed`
populates `tax_constants` via `api/scripts/seed_tax_constants.py`.
The pattern for an idempotent, upsert-driven seed script is therefore
already established and Phase 7 follows it.

PLAN.md §1 names approximately 15 popular Sparplan ETFs as the
phase-one universe; Phase 7 is the moment that list moves from prose
to a curated, machine-readable artifact.

The downstream `comparison.py` docstring explicitly defers two pieces:
"Phase 8 tax module" and "Phase 9 replaces the hardcoded numbers with
real DB lookups and the Phase 8 tax module." Phase 7 lives squarely
in front of that: real ETF metadata in Postgres, served by the
existing endpoints, with the after-tax map left untouched for Phase 9.

## §2. Goals and non-goals

In scope:

- Curate the full 15-ETF list as `shared/etfs.yaml` (source of truth),
  with inline YAML comments noting KID source URL and last-verified
  date for each row.
- Pydantic-validated seed loader at `api/scripts/seed_etfs.py`,
  idempotent via `INSERT ... ON CONFLICT (isin) DO UPDATE` on Postgres.
- Extend `make seed` to run both `seed_tax_constants` and `seed_etfs`.
- Rewire `GET /etfs` and `GET /comparison` to read the `etfs` table
  instead of `shared/mock_etfs.json`.
- Delete `shared/mock_etfs.json` once nothing references it.
- Unit and integration tests covering the loader and both endpoints.

Out of scope (deferred):

- KID/factsheet/PDF parsing. Curation is manual: copy values from the
  KID into the YAML and paste the source URL into a comment above the
  row.
- Price ingestion. The `prices` table stays empty in Phase 7;
  `_HARDCODED_AFTER_TAX_EUR` in `comparison.py` stays put with a
  single comment line referencing Phase 9.
- Any `etfs` table schema change (no `source_url` or `verified_on`
  columns; verification info lives in YAML comments and git history).
- Front-end changes. `web/` is untouched; the API contract from
  Phase 6 is preserved exactly.
- Admin endpoints, search, filter, pagination, or a per-ISIN detail
  route. A 15-row list does not need any of that.
- Deployment to Supabase or Railway. Phase 4 is still deferred per
  CLAUDE.md; Phase 7 ships locally only.

Risk callout: the `aum_eur` field drifts daily. The YAML records a
snapshot, not a live figure. `last_ingested_at` captures when the
loader last touched the row so future phases can be honest about
staleness.

## §3. Architecture

```
shared/
  etfs.yaml                       (new) — curated 15-ETF source of truth
  mock_etfs.json                  (deleted)

api/
  pyproject.toml                  (modified) — add pyyaml, types-pyyaml
  scripts/
    seed_etfs.py                  (new) — Pydantic loader + upsert
  app/
    db.py                         (modified) — add cached engine + get_session
    api/
      comparison.py               (modified) — DB reads replace JSON reads
    repositories/                 (new package)
      __init__.py
      etfs.py                     (new) — list_etfs, get_etf
  tests/
    fixtures/
      etfs_seed_sample.yaml       (new) — 3-row valid YAML for loader tests
    unit/
      test_seed_etfs.py           (new) — Pydantic validation, duplicate check
    integration/
      test_seed_etfs_db.py        (new) — upsert and re-upsert against Docker PG
      test_etfs_endpoints.py      (new) — /etfs and /comparison after seeding

Makefile                          (modified) — make seed runs both seeders
CLAUDE.md                         (modified) — append Phase 7 milestone
README.md                         (modified) — append Phase 7 to status if present
```

Layering rationale: the new thin `app/repositories/etfs.py` keeps SQL
out of the FastAPI handler. The handler converts ORM rows to
`EtfResponse` (the Pydantic response model that already exists in
`comparison.py`). This avoids growing `comparison.py` into a fat
module and leaves a clean home for `repositories/prices.py` in
Phase 9. We split now, while there is exactly one repository to
create, rather than during Phase 9.

`pyyaml` is preferred over `ruamel.yaml`: we read once and write
nothing, so comment-preservation is irrelevant.

## §4. Data shape

YAML row schema (`shared/etfs.yaml`):

```yaml
- isin: IE00B4L5Y983
  name: iShares Core MSCI World UCITS ETF
  issuer: iShares (BlackRock)
  ter: 0.0020
  replication_method: physical          # physical | physical_sampling | synthetic
  distribution_policy: accumulating     # accumulating | distributing
  domicile: IE                          # ISO 3166-1 alpha-2
  aum_eur: 85000000000                  # snapshot, not live
  inception_date: 2009-09-25
  index_tracked: MSCI World
  teilfreistellung_class: equity        # equity | mixed | none
  # KID verified 2026-05-08
  # https://www.ishares.com/.../kid-en.pdf
```

The two trailing comments are not parsed; they are curation hygiene
that lives in git history.

Pydantic loader model (`api/scripts/seed_etfs.py`):

```python
class EtfSeedRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    isin: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]
    name: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    issuer: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    ter: Annotated[Decimal, Field(ge=0, le=Decimal("0.05"))]
    replication_method: Literal["physical", "physical_sampling", "synthetic"]
    distribution_policy: Literal["accumulating", "distributing"]
    domicile: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
    aum_eur: Annotated[Decimal, Field(ge=0)]
    inception_date: date
    index_tracked: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    teilfreistellung_class: Literal["equity", "mixed", "none"]
```

Notes:

- `extra="forbid"` is deliberate. A YAML typo (e.g. `tre: 0.002`)
  becomes a loud loader error instead of silently dropping a field.
- TER upper bound 5% is a sanity check, not a regulatory cap; it
  catches `0.20` entered when `0.0020` was meant.
- ISIN regex matches the format only, not the check digit. We prefer
  discovering a wrong ISIN by failing to load a KID over rejecting a
  valid one due to a misimplemented check digit.
- The Pydantic model mirrors the SQLAlchemy `Etf` model field by
  field; the only column it does not write is `last_ingested_at`,
  which the loader sets on each upsert.
- The three mock ISINs (`IE00B4L5Y983`, `IE00BK5BQT80`,
  `IE00BKM4GZ66`) carry over into the new YAML, so manual testing
  keeps working through the transition.

DB upsert columns: on conflict on `isin`, the loader updates every
business field plus `last_ingested_at = NOW()` and
`updated_at = NOW()`. `created_at` is untouched on updates. Same
pattern as `seed_tax_constants`, adapted to the wider column set.

## §5. Loader behavior

Entry point: `uv run python -m scripts.seed_etfs`. Exit code 0 on
success, non-zero on any validation or DB error.

Sequence:

1. Resolve `shared/etfs.yaml` relative to the repo root via
   `Path(__file__).resolve().parents[2] / "shared" / "etfs.yaml"`,
   matching how `comparison.py` already resolves `shared/mock_etfs.json`.
2. Open with `encoding="utf-8"` and parse with `yaml.safe_load`.
   Never `yaml.load` (arbitrary object construction risk).
3. Validate the parsed list against `list[EtfSeedRow]` via
   `TypeAdapter(list[EtfSeedRow]).validate_python(raw)`. Pydantic
   surfaces every bad row at once.
4. Enforce ISIN uniqueness inside the YAML before hitting the DB. If
   two rows share an ISIN, raise `ValueError` naming the duplicated
   ISIN. Catching this in-process is cheaper than letting the
   on-conflict update silently merge them.
5. Open a `Session`, run a single
   `insert(Etf).values([...]).on_conflict_do_update(index_elements=["isin"], set_={...})`,
   commit, and print `Seeded {n} etfs rows.` Matches the
   tax-constants seed's voice.

Idempotency: re-running the loader with no YAML changes is a no-op
for business fields, but `last_ingested_at` and `updated_at` always
advance to `NOW()`. That is intentional; `last_ingested_at` doubles
as "when did we last touch this row from the seed".

On-conflict columns: every business field plus `last_ingested_at`
and `updated_at` updated; `created_at` untouched. The full update
set is enumerated explicitly so an accidental future field addition
does not silently get overwritten without thought.

Failure modes:

| Failure | Behavior |
|---|---|
| YAML syntax error | `yaml.YAMLError` propagates with file line. No DB writes. |
| Pydantic validation fails on any row | `ValidationError` raised, listing every bad field; loader exits non-zero. No DB writes. |
| Duplicate ISIN inside YAML | Explicit `ValueError` naming the duplicated ISIN. No DB writes. |
| DB unreachable | SQLAlchemy `OperationalError` propagates. No partial commit. |
| Some rows already exist | Fine; that is what on-conflict is for. |

What the loader does not do:

- It does not delete rows that have been removed from the YAML. If
  the curated list ever drops an ETF, the DB row lingers; that is a
  documented limitation. Deletions are a deliberate curation
  decision and should not be silent side effects of editing a file.
- It does not log a diff of what changed. The `updated_at` column is
  the audit trail we have; richer auditing is YAGNI.

## §6. API rewiring

Repository layer (`api/app/repositories/etfs.py`):

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Etf

def list_etfs(session: Session) -> list[Etf]:
    return list(session.execute(select(Etf).order_by(Etf.name)).scalars())

def get_etf(session: Session, isin: str) -> Etf | None:
    return session.get(Etf, isin)
```

Ordered by `name` so the front-end dropdown is stable and predictable
across reloads.

FastAPI dependency added to `api/app/db.py`:

```python
def get_session() -> Iterator[Session]:
    engine = _get_engine()
    with Session(engine) as session:
        yield session
```

The engine is built once per process via a module-level
`lru_cache`-decorated helper using `get_settings().database_url`.
This matches what `seed_tax_constants` does ad-hoc; centralizing
it now lets future seed scripts share the helper instead of
building their own engines.

Handler rewrite (`api/app/api/comparison.py`):

- `_load_mock_etfs`, `_MOCK_PATH`, and the JSON-file path constant
  are deleted.
- `EtfResponse`, `AfterTaxOutcome`, `ComparisonResponse` move
  unchanged; the front-end contract is preserved bit-for-bit.
- `_HARDCODED_AFTER_TAX_EUR` and the `_DEFAULT_*` constants stay,
  with a single comment line: `# Phase 9 replaces this with a tax-module call against price-feed data.`
- New helper `_to_response(etf: Etf) -> EtfResponse` converts ORM
  row to Pydantic response. `Decimal -> float` for `ter` and
  `aum_eur` is acceptable precision loss for display; `Decimal` is
  preserved in the DB. If `ter` is `None` the helper raises
  (Phase 7 seeds always populate it).
- `list_etfs(session)` and `get_comparison(session, isin_a, isin_b)`
  take a `Session = Depends(get_session)`.
- 404 path unchanged: if either ISIN is not in the DB, raise
  `HTTPException(404, f"Unknown ISIN: {isin}")`. Same string, same
  status as Phase 6.

Contract preservation: before and after Phase 7, `GET /etfs`
returns a JSON array of objects with exactly the same field names,
types, and values for the three ISINs that the mock already had.
`GET /comparison?isin_a=...&isin_b=...` returns a JSON object with
the same `horizon_years`, `investment_eur`, `etfs`, and
`after_tax_eur` keys. The web `compare/page.tsx` and `lib/api.ts`
continue to work without modification, and the existing
`web/src/__tests__/comparison-view.test.tsx` should pass unchanged
once the API runs against a seeded DB.

## §7. Testing

Unit tests (`api/tests/unit/test_seed_etfs.py`, no DB). Each test
exercises the YAML-parse and validate path, broken out as
`_parse_yaml(path) -> list[EtfSeedRow]` so it is testable without
a DB.

- valid 3-row YAML parses to 3 `EtfSeedRow` instances
- typo in a key (`tre: 0.002`) raises `ValidationError` and the
  message names the bad key
- invalid ISIN (`IE00B4L5Y9`, too short) raises `ValidationError`
- TER above the 5% sanity bound raises `ValidationError`
- unknown `teilfreistellung_class` (`"bond"`) raises `ValidationError`
- duplicate ISIN within the YAML raises `ValueError` and the message
  names the duplicated ISIN
- the shipped `shared/etfs.yaml` itself parses cleanly and contains
  exactly 15 rows — doubles as a CI guardrail against curator typos

Integration tests (`api/tests/integration/`, Docker Postgres, reusing
the fixture setup from Phase 5's `test_migrations.py`).

`test_seed_etfs_db.py`:

- seed from `tests/fixtures/etfs_seed_sample.yaml` (3 rows); assert
  table has 3 rows with the right values
- mutate one row's TER in a copy of the fixture, re-seed; assert the
  row updated and `last_ingested_at` advanced (and is documented to
  advance for all rows)
- re-seed with the original fixture; assert `created_at` did not
  change but `updated_at` did
- re-seed the same fixture twice in a row; assert the row count
  stays at 3

`test_etfs_endpoints.py`:

- seed the 3-row sample, call `GET /etfs`; assert 200, list of 3,
  ordered by name
- call `GET /comparison?isin_a=<known>&isin_b=<known>`; assert 200,
  response shape matches `ComparisonResponse`, `etfs` array has 2
  entries in the order requested
- call `GET /comparison?isin_a=<known>&isin_b=ZZ00UNKNOWN0`; assert
  404 with body `{"detail": "Unknown ISIN: ZZ00UNKNOWN0"}`
- call `GET /comparison?isin_a=AA` (too short); assert 422 from
  FastAPI's query validation, preserving Phase 6 behavior

Each test in these files truncates `etfs` first so the seed runs
against an empty table. No second test database, no
transaction-rollback scheme.

E2E (Playwright): not in scope. Phase 9 will add one Playwright spec
covering picks → comparison → tap-to-learn against the seeded DB.

Coverage: no new tax code in Phase 7, so the 100%-line-coverage rule
does not apply. New back-end code sits comfortably above the 80%
back-end target per the test plan above.

## §8. Operations and rollout

Dependencies, added in one commit with the lockfile:

- `pyyaml` via `uv add pyyaml` (runtime)
- `types-pyyaml` via `uv add --dev types-pyyaml` (dev only, for `pyright`)

Makefile change:

```make
seed:
	cd api && uv run python -m scripts.seed_tax_constants
	cd api && uv run python -m scripts.seed_etfs
```

`make` aborts on first non-zero exit, so a broken tax-constants seed
skips the ETF seed.

CI: the existing workflow already runs `make seed` after
`make migrate` (Phase-5 commit `c13010d`). Phase 7's only CI change
is implicit; the same `make seed` now seeds two tables. No new
workflow steps, no new secrets. If the YAML is malformed, the
existing job fails with the Pydantic error.

Local rollout after merging the Phase 7 branch:

1. `cd api && uv sync` to pick up `pyyaml`
2. `docker compose -f infra/docker-compose.yml up -d` (no-op if running)
3. `make migrate` (no schema changes, harmless)
4. `make seed` — now seeds both tables
5. `make dev` and visit `/de/compare`. Dropdown shows 15 ETFs
   ordered alphabetically.

Documentation in the same PR:

- `CLAUDE.md`: append Phase 7 to the "Shipped milestones" list and
  add one sentence noting `shared/etfs.yaml` is the curated source
  of truth for the ETF list.
- `README.md`: append Phase 7 to the status section if it has one.

No deployment impact. Phase 4 is still deferred; Phase 7 ships only
locally. The two Supabase projects exist but stay untouched.

## §9. Commit plan

Following "one logical change per commit":

1. `chore(api): add pyyaml and types-pyyaml`
2. `feat(api): add etfs repository and session dependency`
3. `feat: add curated etfs.yaml with 15 rows`
4. `feat(api): add seed_etfs script with pydantic validation`
5. `feat(api): rewire /etfs and /comparison to read from postgres`
6. `chore: wire seed_etfs into make seed`
7. `chore: delete mock_etfs.json`
8. `docs: note Phase 7 in CLAUDE.md`

The API rewrite (5) lands after the seed (4) and the repository (2)
exist, and the mock deletion (7) lands only after nothing references
it. Each commit independently passes CI.

## §10. Open questions and follow-ups

None for Phase 7 itself. The deliberate follow-ups for later phases:

- Phase 8 (tax module): replace `_HARDCODED_AFTER_TAX_EUR` with a
  real calculation against `tax_constants` and (eventually) prices.
- Phase 9 (DB + tax wiring): introduce `repositories/prices.py`,
  add `GET /comparison` integration tests that exercise the tax
  module, and add a single Playwright spec.
- Later: a decision on whether to introduce `verified_on` /
  `source_url` columns on `etfs` and a re-verification cadence.
  Today these live in YAML comments only.
