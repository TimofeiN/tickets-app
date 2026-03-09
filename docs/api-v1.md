# API v1 (MVP + LLM ranking fallback)

## Endpoints
- `GET /health`
- `POST /search`

## Architecture context for API
- `POST /search` is orchestrated by `SearchService` (application layer).
- Flight data comes from Travelpayouts provider adapter with internal fallback dataset.
- Ranking is LLM-first with deterministic fallback.
- Response contains up to 3 options (`1..3`) and a `meta` block describing runtime mode.

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
Returns up to 3 options (`1..3`).

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
  ],
  "meta": {
    "data_source": "live",
    "ranking_mode": "llm",
    "constraints_relaxed": false,
    "fallback_reasons": []
  }
}
```

`meta` fields:
- `data_source`: `live` when external provider data is used, `fallback` when internal fallback dataset is used.
- `ranking_mode`: `llm` when LLM ranking succeeded, `deterministic` when deterministic ranking is used.
- `constraints_relaxed`: `true` when backend includes options outside strict budget/date-filtered matches.
- `fallback_reasons`: machine-readable degradation reasons (provider fallback / LLM fallback / relaxed constraints).

Validation errors use FastAPI default `422` response.

## Search pipeline
Current backend behavior for `POST /search`:
1. Resolve/collect flight candidates via Travelpayouts provider client:
   - map `origin_city` to all known origin airports from DB (`iata_city_map`);
   - query provider asynchronously per origin airport;
   - merge and deduplicate candidates.
2. If provider is unavailable, use internal fallback candidates.
3. Apply rules filtering before ranking:
   - budget filter (`price_usd <= budget_usd / travelers_count`)
   - strict dates filter (candidate interval must fit requested interval)
   - flexible dates filter (year/month/trip length exact match)
4. Build deterministic shortlist for ranking (bounded by `LLM_SHORTLIST_LIMIT`).
5. Attempt one LLM ranking request with strict JSON-schema output validation.
6. If LLM ranking fails (config error, timeout/provider error, invalid/malformed output), fallback to deterministic ranking.
7. Deterministic final selection returns up to 3 options:
   - prefers cheapest candidates;
   - enforces unique `destination_airport` among returned options;
   - may return fewer than 3 when there are not enough unique destinations.

## Known MVP behavior
- `constraints_relaxed=true` is expected when response uses non-filtered options.
- Response is variable-length (`1..3`), not fixed-length.
- Live provider currently supports strict-date mode only.
- Origin city-to-airport mapping for live requests is resolved from DB (`iata_city_map`) by normalized `city_name`.

## Provider env vars
- `TRAVELPAYOUTS_API_TOKEN` - API token for live provider calls.
- `TRAVELPAYOUTS_MARKER` - optional marker parameter.
- `TRAVELPAYOUTS_BASE_URL` - optional base URL (default `https://api.travelpayouts.com`).
- `TRAVELPAYOUTS_TIMEOUT_SEC` - optional timeout for provider requests (default `3`).

## LLM ranking env vars
- `LLM_PROVIDER` - ranking provider (currently supported: `openai`).
- `LLM_API_KEY` - provider API key.
- `LLM_MODEL` - provider model ID.
- `LLM_BASE_URL` - optional provider base URL (default `https://api.openai.com`).
- `LLM_TIMEOUT_SEC` - optional request timeout (default `5`).
- `LLM_MAX_TOKENS` - optional output token cap (default `300`).
- `LLM_RETRY_COUNT` - optional retry count for provider/network errors (default `1`).
- `LLM_RETRY_BACKOFF_MS` - optional bounded linear backoff in ms (default `150`).
- `LLM_SHORTLIST_LIMIT` - optional shortlist size before LLM call (default `8`, range `3..12`).

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
