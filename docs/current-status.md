# Current Status (2026-03-07)

## Backend architecture (current)
- Layered backend structure is in place:
  - `api`: HTTP routers + request/response schemas + dependency wiring
  - `application`: search orchestration + ranking service + ports
  - `domain`: pure models and rules (filtering/scoring)
  - `infrastructure`: Travelpayouts/OpenAI providers + SQLModel repository/session
  - `core`: app config and logging
- Main endpoint: `POST /search` with strict request validation and variable-length response (`1..3` options).
- Search pipeline:
  1. Retrieve candidates from Travelpayouts live API when possible (async fan-out across all mapped origin airports).
  2. Fallback to internal dataset if provider is unavailable.
  3. Apply rules filtering (budget-per-traveler + strict/flexible dates).
  4. Build deterministic shortlist (`LLM_SHORTLIST_LIMIT` bounded).
  5. Try LLM ranking with strict schema validation.
  6. Fallback to deterministic ranking if LLM is disabled/fails.
  7. Return up to 3 options (1..3):
     - deterministic selection prefers cheapest options,
     - keeps destination diversity (unique `destination_airport`),
     - may return fewer than 3 if there are not enough unique destinations.
- Response transparency:
  - `meta.data_source`: `live | fallback`
  - `meta.ranking_mode`: `llm | deterministic`
  - `meta.constraints_relaxed`: whether response includes non-filtered options (budget/date constraints were relaxed)
  - `meta.fallback_reasons`: degradation reasons (provider/LLM/relaxed constraints)

## Data and operations
- Local mapping table `iata_city_map` is used for destination city resolution by airport/city IATA code.
- Origin city to airport resolution is DB-backed via `iata_city_map` (`city_name -> airport IATA list`).
- Schema versioning is managed by Alembic (`apps/backend/alembic/versions`).
- IATA mapping can be synced from Travelpayouts data API via `apps/backend/scripts/sync_iata_city_map.py`.
- DB access is SQLModel + SQLAlchemy sessions (`infrastructure/db`).

## Local run
- `make init`
- `make up`
- frontend: `http://localhost:3000`
- backend health: `http://localhost:8000/health`
- postgres host port: `5433`

## Quality gates
- Backend checks: `make backend-check` (ruff + format check + pytest).
- Frontend checks: `make frontend-lint` and `make frontend-build`.
- Current backend test suite covers health, request validation, filtering, LLM ranking success/failure paths.
