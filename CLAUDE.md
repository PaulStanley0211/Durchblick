# Durchblick — ETF comparison with German tax

ETF comparison tool for German retail investors: side-by-side metrics,
after-tax outcomes under German tax rules, plain-language explanations.
Next.js front end on Vercel, FastAPI back end on Railway, Postgres on
Supabase. Monorepo, solo developer with Claude Code as collaborator.

## Status

**Pre-code.** Planning artifacts complete; implementation has not started.
Do not assume any code, test, schema, or deployment exists. The first
Claude Code sessions will bootstrap the monorepo skeleton.

Planning artifacts:

1. [`PLAN.md`](PLAN.md) — authoritative spec for scope, architecture, data model, testing, security, deployment. Nine §-numbered sections.
2. [`CLAUDE.md`](CLAUDE.md) — this file. Coding rules, conventions, and domain context for Claude Code.

Once the project is bootstrapped, this Status section grows. Each shipped
milestone gets a one-line entry.

## When you start work

Read [`README.md`](README.md) once it exists for the public-facing summary.
Read [`PLAN.md`](PLAN.md) when the task touches scope, architecture, or
any decision about what's in or out of phase one. For routine code work,
this file alone is enough.

## Tech stack

- Front end: Next.js with TypeScript (strict mode), in `/web`
- Back end: Python 3.12+ with FastAPI, in `/api`
- Database: Postgres (Supabase in production, Docker locally)
- Migrations: Alembic, in `/migrations`
- Python deps: `uv` and `pyproject.toml`. Never pip.
- Front-end deps: `npm` and `package.json`
- Hosting: Vercel (front end), Railway (back end), Supabase (database)

## Repository structure

```
/web         Next.js front end
/api         FastAPI back end
/shared      Shared types, ETF list, constants
/docs        Architecture notes, decision logs
/infra       Docker Compose, deployment config
/migrations  Alembic migrations
```

## Common commands

Run from the directory that owns the tool — `uv` and `pytest` from `/api`,
`npm` from `/web`. Make targets live at the repo root.

```bash
# Repo root (Makefile)
make setup       # install all deps, start local Postgres, run migrations
make dev         # run front end and back end in parallel
make test        # run all tests
make lint        # run linters and formatters
make migrate     # create or apply database migrations

# Backend — always uv, never pip
cd api
uv sync                                           # install deps
uv run pytest                                     # run tests
uv run ruff check app/ tests/                     # lint
uv run uvicorn app.main:app --reload              # run dev server
uv run alembic revision --autogenerate -m "msg"   # create migration
uv add <package>                                  # add dependency

# Frontend
cd web
npm install
npm run dev
npm run test
npm run lint
npm run typecheck
```

## Project conventions and gotchas

- **uv only for Python. Never pip.** Every Python command in code, docs, README, or example uses `uv`. Never `pip install`, never `python -m pip`, never `requirements.txt`. Dependencies live in `pyproject.toml`.
- **No emojis anywhere.** Not in code, not in commit messages, not in documentation, not in UI strings, not in error messages, not in log output, not in comments. Plain text only.
- **No financial advice framing.** The product is informational. Never write copy or comments that frame the tool as advice, recommendation, or guidance. Use "comparison," "information," "calculation." Never "should," "best for you," "recommended."
- **No hardcoded UI strings.** All user-facing text goes through the translation system. German (primary) and English (secondary) present from the first commit of any feature.
- **Tax math is test-driven.** Never write tax calculation code without a failing test first. Every German tax rule (Vorabpauschale, Teilfreistellung, Sparerpauschbetrag, capital gains, Solidaritätszuschlag) has explicit cases with known inputs and expected outputs.
- **One logical change per commit.** Imperative mood. Conventional Commits prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- **Tax constants live in the database, not in code.** The `tax_constants` table holds year-indexed values (Basiszins, Sparerpauschbetrag amount, Teilfreistellung rates). Tax law changes; never hardcode the numbers.
- **No user accounts in phase one.** No auth, no user table, no sessions. The `comparisons` table stores pair and timestamp only — no IP, no user agent, no fingerprint.

This section will grow. Real gotchas hit during development get appended
here so they don't get hit twice.

## Domain context

The product serves German retail investors. Claude should recognise these
terms without explanation:

- **Sparplan** — automatic monthly investment plan, near-universal feature of German brokers
- **TER** — total expense ratio, the annual fee charged by an ETF
- **KID / KIID** — Key Information Document, mandatory disclosure for any retail fund in the EU
- **ISIN** — international identifier for a financial instrument
- **Vorabpauschale** — advance lump-sum tax on accumulating funds in Germany
- **Teilfreistellung** — partial tax exemption: 30% for equity-heavy funds, 15% for mixed funds
- **Sparerpauschbetrag** — annual tax-free allowance for investment income (€1,000)
- **Basiszins** — base interest rate set yearly by the Bundesbank, used in Vorabpauschale
- **Solidaritätszuschlag** — solidarity surcharge of 5.5% on top of capital gains tax
- **Kirchensteuer** — church tax, optional, varies by federal state

Tax calculation references the current German Investmentsteuergesetz.

## Testing targets

- Tax calculation module — 100% line coverage, enforced in CI
- Other back-end code — 80% target
- Front-end — tracked, not enforced
- Test fixtures in `/api/tests/fixtures/`
- Tests never hit external APIs or production database
- End-to-end tests (Playwright) deliberately small — around 5 specs covering critical paths only

## What this project is not

- Not a broker
- Not a portfolio tracker
- Not a financial advisor
- Not a real-time price service
- Not an authenticated app in phase one

Push back and check [`PLAN.md`](PLAN.md) before adding features that fit
any of those descriptions.

## Required environment variables

`DATABASE_URL`, `SUPABASE_URL`, and `SUPABASE_ANON_KEY` are required for
any back-end run. Data provider API keys will be added when the data
layer is built in month two. See `.env.example` (committed) for the
canonical list with empty values; real values live in `.env` (gitignored).
