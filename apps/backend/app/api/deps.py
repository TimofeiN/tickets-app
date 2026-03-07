from __future__ import annotations

from app.application.services.ranking_service import RankingService
from app.application.services.search_service import SearchService
from app.infrastructure.db.repositories.iata_city_repository import IataCityRepository
from app.infrastructure.providers.openai_provider import OpenAIProvider
from app.infrastructure.providers.travelpayouts_provider import TravelpayoutsProvider


def get_search_service() -> SearchService:
    return SearchService(
        flight_provider=TravelpayoutsProvider.from_env(),
        city_resolver=IataCityRepository(),
        ranking_service_factory=lambda: RankingService(OpenAIProvider.from_env()),
    )
