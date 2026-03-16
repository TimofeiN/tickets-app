# tickets_app

Monorepo for travel search MVP (frontend + backend + postgres).

## Stack
- Frontend: React + Vite
- Backend: FastAPI (Python deps via uv)
- Database: PostgreSQL
- Infra: Docker Compose

## Top-level structure
- `apps/frontend` - React app
- `apps/backend` - FastAPI app
- `infra/docker` - Dockerfiles
- `infra/postgres/init` - init SQL scripts for local Postgres
- `docs` - product/technical docs
- `scripts` - dev/CI helpers
- `.github/workflows` - CI workflows

## Local start
1. `make init`
2. Fill `.env`:
   - `TRAVELPAYOUTS_API_TOKEN`
   - `OPENAI_API_KEY`
3. `make up`
4. If needed, run `make backend-db-upgrade`
5. Open frontend: `http://localhost:3100`
6. Backend health: `http://localhost:8100/health`

## OpenAI setup
- Local env template already includes the required OpenAI var in `.env.example`.
- Minimum required vars for LLM features:
  - `OPENAI_API_KEY=<your key>`
- End-to-end smoke check after startup:
  - `make backend-llm-smoke`
- This smoke command prints:
  - ranking mode
  - enrichment mode
  - fallback reasons
  - option-level enrichment
  - result-level guidance

## Backend dependencies
- Backend dependency source of truth: `apps/backend/pyproject.toml` + `apps/backend/uv.lock`.
- Sync local `.venv` for IDE and local tooling:
  - `make backend-sync`
- Docker backend image installs from the same lockfile via `uv sync --frozen --extra dev`.

## Common commands
- `make ps`
- `make logs`
- `make backend-sync`
- `make backend-test`
- `make backend-lint`
- `make backend-check`
- `make backend-format`
- `make backend-db-upgrade`
- `make backend-db-current`
- `make backend-sync-iata`
- `make backend-llm-smoke`
- `make frontend-lint`
- `make frontend-build`
