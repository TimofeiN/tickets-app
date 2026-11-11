# tickets_app

A travel search MVP. Give it an origin city, dates, a total budget and a few
travel themes, and it returns a short ranked list of destination ideas built
from real flight fares. An LLM ranks the shortlist and adds trip notes. If the
LLM is temporarily unavailable, the app falls back to rule-based ranking.
`OPENAI_API_KEY` is required: a missing key fails the request.

Signed-in users get their searches saved automatically and can rate
recommendations.

## Features
- Flight candidates from the Travelpayouts / Aviasales API, filtered by budget and dates.
- Factual shortlist, then LLM semantic scoring, then final ranking (with fallbacks when the LLM fails).
- Trip notes and "how to improve your search" guidance per result.
- Accounts with saved search history and like/dislike reactions.

## Stack
- Frontend: React 19 + Vite
- Backend: FastAPI, SQLModel, Alembic (Python 3.12, dependencies managed by [uv](https://docs.astral.sh/uv/))
- Database: PostgreSQL 16
- Infra: Docker Compose (development setup)

See [docs/app_tree.md](docs/app_tree.md) for the project structure and layering.

## Requirements
- Docker with Compose
- [uv](https://docs.astral.sh/uv/) (only for a local `.venv` used by your IDE)
- API keys: a [Travelpayouts](https://www.travelpayouts.com/) token and an OpenAI key

## Quick start
1. `make init` creates `.env` from `.env.example`.
2. Fill in `.env`:
   - `TRAVELPAYOUTS_API_TOKEN`
   - `OPENAI_API_KEY`
3. `make up`
4. `make be-db-upgrade` applies database migrations.
5. `make be-sync-iata` loads the IATA/city dataset used for origin and destination names.
6. Open the frontend at <http://localhost:3100>. The backend health check is <http://localhost:8100/health>.

The Docker setup is meant for local development: the backend runs with
`--reload`, the frontend runs the Vite dev server, and source folders are
mounted into the containers. The database password in `.env.example` is a
local default, change it for anything else.

## Dependencies
- Backend: `apps/backend/pyproject.toml` + `apps/backend/uv.lock` are the source of truth.
  The Docker image installs with `uv sync --frozen`. `make be-deps` syncs a local `.venv` and rebuilds the image.
- Frontend: `apps/frontend/package.json` + `package-lock.json`, installed with `npm ci`.

## Commands
Run `make` targets from the repository root.

| Command | What it does |
| --- | --- |
| `make up` / `make up-build` / `make down` | Start (optionally rebuild) / stop the stack |
| `make ps` / `make logs` | Show containers / follow logs |
| `make be-deps` | Sync local `.venv` and rebuild the backend image |
| `make be-test` | Run backend tests |
| `make be-lint` | Ruff lint and format check |
| `make be-mypy` | Type check |
| `make be-check` | Lint, format check, mypy and tests (run before committing) |
| `make be-format` | Apply ruff fixes and formatting |
| `make be-db-upgrade` / `make be-db-current` | Apply migrations / show current revision |
| `make be-sync-iata` | Sync the IATA/city dataset into the database |
| `make fe-lint` | ESLint and Prettier check |
| `make fe-format` | Apply ESLint fixes and Prettier formatting |
| `make fe-build` | Production build of the frontend |

Backend commands run inside the backend container.

## API
Interactive docs are served by FastAPI at <http://localhost:8100/docs>.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| POST | `/auth/register`, `/auth/login` | Create an account / sign in, returns an access token |
| GET | `/auth/me` | Current user |
| POST | `/auth/logout` | End the session |
| POST | `/search` | Run a search (saved when signed in) |
| GET | `/searches`, `/searches/{id}` | Saved searches |
| POST | `/search/suggestions/{id}/reaction` | Like or dislike a suggestion |

## CI
GitHub Actions runs on every push and pull request:
- Backend: `uv sync --frozen`, ruff (lint and format), mypy, pytest.
- Frontend: `npm ci`, ESLint, Prettier check, build.

## License
[MIT](LICENSE)
