from __future__ import annotations

import logging
from collections.abc import Callable

from app.application.dto.search_result import (
    SearchGuidanceResult,
    SearchMetaResult,
    SearchOptionResult,
    SearchResult,
)
from app.application.ports.city_resolver import CityResolver
from app.application.ports.flight_search_provider import FlightSearchProvider
from app.application.ports.llm_provider import LLMConfigurationError, LLMProviderError
from app.application.services.enrichment_service import (
    EnrichmentContext,
    EnrichmentService,
    build_empty_enrichment,
)
from app.application.services.ranking_service import (
    LLMResponseValidationError,
    RankingService,
    build_shortlist_for_llm,
)
from app.core.errors import DataAccessError, LLMRankingError
from app.core.metrics import log_search_degradation_metrics
from app.core.settings import settings
from app.domain.models.trip_preferences import TripPreferences
from app.domain.services.filtering import filter_candidates
from app.domain.services.scoring import (
    build_reason,
    pick_with_fallback,
    score_candidate,
    sort_candidates,
)
from app.shared.enums import EnrichmentMode, RankingMode, SearchDataSource

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        *,
        flight_provider: FlightSearchProvider,
        city_resolver: CityResolver,
        ranking_service_factory: Callable[[], RankingService],
        enrichment_service_factory: Callable[[], EnrichmentService],
        shortlist_limit: int | None = None,
    ) -> None:
        self.flight_provider = flight_provider
        self.city_resolver = city_resolver
        self.ranking_service_factory = ranking_service_factory
        self.enrichment_service_factory = enrichment_service_factory
        self.shortlist_limit = (
            shortlist_limit if shortlist_limit is not None else settings.llm_shortlist_limit
        )

    def search(self, preferences: TripPreferences) -> SearchResult:
        provider_result = self.flight_provider.get_candidates(preferences)
        all_candidates = provider_result.candidates
        filtered_candidates = filter_candidates(all_candidates, preferences)
        deterministic_top3 = pick_with_fallback(filtered_candidates, all_candidates, preferences)
        filtered_ids = {candidate.option_id for candidate in filtered_candidates}
        fallback_reasons: list[str] = []
        if provider_result.source == SearchDataSource.fallback:
            fallback_reasons.append(
                f"provider fallback: {provider_result.fallback_reason or 'provider unavailable'}"
            )

        selected_candidates = deterministic_top3
        reasons_by_option_id: dict[str, str] = {}
        ranking_mode = RankingMode.deterministic
        enrichment_mode = EnrichmentMode.unavailable

        deterministic_sorted = sort_candidates(filtered_candidates, preferences)
        shortlist = build_shortlist_for_llm(
            deterministic_sorted,
            all_candidates,
            self.shortlist_limit,
        )

        try:
            ranking_service = self.ranking_service_factory()
            ranking_result = ranking_service.rank(preferences, shortlist)
            shortlisted_by_id = {candidate.option_id: candidate for candidate in shortlist}
            llm_ranked = [
                shortlisted_by_id[item.option_id]
                for item in ranking_result.ranked_options
                if item.option_id in shortlisted_by_id
            ]
            if len(llm_ranked) != 3:
                raise LLMResponseValidationError("LLM output cannot be mapped to 3 options")

            selected_candidates = llm_ranked
            reasons_by_option_id = {
                item.option_id: item.reason.strip()
                for item in ranking_result.ranked_options
                if item.reason.strip()
            }
            ranking_mode = RankingMode.llm
            logger.info(
                "llm_ranking_succeeded shortlist_size=%s selected=%s",
                len(shortlist),
                [candidate.option_id for candidate in selected_candidates],
            )
        except LLMConfigurationError as exc:
            logger.info("llm_ranking_disabled reason=%s", str(exc))
            fallback_reasons.append(f"llm disabled: {str(exc)}")
        except (LLMResponseValidationError, LLMProviderError, LLMRankingError) as exc:
            logger.warning("llm_ranking_fallback cause=%s", str(exc))
            fallback_reasons.append(f"llm fallback: {str(exc)}")

        try:
            city_names_by_iata = self.city_resolver.resolve_city_names(
                [candidate.destination_airport for candidate in selected_candidates]
            )
        except DataAccessError as exc:
            logger.warning("city_resolver_fallback cause=%s", str(exc))
            fallback_reasons.append(f"city resolver fallback: {str(exc)}")
            city_names_by_iata = {}

        constraints_relaxed = any(
            candidate.option_id not in filtered_ids for candidate in selected_candidates
        )
        enrichment_context = EnrichmentContext(
            selected_count=len(selected_candidates),
            filtered_count=len(filtered_candidates),
            constraints_relaxed=constraints_relaxed,
            data_source=provider_result.source.value,
            ranking_mode=ranking_mode.value,
        )

        try:
            enrichment_service = self.enrichment_service_factory()
            enrichment_result = enrichment_service.enrich(
                preferences,
                selected_candidates,
                enrichment_context,
            )
            enrichment_mode = EnrichmentMode.llm
        except LLMConfigurationError as exc:
            logger.info("llm_enrichment_disabled reason=%s", str(exc))
            fallback_reasons.append(f"llm enrichment disabled: {str(exc)}")
            enrichment_result = build_empty_enrichment(
                preferences,
                selected_candidates,
                enrichment_context,
            )
        except (LLMResponseValidationError, LLMProviderError, LLMRankingError) as exc:
            logger.warning("llm_enrichment_fallback cause=%s", str(exc))
            fallback_reasons.append(f"llm enrichment fallback: {str(exc)}")
            enrichment_result = build_empty_enrichment(
                preferences,
                selected_candidates,
                enrichment_context,
            )

        options = [
            SearchOptionResult(
                option_id=candidate.option_id,
                destination_city=city_names_by_iata.get(
                    candidate.destination_airport.upper(),
                    candidate.destination_city,
                ),
                origin_airport=candidate.origin_airport,
                destination_airport=candidate.destination_airport,
                price_usd=candidate.price_usd,
                score=score_candidate(candidate, preferences),
                reason=reasons_by_option_id.get(
                    candidate.option_id,
                    build_reason(candidate, preferences),
                ),
                theme_explanation=enrichment_result.insights_by_option_id[
                    candidate.option_id
                ].theme_explanation,
                highlights=enrichment_result.insights_by_option_id[candidate.option_id].highlights,
                tradeoff=enrichment_result.insights_by_option_id[candidate.option_id].tradeoff,
                caveat=enrichment_result.insights_by_option_id[candidate.option_id].caveat,
                trip_style=enrichment_result.insights_by_option_id[candidate.option_id].trip_style,
                vibe=enrichment_result.insights_by_option_id[candidate.option_id].vibe,
            )
            for candidate in selected_candidates
        ]
        if constraints_relaxed:
            fallback_reasons.append(
                "constraints relaxed: included options outside budget/date filters"
            )
        log_search_degradation_metrics(
            data_source=provider_result.source,
            ranking_mode=ranking_mode,
            constraints_relaxed=constraints_relaxed,
            fallback_reasons=fallback_reasons,
        )
        return SearchResult(
            options=options,
            guidance=SearchGuidanceResult(
                improvement_hint=enrichment_result.guidance.improvement_hint,
                counterfactual=enrichment_result.guidance.counterfactual,
            ),
            meta=SearchMetaResult(
                data_source=provider_result.source,
                ranking_mode=ranking_mode,
                enrichment_mode=enrichment_mode,
                constraints_relaxed=constraints_relaxed,
                fallback_reasons=fallback_reasons,
            ),
        )
