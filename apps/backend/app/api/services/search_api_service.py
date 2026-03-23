from __future__ import annotations

import logging

from app.api.mappers.trip_preferences_mapper import to_trip_preferences
from app.api.schemas.search.request import SearchRequest
from app.api.schemas.search.response import SearchResponse
from app.application.services.auth_service import AuthenticatedUser
from app.application.services.search_service import SearchService
from app.core.errors import DataAccessError
from app.infrastructure.db.repositories.saved_search_repository import SavedSearchRepository

logger = logging.getLogger(__name__)


class SearchApiService:
    def __init__(
        self,
        *,
        search_service: SearchService,
        saved_search_repository: SavedSearchRepository,
    ) -> None:
        self.search_service = search_service
        self.saved_search_repository = saved_search_repository

    def run_search(
        self,
        *,
        payload: SearchRequest,
        current_user: AuthenticatedUser | None,
    ) -> SearchResponse:
        preferences = to_trip_preferences(payload)
        result = self.search_service.search(preferences)
        response = SearchResponse.from_contract(result)
        if current_user is None:
            return response

        strict_dates = payload.strict_dates
        if strict_dates is None:
            logger.warning("saved_search_persist_skipped reason=missing_strict_dates")
            return response

        request_payload = payload.model_dump(mode="json")
        response_payload = response.model_dump(mode="json")
        top_option = response.options[0] if response.options else None

        try:
            saved_search = self.saved_search_repository.create_saved_search(
                user_id=current_user.id,
                origin_city=payload.origin_city,
                start_date=strict_dates.start_date,
                end_date=strict_dates.end_date,
                budget_usd=payload.budget_usd,
                themes=[theme.value for theme in payload.themes],
                summary_destination=top_option.destination_city if top_option else None,
                summary_price_usd=top_option.price_usd if top_option else None,
                options_count=len(response.options),
                request_payload=request_payload,
                response_payload=response_payload,
            )
        except DataAccessError as exc:
            logger.warning(
                "saved_search_persist_skipped user_id=%s reason=%s",
                current_user.id,
                str(exc),
            )
            return response

        response.saved_search_id = saved_search.id
        return response
