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
   - `LLM_API_KEY`
   - `LLM_MODEL` (for example `gpt-4.1-mini`)
3. `make up`
4. If needed, run `make backend-db-upgrade`
5. Open frontend: `http://localhost:3000`
6. Backend health: `http://localhost:8000/health`

## OpenAI setup
- Local env template already includes all required OpenAI vars in `.env.example`.
- Minimum required vars for LLM features:
  - `LLM_API_KEY=<your key>`
  - `LLM_MODEL=gpt-4.1-mini`
- Optional tuning vars:
  - `LLM_BASE_URL`
  - `LLM_TIMEOUT_SEC`
  - `LLM_MAX_TOKENS`
  - `LLM_RETRY_COUNT`
  - `LLM_RETRY_BACKOFF_MS`
  - `LLM_SHORTLIST_LIMIT`
- End-to-end smoke check after startup:
  - `make backend-llm-smoke`
- This smoke command prints:
  - ranking mode
  - enrichment mode
  - fallback reasons
  - option-level enrichment
  - result-level guidance

## Common commands
- `make ps`
- `make logs`
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
