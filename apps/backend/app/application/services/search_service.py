from __future__ import annotations

import logging

from app.application.dto.search_pipeline import (
    FactualShortlistedOption,
    FinalRankedOption,
    SemanticScoringStepResult,
    ShortlistStepResult,
)
from app.application.dto.search_result import (
    SearchGuidanceResult,
    SearchMetaResult,
    SearchOptionResult,
    SearchResult,
)
from app.application.ports.city_resolver import CityResolver
from app.application.ports.flight_search_provider import FlightSearchProvider, FlightSearchResult
from app.application.ports.llm_provider import LLMProvider
from app.application.ports.origin_airport_resolver import OriginAirportResolver
from app.application.services.enrichment_service import (
    CandidateTripPlan,
    EnrichmentService,
)
from app.application.services.factual_shortlist_service import (
    FactualShortlistService,
    build_factual_reason,
)
from app.application.services.final_ranking_service import FinalRankingService
from app.application.services.flight_candidates_service import FlightCandidatesService
from app.application.services.semantic_scoring_service import SemanticScoringService
from app.core.errors import DataAccessError, LLMConfigurationError, LLMError
from app.core.metrics import log_search_degradation_metrics
from app.domain.models.trip_preferences import TripPreferences
from app.shared.enums import EnrichmentMode, RankingMode

RANKED_CANDIDATES_TOP_K = 3

logger = logging.getLogger(__name__)


def _append_degradation_reason(
    public_reasons: list[str],
    internal_reasons: list[str],
    *,
    public_reason: str,
    internal_reason: str,
) -> None:
    public_reasons.append(public_reason)
    internal_reasons.append(internal_reason)


class LLMErrorHandler:
    @staticmethod
    def handle(
        exc: LLMError,
        *,
        log_prefix: str,
        internal_prefix: str,
        public_reason: str,
        fallback_reasons: list[str],
        internal_fallback_reasons: list[str],
    ) -> None:
        if isinstance(exc, LLMConfigurationError):
            logger.info("%s_disabled reason=%s", log_prefix, str(exc))
            _append_degradation_reason(
                fallback_reasons,
                internal_fallback_reasons,
                public_reason=public_reason,
                internal_reason=f"{internal_prefix} disabled: {exc!s}",
            )
            return

        logger.warning("%s_fallback cause=%s", log_prefix, str(exc))
        _append_degradation_reason(
            fallback_reasons,
            internal_fallback_reasons,
            public_reason=public_reason,
            internal_reason=f"{internal_prefix} fallback: {exc!s}",
        )


class SearchService:
    def __init__(
        self,
        *,
        flight_provider: FlightSearchProvider,
        origin_airport_resolver: OriginAirportResolver,
        city_resolver: CityResolver,
        semantic_scoring_provider: LLMProvider,
        enrichment_provider: LLMProvider,
    ) -> None:
        self.flight_provider = flight_provider
        self.origin_airport_resolver = origin_airport_resolver
        self.city_resolver = city_resolver
        self.semantic_scoring_provider = semantic_scoring_provider
        self.enrichment_provider = enrichment_provider

    def search(self, preferences: TripPreferences) -> SearchResult:
        tickets_result = self._fetch_candidates(preferences)
        fallback_reasons: list[str] = []
        internal_fallback_reasons: list[str] = []

        shortlist_result = self._build_shortlist(
            tickets_result=tickets_result,
            preferences=preferences,
        )

        self._resolve_city_names(
            shortlist=shortlist_result.shortlist,
            fallback_reasons=fallback_reasons,
            internal_fallback_reasons=internal_fallback_reasons,
        )

        semantic_scores, ranking_mode = self._score_shortlist(
            preferences=preferences,
            shortlist=shortlist_result.shortlist,
            fallback_reasons=fallback_reasons,
            internal_fallback_reasons=internal_fallback_reasons,
        )
        selected_candidates = self._rank_and_select(
            shortlist=shortlist_result.shortlist,
            semantic_scoring_result=semantic_scores,
        )

        trip_plans, enrichment_mode = self._enrich_selected(
            preferences=preferences,
            selected_candidates=selected_candidates,
            fallback_reasons=fallback_reasons,
            internal_fallback_reasons=internal_fallback_reasons,
        )

        options = self._build_options(
            selected_candidates=selected_candidates,
            trip_plans=trip_plans,
        )

        self._log_degradation_metrics(
            tickets_result=tickets_result,
            ranking_mode=ranking_mode,
            internal_fallback_reasons=internal_fallback_reasons,
        )

        return self._build_search_result(
            tickets_result=tickets_result,
            options=options,
            ranking_mode=ranking_mode,
            enrichment_mode=enrichment_mode,
            fallback_reasons=fallback_reasons,
        )

    def _fetch_candidates(self, preferences: TripPreferences) -> FlightSearchResult:
        origin_airports = FlightCandidatesService.resolve_origin_airports(
            origin_city=preferences.origin_city,
            origin_airport_resolver=self.origin_airport_resolver,
        )
        provider_result = self.flight_provider.get_offers(
            preferences,
            origin_airports=origin_airports,
        )
        candidates = FlightCandidatesService.build_candidates_from_offers(
            offers=provider_result.offers,
        )
        deduplicated = FlightCandidatesService.deduplicate_candidates(candidates)
        return FlightSearchResult(
            candidates=deduplicated,
            source=provider_result.source,
        )

    @staticmethod
    def _build_shortlist(
        *,
        tickets_result: FlightSearchResult,
        preferences: TripPreferences,
    ) -> ShortlistStepResult:
        shortlist = FactualShortlistService.build(
            tickets_result.candidates,
            preferences,
        )
        return ShortlistStepResult(
            shortlist=shortlist,
        )

    def _score_shortlist(
        self,
        *,
        preferences: TripPreferences,
        shortlist: list[FactualShortlistedOption],
        fallback_reasons: list[str],
        internal_fallback_reasons: list[str],
    ) -> tuple[SemanticScoringStepResult, RankingMode]:
        semantic_scores = SemanticScoringStepResult(scores=[])
        ranking_mode = RankingMode.deterministic
        try:
            semantic_scores = SemanticScoringService.score(
                llm_provider=self.semantic_scoring_provider,
                preferences=preferences,
                shortlist=shortlist,
            )
            ranking_mode = RankingMode.llm
            logger.info(
                "semantic_scoring_succeeded shortlist_size=%s selected=%s",
                len(shortlist),
                sorted(item.option_id for item in semantic_scores.scores),
            )
        except LLMError as exc:
            LLMErrorHandler.handle(
                exc,
                log_prefix="semantic_scoring",
                internal_prefix="semantic scoring",
                public_reason="ranking_unavailable",
                fallback_reasons=fallback_reasons,
                internal_fallback_reasons=internal_fallback_reasons,
            )
        return semantic_scores, ranking_mode

    @staticmethod
    def _rank_and_select(
        *,
        shortlist: list[FactualShortlistedOption],
        semantic_scoring_result: SemanticScoringStepResult,
    ) -> list[FinalRankedOption]:
        ranked_candidates = FinalRankingService.rank(shortlist, semantic_scoring_result)
        return ranked_candidates[:RANKED_CANDIDATES_TOP_K]

    def _resolve_city_names(
        self,
        *,
        shortlist: list[FactualShortlistedOption],
        fallback_reasons: list[str],
        internal_fallback_reasons: list[str],
    ) -> None:
        iata_codes = [item.candidate.destination_airport for item in shortlist]

        try:
            resolved_city_names = self.city_resolver.resolve_city_names(iata_codes)
            city_names_by_iata = {
                item.iata_code.upper(): item.city_name for item in resolved_city_names
            }
            for item in shortlist:
                candidate = item.candidate
                candidate.resolved_city_name = city_names_by_iata.get(
                    candidate.destination_airport,
                    "",
                )
        except DataAccessError as exc:
            logger.warning("city_resolver_fallback cause=%s", str(exc))
            _append_degradation_reason(
                fallback_reasons,
                internal_fallback_reasons,
                public_reason="city_names_unavailable",
                internal_reason=f"city resolver fallback: {exc!s}",
            )

    def _enrich_selected(
        self,
        *,
        preferences: TripPreferences,
        selected_candidates: list[FinalRankedOption],
        fallback_reasons: list[str],
        internal_fallback_reasons: list[str],
    ) -> tuple[list[CandidateTripPlan], EnrichmentMode]:
        trip_plans: list[CandidateTripPlan] = []
        enrichment_mode = EnrichmentMode.unavailable
        if not selected_candidates:
            return trip_plans, enrichment_mode

        try:
            trip_plans = EnrichmentService.enrich_selected(
                self.enrichment_provider,
                selected_candidates=selected_candidates,
                themes=preferences.themes,
                max_workers=RANKED_CANDIDATES_TOP_K,
            )
            enrichment_mode = EnrichmentMode.llm
        except LLMError as exc:
            LLMErrorHandler.handle(
                exc,
                log_prefix="llm_enrichment",
                internal_prefix="llm enrichment",
                public_reason="enrichment_unavailable",
                fallback_reasons=fallback_reasons,
                internal_fallback_reasons=internal_fallback_reasons,
            )
        return trip_plans, enrichment_mode

    @staticmethod
    def _build_options(
        *,
        selected_candidates: list[FinalRankedOption],
        trip_plans: list[CandidateTripPlan],
    ) -> list[SearchOptionResult]:
        trip_plans_by_option_id = {item.option_id: item.trip_plan for item in trip_plans}
        options: list[SearchOptionResult] = []
        for item in selected_candidates:
            candidate = item.candidate
            option_id = candidate.option_id
            destination_city = candidate.resolved_city_name or candidate.destination_city
            reason = item.reason_short or build_factual_reason(candidate)
            trip_plan = trip_plans_by_option_id.get(option_id, "")

            option = SearchOptionResult(
                option_id=option_id,
                destination_city=destination_city,
                origin_airport=candidate.origin_airport,
                destination_airport=candidate.destination_airport,
                price_usd=candidate.price_usd,
                score=item.final_score,
                reason=reason,
                trip_plan=trip_plan,
            )
            options.append(option)
        return options

    @staticmethod
    def _log_degradation_metrics(
        *,
        tickets_result: FlightSearchResult,
        ranking_mode: RankingMode,
        internal_fallback_reasons: list[str],
    ) -> None:
        log_search_degradation_metrics(
            data_source=tickets_result.source,
            ranking_mode=ranking_mode,
            fallback_reasons=internal_fallback_reasons,
        )

    @staticmethod
    def _build_search_result(
        *,
        tickets_result: FlightSearchResult,
        options: list[SearchOptionResult],
        ranking_mode: RankingMode,
        enrichment_mode: EnrichmentMode,
        fallback_reasons: list[str],
    ) -> SearchResult:
        guidance = SearchGuidanceResult(
            improvement_hint="",
            counterfactual="",
        )
        meta = SearchMetaResult(
            data_source=tickets_result.source,
            ranking_mode=ranking_mode,
            enrichment_mode=enrichment_mode,
            fallback_reasons=fallback_reasons,
        )
        trip_plan = options[0].trip_plan if options else ""

        return SearchResult(
            options=options,
            guidance=guidance,
            meta=meta,
            trip_plan=trip_plan,
        )
