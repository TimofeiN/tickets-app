from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.application.dto.search_pipeline import FinalRankedOption
from app.application.ports.llm_provider import LLMProvider


@dataclass(frozen=True)
class SearchEnrichment:
    trip_plan: str


@dataclass(frozen=True)
class CandidateTripPlan:
    option_id: str
    trip_plan: str


class EnrichmentService:
    @staticmethod
    def enrich(
        llm_provider: LLMProvider,
        *,
        city: str,
        num_days: int,
        themes: str,
    ) -> SearchEnrichment:
        if not city.strip() or num_days <= 0:
            return build_empty_enrichment()

        trip_plan = llm_provider.render_trip_summary(
            city=city.strip(),
            num_days=num_days,
            themes=themes.strip(),
        )
        return SearchEnrichment(trip_plan=trip_plan)

    @staticmethod
    def enrich_selected(
        llm_provider: LLMProvider,
        *,
        selected_candidates: list[FinalRankedOption],
        themes: tuple[str, ...],
        max_workers: int,
    ) -> list[CandidateTripPlan]:
        if not selected_candidates:
            return []

        normalized_themes = ", ".join(sorted(themes))
        tasks: list[tuple[str, str, int, str]] = []
        for item in selected_candidates:
            candidate = item.candidate
            tasks.append(
                (
                    candidate.option_id,
                    candidate.resolved_city_name or candidate.destination_city,
                    (candidate.return_date - candidate.departure_date).days,
                    normalized_themes,
                )
            )

        if len(tasks) == 1:
            return [EnrichmentService._enrich_one_candidate(llm_provider, tasks[0])]

        workers = min(len(tasks), max_workers) if max_workers > 0 else len(tasks)
        trip_plans: list[CandidateTripPlan] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for result in executor.map(
                lambda task: EnrichmentService._enrich_one_candidate(llm_provider, task),
                tasks,
            ):
                trip_plans.append(result)
        return trip_plans

    @staticmethod
    def _enrich_one_candidate(
        llm_provider: LLMProvider,
        task: tuple[str, str, int, str],
    ) -> CandidateTripPlan:
        option_id, city, num_days, themes = task
        enrichment_result = EnrichmentService.enrich(
            llm_provider,
            city=city,
            num_days=num_days,
            themes=themes,
        )
        return CandidateTripPlan(option_id=option_id, trip_plan=enrichment_result.trip_plan)


def build_empty_enrichment() -> SearchEnrichment:
    return SearchEnrichment(trip_plan="")
