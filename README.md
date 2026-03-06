# tickets_app

Monorepo for travel search MVP (frontend + backend + postgres).

## Top-level structure

- `apps/frontend` - React app
- `apps/backend` - FastAPI app
- `infra/docker` - Docker-related assets (Dockerfiles, helper configs)
- `infra/postgres/init` - SQL/init scripts for local Postgres bootstrap
- `docs` - product/technical documentation
- `scripts` - local dev/CI helper scripts
- `.github/workflows` - CI workflows

## Quick start (planned)

1. Copy `.env.example` to `.env`
2. Fill required environment variables
3. Run `docker compose up --build`
