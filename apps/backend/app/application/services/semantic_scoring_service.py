from __future__ import annotations

import json

from pydantic import Field

from app.application.dto.search_pipeline import (
    FactualShortlistedOption,
    SemanticScoreResult,
    SemanticScoringStepResult,
)
from app.application.ports.llm_provider import LLMProvider
from app.core.errors import DomainInvariantError, LLMResponseValidationError
from app.domain.models.trip_preferences import TripPreferences
from app.shared.enums import DatesMode
from app.shared.strict_model import StrictModel


class _SemanticScoreSchema(StrictModel):
    option_id: str = Field(min_length=1)
    theme_fit_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    matched_themes: list[str] = Field(max_length=5)
    reason_short: str = Field(min_length=1, max_length=180)


class _SemanticScoringOutputSchema(StrictModel):
    scores: list[_SemanticScoreSchema] = Field(min_length=1, max_length=12)


class SemanticScoringService:
    @classmethod
    def score(
        cls,
        llm_provider: LLMProvider,
        preferences: TripPreferences,
        shortlist: list[FactualShortlistedOption],
    ) -> SemanticScoringStepResult:
        if not shortlist:
            return SemanticScoringStepResult(scores=[])

        raw_output = llm_provider.complete(
            system_prompt=(
                "Score how well travel destinations fit user-selected themes. "
                "Return strict JSON only. "
                "Use modest confidence when the fit is uncertain. "
                "Do not invent route facts or hidden destination details. "
                "Score only the provided options and return each option exactly once."
            ),
            user_prompt=json.dumps(
                cls._build_semantic_scoring_context(
                    preferences,
                    shortlist,
                ),
                ensure_ascii=True,
            ),
            output_model=_SemanticScoringOutputSchema,
        )

        parsed = _SemanticScoringOutputSchema.model_validate_json(raw_output)

        allowed_ids = {item.candidate.option_id for item in shortlist}
        seen_ids: set[str] = set()
        scores: list[SemanticScoreResult] = []
        for item in parsed.scores:
            if item.option_id not in allowed_ids:
                raise LLMResponseValidationError("semantic scoring returned unknown option id")
            if item.option_id in seen_ids:
                raise LLMResponseValidationError("semantic scoring returned duplicate option id")
            seen_ids.add(item.option_id)
            scores.append(
                SemanticScoreResult(
                    option_id=item.option_id,
                    theme_fit_score=round(item.theme_fit_score, 2),
                    confidence=round(item.confidence, 2),
                    matched_themes=tuple(sorted(set(item.matched_themes))),
                    reason_short=item.reason_short.strip(),
                )
            )

        if len(scores) != len(shortlist):
            raise LLMResponseValidationError("semantic scoring did not return all options")

        return SemanticScoringStepResult(scores=scores)

    @staticmethod
    def _build_semantic_scoring_context(
        preferences: TripPreferences,
        shortlist: list[FactualShortlistedOption],
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
                    "option_id": item.candidate.option_id,
                    "destination_city": (
                        item.candidate.resolved_city_name or item.candidate.destination_city
                    ),
                    "destination_airport": item.candidate.destination_airport,
                    "price_usd": item.candidate.price_usd,
                    "trip_length_days": (
                        item.candidate.return_date - item.candidate.departure_date
                    ).days,
                    "stops_count": item.candidate.stops_count,
                    "travel_time_minutes": item.candidate.travel_time_minutes,
                    "factual_score": item.factual_score,
                }
                for item in shortlist
            ],
        }
