from __future__ import annotations

from app.application.services.ranking_service import RankingService
from app.application.services.search_service import SearchService
from app.infrastructure.db.repositories.iata_city_repository import IataCityRepository
from app.infrastructure.db.repositories.origin_airport_repository import OriginAirportRepository
from app.infrastructure.providers.openai_provider import OpenAIProvider
from app.infrastructure.providers.travelpayouts_provider import TravelpayoutsProvider


def get_search_service() -> SearchService:
    origin_airport_repository = OriginAirportRepository()
    flight_provider = TravelpayoutsProvider.from_env(
        origin_airport_resolver=origin_airport_repository.resolve_airports
    )
    return SearchService(
        flight_provider=flight_provider,
        city_resolver=IataCityRepository(),
        ranking_service_factory=lambda: RankingService(OpenAIProvider.from_env()),
    )
