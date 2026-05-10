# Durchblick — Project Plan

ETF comparison tool with German tax calculation, for intermediate German
retail investors who already invest through Sparpläne but lack confidence
in their choices. Next.js front end on Vercel, FastAPI back end on
Railway, Postgres on Supabase. Solo developer working full-time, with
Claude Code as collaborator. Target: phase one ships in approximately
four months.

This document is the authoritative spec for scope, architecture, and
decisions. For day-to-day coding rules, conventions, and domain context
see [`CLAUDE.md`](CLAUDE.md).

---

## §1. Product

**What it is.** A web-based educational and decision-support tool. Not a
broker, not a portfolio tracker, not financial advice.

**Audience.** Intermediate German retail investors who have started
investing in ETFs — often via Sparpläne with Trade Republic, Scalable
Capital, ING, or Comdirect — but lack confidence in their choices and
tax implications.

**Phase one scope.**
- Compare any two ETFs from a curated list of approximately 15 popular options on German Sparplan lists
- Side-by-side metrics: annual fee, long-term return, diversification, fund size, replication method, distribution policy
- After-tax outcome calculation over a chosen time horizon under German tax rules
- Plain-language explanation for each metric (tap to learn)
- Bilingual: German primary, English available as a switch

**Out of scope for phase one.** Individual stocks. Mutual funds. Bonds.
Portfolio tracking. Buy buttons. Broker integration. Real-time prices.
User accounts. Personalized financial advice. Historical price charts.
Social features.

**Monetization stance.** Free and ad-free in phase one. No advertising,
no affiliate revenue, no broker referrals. Long-term funding deferred
until evidence of user value.

**Success criterion.** At least 25 users compare ETFs three or more times
each, and at least 10 say unprompted that the tool helped them understand
something new.

**Timeline (target, not hard commitment).**
- Month 1 — brief, architecture, repo, deployment pipeline, static prototype
- Month 2 — data layer: KID ingestion, factsheets, price feeds, database
- Month 3 — German tax calculation layer
- Month 4 — polish, content writing, first real users

**Principles.** Depth over breadth. Trust over engagement. Plain language
always. Transparency about limits. Ship the smallest thing that works.

---

## §2. Architecture

**Tech stack.**
- Front end: Next.js with TypeScript
- Back end: Python with FastAPI
- Python package manager: `uv` exclusively (never pip)
- Database: Postgres via Supabase
- Migrations: Alembic
- Front-end hosting: Vercel
- Back-end hosting: Railway
- Source control: GitHub, monorepo
- CI: GitHub Actions

**System architecture.** Three layers with clear boundaries.

- **Presentation layer** — Next.js on Vercel. Renders pages, handles interaction, calls back end over HTTPS.
- **Comparison engine** — FastAPI on Railway. Metric calculations and German tax logic.
- **Data layer** — Postgres on Supabase, accessed only through FastAPI. ETF metadata, prices, tax constants.

A typical request: user picks two ETFs in the browser, Next.js calls a
FastAPI endpoint, FastAPI reads from Postgres, runs the comparison and
tax calculation, returns structured JSON, Next.js renders the comparison
view.

---

## §3. Data model (phase one)

- `etfs` — ISIN, name, issuer, TER, replication method, distribution policy, domicile, AUM, inception date, index tracked, Teilfreistellung classification
- `prices` — ETF ISIN, date, NAV, currency
- `tax_constants` — year, basiszins, sparerpauschbetrag, teilfreistellung rates, capital gains rate
- `comparisons` — anonymous log of ETF pairs compared, timestamp (no user identification)

Tax constants are year-indexed and stored in the database. Never hardcode
them in application code.

---

## §4. Repository and environment

**Repository structure (monorepo).**

```
/web         Next.js front end
/api         FastAPI back end
/shared      Shared types, ETF list, constants
/docs        Architecture notes, decision logs
/infra       Deployment config, Docker Compose for local dev
/migrations  Alembic database migrations
```

**Local development.** Docker Compose for Postgres. FastAPI via
`uv run uvicorn`. Next.js via `npm run dev`. A Makefile exposes
`make dev`, `make test`, `make migrate`, `make lint`. Environment
variables in `.env` (gitignored), with example values in `.env.example`
(committed).

---

## §5. Development conventions

- Work on a feature branch off `main`. Small, frequent commits — one logical change per commit. Pull request to `main` triggers CI. Merge to `main` triggers deployment.
- Commit messages: imperative mood, Conventional Commits prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Code style: TypeScript strict mode, ESLint, Prettier on the front end. Python type hints enforced, `ruff` for linting, `pyright` for type checking on the back end. All formatters run via pre-commit hook.
- Python commands: always `uv`, never pip. Dependencies in `pyproject.toml`.

See [`CLAUDE.md`](CLAUDE.md) for the full list of project conventions.

---

## §6. Testing

Three layers, each owning a different kind of confidence.

**Unit tests.** `pytest` for the back end, `vitest` for the front end.
Tax calculation module is test-driven — every rule (Vorabpauschale,
Teilfreistellung, Sparerpauschbetrag, capital gains, Solidaritätszuschlag)
has explicit cases with known inputs and expected outputs. Write the
test first, then the code.

**Integration tests.** `pytest` with a real Postgres test database
(Docker). Each test starts from a known database state and asserts the
API response.

**End-to-end tests.** Playwright, deliberately small (around 5 specs).
Critical paths only: open app, pick two ETFs, see comparison render, tap
explanation.

**Coverage targets.**
- Tax calculation module — 100% line coverage, enforced in CI
- Other back-end code — 80%
- Front-end — tracked, not enforced

**Execution.** GitHub Actions runs unit and integration tests on every
pull request. End-to-end tests run on schedule against staging. Test
fixtures live in `/api/tests/fixtures/`. Tests never hit external APIs
or production databases.

---

## §7. Security and operations

**Secrets management.** All secrets in environment variables, never
committed. Production secrets via Vercel and Railway secret managers.
`.env` gitignored; `.env.example` documents required keys with empty
values.

**Data minimization.** No user accounts in phase one. No personally
identifiable information stored. The `comparisons` table stores pair
and timestamp only — no IP, no user agent, no fingerprint. No
third-party analytics or tracking.

**GDPR posture.** Operating under GDPR. Privacy policy published before
phase one launch. No cookies beyond strictly necessary. All data
processing happens within the EU (Supabase EU region, Railway EU region).

**Dependency security.** `uv` lockfile committed for reproducible Python
builds. `npm` lockfile committed for the front end. Dependabot enabled
for security advisories. Manual review of any new dependency.

**Disclaimers in UI.** "Not financial advice" displayed prominently.
"Past returns don't predict future returns" near every return metric.
About page clearly states the tool is informational only.

**Deployment.** Push to `main` triggers Vercel to redeploy the front end
and Railway to redeploy the back end. Alembic migrations run automatically
on Railway deploy. Rollback via Vercel and Railway dashboards.

**Environments.**
- Local — developer machine with Docker Postgres
- Staging — Vercel preview deployments, Railway staging service
- Production — Vercel production, Railway production

**Monitoring.** Vercel and Railway built-in logs. No third-party
monitoring in phase one. Manual checks of deployed app after every
release.

**Iteration approach.** Ship small, ship often. Each week ends with
something deployed. Feedback from newsletter readers and first users —
no in-app surveys. A weekly newsletter post in German runs in parallel
with development from week one.

---

## §8. Non-reversible decisions

These choices are committed to and should not be revisited without strong
reason. Each is expensive to undo later; making them deliberate now costs
nothing.

- **Bilingual from day one.** Translation file structure exists from the first commit; no hardcoded UI strings.
- **No user accounts in phase one.** No auth, no user table, no sessions. Adding this later is a real migration.
- **Privacy-first.** No analytics, no tracking pixels, no third-party scripts beyond what is named and justified here.
- **Server-side rendering for the comparison view.** Indexable by search engines, works without JavaScript.
- **No emojis anywhere.** Code, commits, documentation, UI copy, error messages — plain text only.
- **uv only for Python.** Never pip in any script, command, or documentation.

---

## §9. Deferred to later phases

- Authentication and user accounts
- Mobile apps
- Asset classes other than ETFs (mutual funds in phase two, individual stocks in phase three)
- Real-time prices
- Multi-currency support
- Personalized tax optimization
- Portfolio tracking
