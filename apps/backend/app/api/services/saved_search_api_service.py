from __future__ import annotations

from datetime import datetime

from app.api.schemas.search.saved import (
    SavedSearchDetailResponse,
    SavedSearchSummaryResponse,
)
from app.application.services.auth_service import AuthenticatedUser
from app.core.errors import DataAccessError, SavedSearchNotFoundError
from app.infrastructure.db.models.saved_search import SavedSearch
from app.infrastructure.db.repositories.saved_search_repository import SavedSearchRepository


class SavedSearchApiService:
    def __init__(self, *, repository: SavedSearchRepository) -> None:
        self.repository = repository

    def list_saved_searches(
        self,
        *,
        current_user: AuthenticatedUser,
    ) -> list[SavedSearchSummaryResponse]:
        return [
            self._to_summary_response(item)
            for item in self.repository.list_for_user(user_id=current_user.id)
        ]

    def get_saved_search(
        self,
        *,
        current_user: AuthenticatedUser,
        saved_search_id: str,
    ) -> SavedSearchDetailResponse:
        saved_search = self.repository.find_for_user(
            user_id=current_user.id,
            saved_search_id=saved_search_id,
        )
        if saved_search is None:
            raise SavedSearchNotFoundError("saved search not found")
        return self._to_detail_response(saved_search)

    @staticmethod
    def _to_summary_response(saved_search: SavedSearch) -> SavedSearchSummaryResponse:
        created_at = saved_search.created_at
        if not isinstance(created_at, datetime):
            raise DataAccessError("saved search created_at is missing or invalid")
        return SavedSearchSummaryResponse(
            id=saved_search.id,
            created_at=created_at,
            origin_city=saved_search.origin_city,
            start_date=saved_search.start_date,
            end_date=saved_search.end_date,
            budget_usd=saved_search.budget_usd,
            themes=saved_search.themes,
            summary_destination=saved_search.summary_destination,
            summary_price_usd=saved_search.summary_price_usd,
            options_count=saved_search.options_count,
        )

    def _to_detail_response(self, saved_search: SavedSearch) -> SavedSearchDetailResponse:
        summary = self._to_summary_response(saved_search)
        return SavedSearchDetailResponse(
            **summary.model_dump(),
            request_payload=saved_search.request_payload,
            response_payload=saved_search.response_payload,
        )
