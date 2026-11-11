# Project tree

Monorepo layout and the responsibility of each module.

```text
.
├── apps/
│   ├── backend/                       # FastAPI service (Python 3.12, uv)
│   │   ├── pyproject.toml             # Dependencies, ruff, mypy, pytest config
│   │   ├── uv.lock                    # Locked dependencies (source of truth)
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py                 # Alembic runtime environment
│   │   │   └── versions/              # DB migrations (0001..0004)
│   │   ├── app/
│   │   │   ├── main.py                # FastAPI entrypoint: logging, middleware, routers
│   │   │   ├── middleware.py          # CORS setup
│   │   │   ├── exception_handler.py   # Typed errors -> HTTP error contract
│   │   │   ├── api/
│   │   │   │   ├── deps.py            # DI factories for services and adapters
│   │   │   │   ├── mappers/
│   │   │   │   │   └── trip_preferences_mapper.py  # SearchRequest -> TripPreferences
│   │   │   │   ├── routers/
│   │   │   │   │   ├── auth.py            # /auth: register, login, me, logout
│   │   │   │   │   ├── health.py          # /health liveness
│   │   │   │   │   ├── saved_searches.py  # /searches: list and open saved searches
│   │   │   │   │   └── search.py          # /search and suggestion reactions
│   │   │   │   ├── schemas/               # Pydantic request/response models
│   │   │   │   │   ├── auth/              # requests.py, responses.py
│   │   │   │   │   └── search/            # request.py, response.py, saved.py, reaction.py
│   │   │   │   └── services/              # HTTP-boundary orchestration
│   │   │   │       ├── auth_api_service.py
│   │   │   │       ├── saved_search_api_service.py
│   │   │   │       └── search_api_service.py
│   │   │   ├── application/               # Use cases, independent of HTTP and DB
│   │   │   │   ├── dto/                   # search_pipeline.py, search_result.py
│   │   │   │   ├── ports/                 # Contracts: city_resolver, flight_search_provider,
│   │   │   │   │                          #   llm_provider, origin_airport_resolver
│   │   │   │   └── services/
│   │   │   │       ├── auth_service.py               # Passwords (scrypt) and session tokens
│   │   │   │       ├── search_service.py             # Search orchestration and degradation
│   │   │   │       ├── flight_candidates_service.py  # Candidate fetching per origin airport
│   │   │   │       ├── factual_shortlist_service.py  # Filtering, dedup, shortlist scoring
│   │   │   │       ├── semantic_scoring_service.py   # LLM semantic scoring of the shortlist
│   │   │   │       ├── final_ranking_service.py      # Combines factual and semantic signals
│   │   │   │       └── enrichment_service.py         # LLM trip notes and guidance
│   │   │   ├── core/
│   │   │   │   ├── settings.py        # Env-based settings (pydantic-settings)
│   │   │   │   ├── errors.py          # Shared typed exceptions
│   │   │   │   ├── logging.py         # Logging configuration
│   │   │   │   └── metrics.py         # Degradation metric-style log emitters
│   │   │   ├── domain/
│   │   │   │   ├── models/            # flight_candidate.py, trip_preferences.py
│   │   │   │   └── services/
│   │   │   │       └── filtering.py   # Budget/date filtering rules
│   │   │   ├── infrastructure/
│   │   │   │   ├── db/
│   │   │   │   │   ├── session.py     # Engine and session helpers
│   │   │   │   │   ├── models/        # SQLModel tables: iata_city_map, user_account,
│   │   │   │   │   │                  #   user_session, saved_search, trip_suggestion,
│   │   │   │   │   │                  #   trip_suggestion_reaction
│   │   │   │   │   └── repositories/  # auth, saved_search, trip_suggestion,
│   │   │   │   │                      #   iata_city, origin_airport
│   │   │   │   └── providers/
│   │   │   │       ├── openai_provider.py        # LLM adapter
│   │   │   │       └── travelpayouts_provider.py # Flight API adapter
│   │   │   └── shared/
│   │   │       ├── enums.py           # Enums shared across layers
│   │   │       └── strict_model.py    # Pydantic base model forbidding extra fields
│   │   ├── scripts/
│   │   │   └── sync_iata_city_map.py  # Pull and upsert the IATA/city dataset
│   │   └── tests/                     # pytest suite
│   │
│   └── frontend/                      # React + Vite
│       ├── package.json
│       ├── package-lock.json
│       ├── vite.config.js
│       ├── eslint.config.js
│       └── src/
│           ├── main.jsx               # React entrypoint
│           ├── App.jsx                # Page composition and search flow state
│           ├── config/constants.js    # Backend URL, themes, user-facing label maps
│           ├── api/
│           │   ├── client.js          # fetchJson and error message extraction
│           │   └── authStorage.js     # Access token persistence (localStorage)
│           ├── hooks/
│           │   ├── useAuth.js         # Session bootstrap, sign in/up, sign out
│           │   ├── useSavedSearches.js
│           │   ├── useReactions.js    # Like/dislike state and requests
│           │   └── useLoadingStep.js  # Rotating loading messages
│           ├── utils/
│           │   ├── format.js          # Date, currency, badge and label helpers
│           │   └── searchPayload.js   # API payload <-> UI state mapping
│           ├── components/            # HeroCopy, AccountPanel, SearchForm,
│           │                          #   StatusBanners, ResultsMain, OptionCard,
│           │                          #   ResultMeta, GuidancePanel, ResultSkeleton,
│           │                          #   SearchSummary, SavedSearchesPanel
│           └── styles/                # CSS split by area, imported in order
│               ├── index.css          # Import order (matters for the cascade)
│               ├── base.css           # Tokens, reset, form element defaults
│               ├── layout.css         # Page, hero, typography, account panel
│               ├── search-form.css    # Search form, themes, call to action
│               ├── results.css        # Results layout, summary, history, meta, guidance
│               ├── cards.css          # Option cards, markdown, banners, skeletons
│               └── responsive.css     # Media queries
│
├── infra/
│   ├── docker/                        # backend.Dockerfile, frontend.Dockerfile
│   └── postgres/init/                 # Init SQL scripts for local Postgres
├── docs/                              # Project documentation
├── .github/workflows/ci.yml           # Backend (ruff, mypy, pytest) and frontend (eslint, prettier, build)
├── docker-compose.yml                 # Postgres, backend, frontend
├── Makefile                           # Dev commands (see README)
└── .env.example                       # Environment template
```

## Backend layering

`api` -> `application` / `domain` -> `infrastructure`

- `api` owns HTTP: routers, schemas, mapping to application inputs.
- `application` owns use cases and talks to the outside world only through `ports`.
- `domain` holds entities and pure rules.
- `infrastructure` implements ports (database, OpenAI, Travelpayouts).
