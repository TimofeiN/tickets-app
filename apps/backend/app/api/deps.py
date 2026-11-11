from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlmodel import Session

from app.api.services.auth_api_service import AuthApiService
from app.api.services.saved_search_api_service import SavedSearchApiService
from app.api.services.search_api_service import SearchApiService
from app.application.services.auth_service import AuthenticatedUser, AuthService
from app.application.services.search_service import SearchService
from app.infrastructure.db.repositories.auth_repository import AuthRepository
from app.infrastructure.db.repositories.iata_city_repository import IataCityRepository
from app.infrastructure.db.repositories.origin_airport_repository import OriginAirportRepository
from app.infrastructure.db.repositories.saved_search_repository import SavedSearchRepository
from app.infrastructure.db.repositories.trip_suggestion_repository import TripSuggestionRepository
from app.infrastructure.db.session import get_db_session
from app.infrastructure.providers.openai_provider import OpenAIProvider
from app.infrastructure.providers.travelpayouts_provider import TravelpayoutsProvider


def get_origin_airport_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> OriginAirportRepository:
    return OriginAirportRepository(session=session)


def get_iata_city_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> IataCityRepository:
    return IataCityRepository(session=session)


def get_auth_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> AuthRepository:
    return AuthRepository(session=session)


def get_saved_search_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> SavedSearchRepository:
    return SavedSearchRepository(session=session)


def get_trip_suggestion_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> TripSuggestionRepository:
    return TripSuggestionRepository(session=session)


def get_search_service(
    origin_airport_resolver: Annotated[
        OriginAirportRepository, Depends(get_origin_airport_repository)
    ],
    city_resolver: Annotated[IataCityRepository, Depends(get_iata_city_repository)],
) -> SearchService:
    flight_provider = TravelpayoutsProvider.from_settings()
    llm_provider = OpenAIProvider.from_settings()
    return SearchService(
        flight_provider=flight_provider,
        origin_airport_resolver=origin_airport_resolver,
        city_resolver=city_resolver,
        semantic_scoring_provider=llm_provider,
        enrichment_provider=llm_provider,
    )


def get_auth_service(
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> AuthService:
    return AuthService(repository=repository)


def get_auth_api_service(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthApiService:
    return AuthApiService(auth_service=auth_service)


def get_saved_search_api_service(
    repository: Annotated[SavedSearchRepository, Depends(get_saved_search_repository)],
) -> SavedSearchApiService:
    return SavedSearchApiService(repository=repository)


def get_search_api_service(
    search_service: Annotated[SearchService, Depends(get_search_service)],
    saved_search_repository: Annotated[SavedSearchRepository, Depends(get_saved_search_repository)],
    trip_suggestion_repository: Annotated[
        TripSuggestionRepository, Depends(get_trip_suggestion_repository)
    ],
) -> SearchApiService:
    return SearchApiService(
        search_service=search_service,
        saved_search_repository=saved_search_repository,
        trip_suggestion_repository=trip_suggestion_repository,
    )


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def get_access_token(authorization: Annotated[str | None, Header()] = None) -> str | None:
    return _extract_bearer_token(authorization)


def get_optional_current_user(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    access_token: Annotated[str | None, Depends(get_access_token)] = None,
) -> AuthenticatedUser | None:
    return auth_service.authenticate_optional(access_token=access_token)


def get_current_user(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    access_token: Annotated[str | None, Depends(get_access_token)] = None,
) -> AuthenticatedUser:
    return auth_service.authenticate(access_token=access_token)
