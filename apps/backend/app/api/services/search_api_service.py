from __future__ import annotations

import hashlib
import logging

from app.api.mappers.trip_preferences_mapper import to_trip_preferences
from app.api.schemas.search.reaction import SuggestionReactionResponse
from app.api.schemas.search.request import SearchRequest
from app.api.schemas.search.response import (
    FlightOption,
    SearchGuidance,
    SearchMeta,
    SearchResponse,
)
from app.application.services.auth_service import AuthenticatedUser
from app.application.services.search_service import SearchService
from app.core.errors import DataAccessError
from app.infrastructure.db.repositories.saved_search_repository import SavedSearchRepository
from app.infrastructure.db.repositories.trip_suggestion_repository import (
    TripSuggestionOptionData,
    TripSuggestionRepository,
)
from app.shared.enums import EnrichmentMode, RankingMode, ReactionType, SearchDataSource

logger = logging.getLogger(__name__)


class SearchApiService:
    def __init__(
        self,
        *,
        search_service: SearchService,
        saved_search_repository: SavedSearchRepository,
        trip_suggestion_repository: TripSuggestionRepository,
    ) -> None:
        self.search_service = search_service
        self.saved_search_repository = saved_search_repository
        self.trip_suggestion_repository = trip_suggestion_repository

    def run_search(
        self,
        *,
        payload: SearchRequest,
        current_user: AuthenticatedUser | None,
    ) -> SearchResponse:
        strict_dates = payload.strict_dates
        if strict_dates is None:
            logger.warning("search_payload_invalid reason=missing_strict_dates")
            return SearchResponse(
                options=[],
                guidance=SearchGuidance(),
                meta=SearchMeta(
                    data_source=SearchDataSource.fallback,
                    ranking_mode=RankingMode.deterministic,
                    enrichment_mode=EnrichmentMode.unavailable,
                    fallback_reasons=["invalid_dates_payload"],
                ),
                trip_plan="",
            )

        query_key = self._build_query_key(payload)
        cached_response = self._load_cached_response(query_key=query_key)
        if cached_response is not None:
            self._persist_saved_search(
                payload=payload,
                response=cached_response,
                current_user=current_user,
            )
            return cached_response

        preferences = to_trip_preferences(payload)
        result = self.search_service.search(preferences)
        response = SearchResponse.from_contract(result)

        self._persist_trip_suggestions(
            query_key=query_key,
            payload=payload,
            response=response,
        )

        self._persist_saved_search(
            payload=payload,
            response=response,
            current_user=current_user,
        )
        return response

    def react_to_suggestion(
        self,
        *,
        suggestion_id: str,
        reaction: ReactionType,
        current_user: AuthenticatedUser,
    ) -> SuggestionReactionResponse:
        suggestion = self.trip_suggestion_repository.record_reaction(
            user_id=current_user.id,
            suggestion_id=suggestion_id,
            reaction=reaction,
        )
        return SuggestionReactionResponse(
            suggestion_id=suggestion.id,
            reaction=reaction,
            likes=suggestion.likes,
            dislikes=suggestion.dislikes,
        )

    @staticmethod
    def _build_query_key(payload: SearchRequest) -> str:
        strict_dates = payload.strict_dates
        if strict_dates is None:
            raise ValueError("strict_dates is required for query key")
        themes = ",".join(sorted(theme.value for theme in payload.themes))
        origin = payload.origin_city.strip().lower()
        raw_key = (
            f"{origin}|{strict_dates.start_date.isoformat()}|{strict_dates.end_date.isoformat()}|"
            f"{payload.budget_usd}|{payload.travelers_count}|{themes}"
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def _load_cached_response(self, *, query_key: str) -> SearchResponse | None:
        try:
            cached_options = self.trip_suggestion_repository.list_top_for_query(query_key=query_key)
        except DataAccessError as exc:
            logger.warning("trip_suggestion_cache_lookup_failed reason=%s", str(exc))
            return None

        if not cached_options:
            return None

        options = [
            FlightOption(
                option_id=item.option_id,
                suggestion_id=item.id,
                destination_city=item.destination_city,
                origin_airport=item.origin_airport,
                destination_airport=item.destination_airport,
                price_usd=item.price_usd,
                score=item.score,
                reason=item.reason,
                trip_plan=item.trip_plan,
                likes=item.likes,
                dislikes=item.dislikes,
            )
            for item in cached_options
        ]
        return SearchResponse(
            options=options,
            guidance=SearchGuidance(),
            meta=SearchMeta(
                data_source=SearchDataSource.fallback,
                ranking_mode=RankingMode.deterministic,
                enrichment_mode=EnrichmentMode.unavailable,
                fallback_reasons=[],
            ),
            trip_plan=options[0].trip_plan if options else "",
        )

    def _persist_trip_suggestions(
        self,
        *,
        query_key: str,
        payload: SearchRequest,
        response: SearchResponse,
    ) -> None:
        strict_dates = payload.strict_dates
        if strict_dates is None or not response.options:
            return

        options = [
            TripSuggestionOptionData(
                option_id=item.option_id,
                destination_city=item.destination_city,
                origin_airport=item.origin_airport,
                destination_airport=item.destination_airport,
                price_usd=item.price_usd,
                score=item.score,
                reason=item.reason,
                trip_plan=item.trip_plan,
            )
            for item in response.options
        ]

        try:
            saved = self.trip_suggestion_repository.save_suggestions(
                query_key=query_key,
                origin_city=payload.origin_city,
                start_date=strict_dates.start_date,
                end_date=strict_dates.end_date,
                budget_usd=payload.budget_usd,
                travelers_count=payload.travelers_count,
                themes=[theme.value for theme in payload.themes],
                options=options,
            )
        except DataAccessError as exc:
            logger.warning("trip_suggestion_cache_save_failed reason=%s", str(exc))
            return

        saved_by_option_id = {item.option_id: item for item in saved}
        for option in response.options:
            saved_option = saved_by_option_id.get(option.option_id)
            if saved_option is None:
                continue
            option.suggestion_id = saved_option.id
            option.likes = saved_option.likes
            option.dislikes = saved_option.dislikes

    def _persist_saved_search(
        self,
        *,
        payload: SearchRequest,
        response: SearchResponse,
        current_user: AuthenticatedUser | None,
    ) -> None:
        if current_user is None:
            return
        strict_dates = payload.strict_dates
        if strict_dates is None:
            logger.warning("saved_search_persist_skipped reason=missing_strict_dates")
            return

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
            return

        response.saved_search_id = saved_search.id
