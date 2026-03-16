from __future__ import annotations

from app.application.dto.search_pipeline import FactualShortlistedOption
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences
from app.domain.services.filtering import filter_candidates

DEFAULT_SHORTLIST_LIMIT = 3


class FactualShortlistService:
    @classmethod
    def build(
        cls,
        candidates: list[FlightCandidate],
        preferences: TripPreferences,
        *,
        shortlist_limit: int | None = None,
    ) -> list[FactualShortlistedOption]:
        factual_shortlist_limit = shortlist_limit or DEFAULT_SHORTLIST_LIMIT
        filtered_candidates = filter_candidates(candidates, preferences)
        shortlisted = cls._deduplicate_and_rank(filtered_candidates, preferences)
        return shortlisted[:factual_shortlist_limit]

    @classmethod
    def _deduplicate_and_rank(
        cls,
        candidates: list[FlightCandidate],
        preferences: TripPreferences,
    ) -> list[FactualShortlistedOption]:
        best_by_destination: dict[str, FlightCandidate] = {}
        for candidate in candidates:
            key = candidate.destination_airport.upper()
            current = best_by_destination.get(key)
            if current is None or cls._candidate_sort_key(candidate) < cls._candidate_sort_key(
                current
            ):
                best_by_destination[key] = candidate

        shortlisted = [
            FactualShortlistedOption(
                candidate=candidate,
                factual_score=cls._score_candidate(candidate, preferences),
            )
            for candidate in best_by_destination.values()
        ]
        return sorted(
            shortlisted,
            key=lambda item: (
                item.factual_score,
                -item.candidate.price_usd,
                -(item.candidate.stops_count is not None),
                -(item.candidate.travel_time_minutes is not None),
            ),
            reverse=True,
        )

    @staticmethod
    def _candidate_sort_key(candidate: FlightCandidate) -> tuple[int, int, int]:
        return (
            candidate.price_usd,
            candidate.stops_count if candidate.stops_count is not None else 999,
            candidate.travel_time_minutes if candidate.travel_time_minutes is not None else 10**9,
        )

    @staticmethod
    def _score_candidate(candidate: FlightCandidate, preferences: TripPreferences) -> float:
        per_traveler_budget = preferences.budget_usd / preferences.travelers_count
        price_score = 1.0
        if per_traveler_budget > 0:
            price_score = max(
                0.0,
                min(1.0, 1.0 - (candidate.price_usd / per_traveler_budget) * 0.5),
            )

        component_scores = [price_score]
        if candidate.stops_count is not None:
            stops_penalty = min(candidate.stops_count, 3) * 0.25
            component_scores.append(max(0.0, 1.0 - stops_penalty))
        if candidate.travel_time_minutes is not None:
            normalized = (candidate.travel_time_minutes - 180) / 720
            component_scores.append(max(0.0, min(1.0, 1.0 - normalized)))

        return round(sum(component_scores) / len(component_scores), 2)


def build_factual_reason(candidate: FlightCandidate) -> str:
    details: list[str] = [f"Price ${candidate.price_usd} fits the current search window."]
    if candidate.stops_count is not None:
        if candidate.stops_count == 0:
            details.append("Non-stop routing improves convenience.")
        else:
            details.append(f"{candidate.stops_count} stop(s) in the current itinerary.")
    if candidate.travel_time_minutes is not None:
        details.append(f"Approximate total travel time is {candidate.travel_time_minutes} minutes.")
    return " ".join(details)
