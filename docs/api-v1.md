# API v1 (MVP, no LLM yet)

## Endpoints
- `GET /health`
- `POST /search`

## POST /search request
Required fields:
- `origin_city` (string)
- `dates_mode` (`strict` | `flexible`)
- `themes` (array, 1..5)
- `budget_usd` (integer, 100..50000)

Optional:
- `travelers_count` (default `2`)

Dates payload rules:
- if `dates_mode = strict`: must include `strict_dates`, must not include `flexible_dates`
- if `dates_mode = flexible`: must include `flexible_dates`, must not include `strict_dates`

### Strict example
```json
{
  "origin_city": "Belgrade",
  "dates_mode": "strict",
  "strict_dates": {
    "start_date": "2026-06-10",
    "end_date": "2026-06-17"
  },
  "themes": ["beach", "history"],
  "budget_usd": 2000,
  "travelers_count": 2
}
```

### Flexible example
```json
{
  "origin_city": "Belgrade",
  "dates_mode": "flexible",
  "flexible_dates": {
    "year": 2026,
    "month": 7,
    "trip_length_days": 7
  },
  "themes": ["beach"],
  "budget_usd": 1800,
  "travelers_count": 2
}
```

## POST /search response
Returns exactly 3 options.

```json
{
  "options": [
    {
      "option_id": "opt_bcn_001",
      "destination_city": "Barcelona",
      "origin_airport": "BEG",
      "destination_airport": "BCN",
      "price_usd": 640,
      "score": 0.92,
      "reason": "Beach + culture fit and good weather in selected window."
    }
  ]
}
```

Validation errors use FastAPI default `422` response.

## Search pipeline
Current backend behavior for `POST /search`:
1. Resolve/collect flight candidates via Travelpayouts provider client.
2. If provider is unavailable, use internal fallback candidates.
3. Apply rules filtering before ranking:
   - budget filter (`price_usd <= budget_usd / travelers_count`)
   - strict dates filter (candidate interval must fit requested interval)
   - flexible dates filter (year/month/trip length exact match)
4. Apply deterministic non-LLM ranking.
5. Return top 3 options (if filtered set has less than 3, fill from cheapest remaining candidates).

## Provider env vars
- `TRAVELPAYOUTS_API_TOKEN` - API token for live provider calls.
- `TRAVELPAYOUTS_MARKER` - optional marker parameter.
- `TRAVELPAYOUTS_BASE_URL` - optional base URL (default `https://api.travelpayouts.com`).
- `TRAVELPAYOUTS_TIMEOUT_SEC` - optional timeout for provider requests (default `3`).

## IATA city mapping
- Backend resolves `destination_city` from local table `iata_city_map` by `destination_airport` IATA code.
- DB reads/writes use SQLModel + SQLAlchemy (no raw SQL in app services/scripts).
- Table schema is versioned with Alembic (`apps/backend/alembic/versions`).
- Manual sync command:
  - `make backend-db-upgrade`
  - `make backend-sync-iata`
- Sync source datasets:
  - `${TRAVELPAYOUTS_DATA_BASE_URL}/${TRAVELPAYOUTS_DATA_LANG}/airports.json`
  - `${TRAVELPAYOUTS_DATA_BASE_URL}/${TRAVELPAYOUTS_DATA_LANG}/cities.json`
