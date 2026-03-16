apps/backend/
  pyproject.toml
  alembic.ini

  app/
    main.py  # FastAPI entrypoint: app init, logging, middleware, routers
    middleware.py  # Shared middleware setup (currently CORS)

    api/
      deps.py  # DI factories for application services/adapters
      mappers/
        trip_preferences_mapper.py  # SearchRequest -> TripPreferences mapper
      routers/
        health.py  # Liveness endpoint
        search.py  # POST /search endpoint and HTTP boundary mapping
      schemas/
        search_request.py  # Input validation models
        search_response.py  # Output models and response mapper

	    application/
	      dto/
	        search_pipeline.py  # Internal DTOs for factual shortlist and semantic/final ranking
	        search_result.py  # Use-case output DTO returned by SearchService
	      ports/
	        city_resolver.py  # Destination city-name resolver contract
	        flight_search_provider.py  # Flight provider contract
	        llm_provider.py  # LLM provider contract
	        origin_airport_resolver.py  # Origin city -> airport list resolver contract
	      services/
	        factual_shortlist_service.py  # Factual filtering, deduplication, and shortlist scoring
	        final_ranking_service.py  # Combines factual and semantic signals
	        semantic_scoring_service.py  # LLM semantic scoring for shortlist options
	        search_service.py  # Search orchestration and fallback/degradation handling

    core/
      config.py  # Env-based configuration accessors
      errors.py  # Shared typed exceptions
      logging.py  # Logging configuration
      metrics.py  # Search degradation metric-like log emitters

    domain/
	      models/
	        flight_candidate.py  # Domain flight option entity
	        trip_preferences.py  # Domain search preferences entity
	      services/
	        filtering.py  # Budget/date filtering rules

    infrastructure/
      db/
        models/
          iata_city_map.py  # SQLModel table for IATA -> city mapping
        repositories/
          iata_city_repository.py  # DB-backed CityResolver adapter
          origin_airport_repository.py  # DB-backed OriginAirportResolver adapter
        session.py  # SQLAlchemy/SQLModel engine and session helpers
      providers/
        openai_provider.py  # External LLM API adapter
        travelpayouts_provider.py  # External flight API adapter with async fan-out and fallback dataset

    shared/
      enums.py  # Shared enums used across API/application/domain boundaries

  alembic/  # Alembic runtime env/config & migrations
    env.py
    versions/
      20260307_0001_create_iata_city_map.py

  scripts/
    sync_iata_city_map.py  # Pull + upsert IATA/city dataset into DB

  tests/
