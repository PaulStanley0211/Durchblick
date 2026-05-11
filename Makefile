.PHONY: setup dev test lint migrate migrate-new seed dev-api dev-web

setup:
	cd api && uv sync
	cd web && npm install
	uv tool install --quiet pre-commit
	pre-commit install
	docker compose -f infra/docker-compose.yml up -d

dev:
	$(MAKE) -j2 dev-api dev-web

dev-api:
	cd api && uv run uvicorn app.main:app --reload

dev-web:
	cd web && npm run dev

test:
	cd api && uv run pytest
	cd web && npm run test

lint:
	cd api && uv run ruff check app/ tests/
	cd api && uv run pyright app/
	cd web && npm run lint
	cd web && npm run typecheck
	npx --prefix web prettier --check .

migrate:
	cd api && uv run alembic upgrade head

migrate-new:
	cd api && uv run alembic revision --autogenerate -m "$(MSG)"

seed:
	cd api && uv run python -m scripts.seed_tax_constants
	cd api && uv run python -m scripts.seed_etfs
