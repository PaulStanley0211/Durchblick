.PHONY: setup dev test lint migrate dev-api dev-web

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
	@echo "not implemented yet (filled in Phase 5)"
