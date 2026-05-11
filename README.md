# Durchblick

[![CI](https://github.com/PaulStanley0211/Durchblick/actions/workflows/ci.yml/badge.svg)](https://github.com/PaulStanley0211/Durchblick/actions/workflows/ci.yml)

Durchblick is a web-based ETF comparison tool for German retail investors. It shows side-by-side metrics, after-tax outcomes under German tax rules, and plain-language explanations for every number. Informational only — not financial advice.

## Status

Early-stage build. In place today:

- Monorepo: `/api` (FastAPI, uv-managed Python 3.12), `/web` (Next.js 16, TypeScript strict, Tailwind v4), `/infra` (Postgres 16 via Docker Compose for local dev)
- Back end: `/health` endpoint, ruff + pyright (strict for `app/`) + pytest with one passing test
- Front end: bilingual placeholder home (German default, English available via `/en`), vitest + React Testing Library with one passing test
- Root tooling: Prettier, pre-commit hooks (ruff, prettier, standard validators), `Makefile` targets, `.gitattributes` for cross-platform line endings
- CI: GitHub Actions runs lint, typecheck, and tests on every pull request

Not built yet: deployment pipelines, database schema, data ingestion, German tax calculation, the actual side-by-side comparison view, privacy policy. See [PLAN.md](PLAN.md) for the authoritative scope and phased build plan.

## Local development

Requires `uv`, Node 22+, and Docker. Optionally `make` (Linux/macOS/WSL natively, or `choco install make` / `scoop install make` on Windows).

With `make`:

```
make setup    # install deps, start local Postgres
make dev      # run back end and front end in parallel
make test     # run both test suites
make lint     # run all linters and type checkers
```

Without `make`:

```
cd api && uv sync
cd web && npm install
docker compose -f infra/docker-compose.yml up -d

# in separate shells:
cd api && uv run uvicorn app.main:app --reload    # back end on :8000
cd web && npm run dev                              # front end on :3000
```

The placeholder home is at http://localhost:3000 (redirects to `/de`; switch to `/en` for English).

## Project documents

- [PLAN.md](PLAN.md) — scope, architecture, data model, testing, security, deployment
- [CLAUDE.md](CLAUDE.md) — coding conventions and domain context
