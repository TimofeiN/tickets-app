from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import Field, ValidationError

from app.application.ports.llm_provider import LLMProvider
from app.core.errors import LLMResponseValidationError
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences
from app.shared.strict_model import StrictModel

_THEME_INTENTS: dict[str, str] = {
    "active_summer": "movement, outdoor energy, and physically active warm-weather days",
    "active_winter": "winter activity, mountain rhythm, and active cold-weather days",
    "beach": "sea time, warm-weather ease, and a beach-centered trip rhythm",
    "family": "comfort, calmer pacing, and easy planning for a family-style trip",
    "gastronomy": "food-led travel with strong restaurant or local dining value",
    "history": "old-city atmosphere, culture, and time around historic places",
    "nightlife": "late activity, bars or clubs, and stronger evening energy",
}


@dataclass(frozen=True)
class OptionInsight:
    option_id: str
    theme_explanation: str
    highlights: tuple[str, ...]
    tradeoff: str
    caveat: str
    trip_style: str
    vibe: str


@dataclass(frozen=True)
class SearchGuidance:
    improvement_hint: str
    counterfactual: str


@dataclass(frozen=True)
class EnrichmentContext:
    selected_count: int
    filtered_count: int
    constraints_relaxed: bool
    data_source: str
    ranking_mode: str


@dataclass(frozen=True)
class SearchEnrichment:
    insights_by_option_id: dict[str, OptionInsight]
    guidance: SearchGuidance


class _HighlightSchema(StrictModel):
    text: str = Field(
        min_length=1,
        max_length=120,
        description="Short concrete strength.",
    )


class _EnrichedOptionSchema(StrictModel):
    option_id: str = Field(min_length=1, description="Selected option identifier.")
    theme_explanation: str = Field(
        min_length=1,
        max_length=240,
        description="Theme-based explanation.",
    )
    highlights: list[_HighlightSchema] = Field(
        min_length=1,
        max_length=3,
        description="One to three short strengths.",
    )
    tradeoff: str = Field(
        min_length=1,
        max_length=180,
        description="Main compromise.",
    )
    caveat: str = Field(
        min_length=1,
        max_length=180,
        description="Main limitation.",
    )
    trip_style: str = Field(
        min_length=1,
        max_length=80,
        description="Short trip format.",
    )
    vibe: str = Field(
        min_length=1,
        max_length=80,
        description="Short mood descriptor.",
    )


class _GuidanceSchema(StrictModel):
    improvement_hint: str = Field(
        min_length=1,
        max_length=220,
        description="Actionable improvement hint.",
    )
    counterfactual: str = Field(
        min_length=1,
        max_length=220,
        description="Alternative-priority perspective.",
    )


class _LLMEnrichmentOutputSchema(StrictModel):
    options: list[_EnrichedOptionSchema] = Field(description="Enrichment for each selected option.")
    guidance: _GuidanceSchema = Field(description="Search-level guidance.")


class EnrichmentService:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    def enrich(
        self,
        preferences: TripPreferences,
        candidates: list[FlightCandidate],
        context: EnrichmentContext,
    ) -> SearchEnrichment:
        if not candidates:
            return SearchEnrichment(
                insights_by_option_id={},
                guidance=SearchGuidance(improvement_hint="", counterfactual=""),
            )

        raw_output = self.llm_provider.complete(
            system_prompt=(
                "You enrich travel search results for decision support. Return strict JSON only. "
                "Use only the facts present in the request payload. Do not invent attractions, "
                "weather, beaches, museums, family infrastructure, or nightlife details that are "
                "not supported by the payload. Keep the language concise, concrete, and user-facing. "
                "Explain fit through the user's trip intent, not by repeating theme tags. "
                "Field rules: "
                "theme_explanation must connect the user's selected themes to a plausible trip scenario "
                "for this option and must not say generic phrases like 'matches your preferences'. "
                "highlights must contain 1 to 3 concrete strengths that are useful for choosing, not "
                "generic praise or destination ads. "
                "tradeoff must explain the main useful compromise in calm decision-making language. "
                "caveat must name the main limitation and must not duplicate the tradeoff wording. "
                "trip_style must be a short practical trip format, such as a city break or family beach holiday. "
                "vibe must be a short intuitive travel mood, not taxonomy. "
                "improvement_hint must give exactly one highest-impact next-search adjustment only when the "
                "result set is weak, narrow, or constraints were relaxed; otherwise keep it short and neutral. "
                "counterfactual must explain how the choice changes if one priority shifts, and must not turn "
                "into a full reranking or generic advice. "
                "If the payload signal is weak, stay modest and specific instead of pretending certainty."
            ),
            user_prompt=json.dumps(
                {
                    "request": {
                        "themes": [
                            {
                                "key": theme,
                                "intent": _THEME_INTENTS.get(theme, "the selected trip priority"),
                            }
                            for theme in sorted(preferences.themes)
                        ],
                        "budget_usd": preferences.budget_usd,
                        "travelers_count": preferences.travelers_count,
                    },
                    "result_context": {
                        "selected_count": context.selected_count,
                        "filtered_count": context.filtered_count,
                        "constraints_relaxed": context.constraints_relaxed,
                        "data_source": context.data_source,
                        "ranking_mode": context.ranking_mode,
                    },
                    "options": [
                        {
                            "option_id": candidate.option_id,
                            "destination_city": candidate.destination_city,
                            "destination_airport": candidate.destination_airport,
                            "price_usd": candidate.price_usd,
                            "themes": sorted(candidate.themes),
                        }
                        for candidate in candidates
                    ],
                },
                ensure_ascii=True,
            ),
            output_model=_LLMEnrichmentOutputSchema,
        )

        try:
            parsed = _LLMEnrichmentOutputSchema.model_validate_json(raw_output)
        except ValidationError as exc:
            raise LLMResponseValidationError(
                "llm enrichment output failed schema validation"
            ) from exc

        allowed_ids = {candidate.option_id for candidate in candidates}
        insights: dict[str, OptionInsight] = {}
        for item in parsed.options:
            if item.option_id not in allowed_ids:
                raise LLMResponseValidationError("llm enrichment returned unknown option id")
            insights[item.option_id] = OptionInsight(
                option_id=item.option_id,
                theme_explanation=item.theme_explanation.strip(),
                highlights=tuple(highlight.text.strip() for highlight in item.highlights),
                tradeoff=item.tradeoff.strip(),
                caveat=item.caveat.strip(),
                trip_style=item.trip_style.strip(),
                vibe=item.vibe.strip(),
            )

        if len(insights) != len(candidates):
            raise LLMResponseValidationError("llm enrichment did not return all options")

        return SearchEnrichment(
            insights_by_option_id=insights,
            guidance=SearchGuidance(
                improvement_hint=parsed.guidance.improvement_hint.strip(),
                counterfactual=parsed.guidance.counterfactual.strip(),
            ),
        )


def build_empty_enrichment(
    _preferences: TripPreferences,
    candidates: list[FlightCandidate],
    _context: EnrichmentContext,
) -> SearchEnrichment:
    return SearchEnrichment(
        insights_by_option_id={
            candidate.option_id: OptionInsight(
                option_id=candidate.option_id,
                theme_explanation="",
                highlights=(),
                tradeoff="",
                caveat="",
                trip_style="",
                vibe="",
            )
            for candidate in candidates
        },
        guidance=SearchGuidance(
            improvement_hint="",
            counterfactual="",
        ),
    )
