from __future__ import annotations

import json

from pydantic import Field, ValidationError

from app.application.ports.llm_provider import LLMProvider
from app.core.errors import DomainInvariantError, LLMResponseValidationError
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.ranking_result import RankedOption, RankingResult
from app.domain.models.trip_preferences import TripPreferences
from app.shared.enums import DatesMode
from app.shared.strict_model import StrictModel


class _RankedOptionSchema(StrictModel):
    option_id: str = Field(min_length=1, description="Selected option identifier.")
    reason: str = Field(
        min_length=1,
        max_length=240,
        description="Short reason for this ranking.",
    )


class _LLMRankingOutputSchema(StrictModel):
    ranked_options: list[_RankedOptionSchema] = Field(
        min_length=3,
        max_length=3,
        description="Exactly three ranked options.",
    )


class RankingService:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    def rank(
        self,
        preferences: TripPreferences,
        shortlist: list[FlightCandidate],
    ) -> RankingResult:
        if len(shortlist) < 3:
            raise LLMResponseValidationError("shortlist must have at least 3 options")

        raw_output = self.llm_provider.complete(
            system_prompt=(
                "Rank travel options. Return strict JSON with exactly 3 ranked options. "
                "Only use option_id values from the shortlist."
            ),
            user_prompt=json.dumps(
                _build_compact_ranking_context(preferences, shortlist),
                ensure_ascii=True,
            ),
            output_model=_LLMRankingOutputSchema,
        )

        try:
            parsed = _LLMRankingOutputSchema.model_validate_json(raw_output)
        except ValidationError as exc:
            raise LLMResponseValidationError("llm output failed schema validation") from exc

        allowed_ids = {candidate.option_id for candidate in shortlist}
        ranked_ids = [item.option_id for item in parsed.ranked_options]
        if len(set(ranked_ids)) != 3:
            raise LLMResponseValidationError("llm returned duplicate option ids")
        if any(option_id not in allowed_ids for option_id in ranked_ids):
            raise LLMResponseValidationError("llm returned unknown option ids")

        return RankingResult(
            ranked_options=(
                RankedOption(
                    option_id=parsed.ranked_options[0].option_id,
                    reason=parsed.ranked_options[0].reason,
                ),
                RankedOption(
                    option_id=parsed.ranked_options[1].option_id,
                    reason=parsed.ranked_options[1].reason,
                ),
                RankedOption(
                    option_id=parsed.ranked_options[2].option_id,
                    reason=parsed.ranked_options[2].reason,
                ),
            )
        )


def build_shortlist_for_llm(
    deterministic_sorted_candidates: list[FlightCandidate],
    all_candidates: list[FlightCandidate],
    limit: int,
) -> list[FlightCandidate]:
    clamped_limit = max(3, min(limit, 12))
    shortlist = list(deterministic_sorted_candidates[:clamped_limit])
    selected_ids = {candidate.option_id for candidate in shortlist}

    for candidate in sorted(all_candidates, key=lambda item: item.price_usd):
        if len(shortlist) >= clamped_limit:
            break
        if candidate.option_id in selected_ids:
            continue
        shortlist.append(candidate)
        selected_ids.add(candidate.option_id)

    return shortlist


def _build_compact_ranking_context(
    preferences: TripPreferences,
    shortlist: list[FlightCandidate],
) -> dict[str, object]:
    budget_per_traveler = round(preferences.budget_usd / preferences.travelers_count, 2)
    dates_payload: dict[str, object]
    if preferences.dates_mode == DatesMode.strict:
        if preferences.strict_start_date is None or preferences.strict_end_date is None:
            raise DomainInvariantError("strict dates are required for strict mode")
        dates_payload = {
            "mode": "strict",
            "start_date": preferences.strict_start_date.isoformat(),
            "end_date": preferences.strict_end_date.isoformat(),
        }
    else:
        if (
            preferences.flexible_year is None
            or preferences.flexible_month is None
            or preferences.flexible_trip_length_days is None
        ):
            raise DomainInvariantError("flexible dates payload is incomplete")
        dates_payload = {
            "mode": "flexible",
            "year": preferences.flexible_year,
            "month": preferences.flexible_month,
            "trip_length_days": preferences.flexible_trip_length_days,
        }

    return {
        "request": {
            "origin_city": preferences.origin_city,
            "themes": sorted(preferences.themes),
            "budget_per_traveler_usd": budget_per_traveler,
            "dates": dates_payload,
        },
        "shortlist": [
            {
                "option_id": candidate.option_id,
                "destination_city": candidate.destination_city,
                "destination_airport": candidate.destination_airport,
                "price_usd": candidate.price_usd,
                "trip_length_days": (candidate.return_date - candidate.departure_date).days,
                "themes": sorted(candidate.themes),
            }
            for candidate in shortlist
        ],
    }
