.PHONY: init up up-build down logs ps be-deps be-test be-lint be-mypy be-check be-format be-db-upgrade be-db-current be-sync-iata fe-lint fe-format fe-build

init:
	cp -n .env.example .env || true

up:
	docker compose up -d

up-build:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

be-deps:
	cd apps/backend && uv sync --frozen
	docker compose build backend

be-test:
	docker compose run --rm backend pytest

be-lint:
	docker compose run --rm backend bash -c 'ruff check . && ruff format . --check'

be-mypy:
	docker compose run --rm backend mypy .

be-check:
	docker compose run --rm backend ruff check . && docker compose run --rm backend ruff format . --check && docker compose run --rm backend mypy . && docker compose run --rm backend pytest

be-format:
	docker compose run --rm backend ruff check . --fix && docker compose run --rm backend ruff format .

be-db-upgrade:
	docker compose run --rm backend alembic -c alembic.ini upgrade head

be-db-current:
	docker compose run --rm backend alembic -c alembic.ini current

be-sync-iata:
	docker compose run --rm backend python scripts/sync_iata_city_map.py

fe-lint:
	docker compose run --rm frontend npm run lint && docker compose run --rm frontend npm run format

fe-format:
	docker compose run --rm frontend npm run lint:fix && docker compose run --rm frontend npm run format:write

fe-build:
	docker compose run --rm frontend npm run build
