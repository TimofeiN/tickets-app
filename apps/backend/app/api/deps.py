from __future__ import annotations

from app.application.services.search_service import SearchService
from app.infrastructure.db.repositories.iata_city_repository import IataCityRepository
from app.infrastructure.db.repositories.origin_airport_repository import OriginAirportRepository
from app.infrastructure.providers.openai_provider import OpenAIProvider
from app.infrastructure.providers.travelpayouts_provider import TravelpayoutsProvider


def get_search_service() -> SearchService:
    origin_airport_resolver = OriginAirportRepository()
    city_resolver = IataCityRepository()
    flight_provider = TravelpayoutsProvider.from_settings()
    llm_provider = OpenAIProvider.from_settings()

    return SearchService(
        flight_provider=flight_provider,
        origin_airport_resolver=origin_airport_resolver,
        city_resolver=city_resolver,
        semantic_scoring_provider=llm_provider,
        enrichment_provider=llm_provider,
    )
