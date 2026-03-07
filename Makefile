.PHONY: init up down logs ps backend-test backend-lint frontend-lint frontend-build

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
	docker compose run --rm backend ruff check . && docker compose run --rm backend black --check .

frontend-lint:
	docker compose run --rm frontend npm run lint && docker compose run --rm frontend npm run format

frontend-build:
	docker compose run --rm frontend npm run build
