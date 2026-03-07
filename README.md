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
2. `make up`
3. Open frontend: `http://localhost:3000`
4. Backend health: `http://localhost:8000/health`

## Common commands
- `make ps`
- `make logs`
- `make backend-test`
- `make backend-lint`
- `make frontend-lint`
- `make frontend-build`
