.PHONY: init up down logs ps backend-test backend-lint backend-check backend-format backend-db-upgrade backend-db-current backend-sync-iata backend-llm-smoke frontend-lint frontend-build

init:
	cp -n .env.example .env || true

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

backend-test:
	docker compose run --rm backend pytest

backend-lint:
	docker compose run --rm backend ruff check .

backend-check:
	docker compose run --rm backend ruff check . && docker compose run --rm backend ruff format . --check && docker compose run --rm backend pytest

backend-format:
	docker compose run --rm backend ruff check . --fix && docker compose run --rm backend ruff format .

backend-db-upgrade:
	docker compose run --rm backend alembic -c alembic.ini upgrade head

backend-db-current:
	docker compose run --rm backend alembic -c alembic.ini current

backend-sync-iata:
	docker compose run --rm backend python scripts/sync_iata_city_map.py

backend-llm-smoke:
	docker compose run --rm backend python scripts/dev/manual_search_check.py

frontend-lint:
	docker compose run --rm frontend npm run lint && docker compose run --rm frontend npm run format

frontend-build:
	docker compose run --rm frontend npm run build
