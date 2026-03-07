# Current Status (2026-03-07)

## Completed in this branch
- Monorepo skeleton initialized
- Docker Compose stack configured (`frontend`, `backend`, `postgres`)
- Python package management in backend switched to `uv`
- CORS configured for local frontend origins
- Backend endpoint `POST /search` added with request validation
- API response contract stabilized for frontend integration
- Frontend search form connected to backend and renders top-3 options
- Backend tests and frontend build pass in Docker
- Travelpayouts integration layer added with env-based config
- Provider fallback implemented when external API is unavailable
- Rules filtering added before ranking:
  - budget per traveler check (`budget_usd / travelers_count`)
  - strict/flexible date filtering
- Deterministic non-LLM ranking and fallback-to-3 options added
- Backend unit tests added for filtering logic
- Local table `iata_city_map` added for city-name resolution
- Manual sync script added to fill/update IATA mapping from Travelpayouts data API
- Alembic migrations initialized for DB schema versioning
- DB access refactored from raw SQL to SQLModel + SQLAlchemy sessions

## Local run
- `make init`
- `make up`
- frontend: `http://localhost:3000`
- backend health: `http://localhost:8000/health`
- postgres host port: `5433`

## Notes
- Current `POST /search` uses provider + rules filtering + deterministic ranking (no LLM yet).
- Live Travelpayouts requests are attempted for strict-date mode when `TRAVELPAYOUTS_API_TOKEN` is set.
- If provider call fails/unavailable, backend uses internal fallback dataset.
- Destination city names are resolved from local DB mapping when available.
- DB schema updates are managed via Alembic revisions.
- OpenAPI schema contains request/response examples.
