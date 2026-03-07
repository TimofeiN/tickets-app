# API v1 (MVP mock)

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
