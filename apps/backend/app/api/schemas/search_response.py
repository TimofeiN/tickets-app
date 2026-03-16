from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import EnrichmentMode, RankingMode, SearchDataSource


class SearchOptionContract(Protocol):
    @property
    def option_id(self) -> str: ...

    @property
    def destination_city(self) -> str: ...

    @property
    def origin_airport(self) -> str: ...

    @property
    def destination_airport(self) -> str: ...

    @property
    def price_usd(self) -> int: ...

    @property
    def score(self) -> float: ...

    @property
    def reason(self) -> str: ...

    @property
    def trip_plan(self) -> str: ...

    @property
    def theme_explanation(self) -> str: ...

    @property
    def highlights(self) -> tuple[str, ...]: ...

    @property
    def tradeoff(self) -> str: ...

    @property
    def caveat(self) -> str: ...

    @property
    def trip_style(self) -> str: ...

    @property
    def vibe(self) -> str: ...


class SearchGuidanceContract(Protocol):
    @property
    def improvement_hint(self) -> str: ...

    @property
    def counterfactual(self) -> str: ...


class SearchMetaContract(Protocol):
    @property
    def data_source(self) -> SearchDataSource: ...

    @property
    def ranking_mode(self) -> RankingMode: ...

    @property
    def enrichment_mode(self) -> EnrichmentMode: ...

    @property
    def fallback_reasons(self) -> list[str]: ...


class SearchResultContract(Protocol):
    @property
    def options(self) -> Sequence[SearchOptionContract]: ...

    @property
    def guidance(self) -> SearchGuidanceContract: ...

    @property
    def meta(self) -> SearchMetaContract: ...

    @property
    def trip_plan(self) -> str: ...


class FlightOption(BaseModel):
    option_id: str
    destination_city: str
    origin_airport: str
    destination_airport: str
    price_usd: int
    score: float = Field(ge=0, le=1)
    reason: str
    trip_plan: str = ""
    theme_explanation: str = ""
    highlights: list[str] = Field(default_factory=list, max_length=3)
    tradeoff: str = ""
    caveat: str = ""
    trip_style: str = ""
    vibe: str = ""


class SearchGuidance(BaseModel):
    improvement_hint: str = ""
    counterfactual: str = ""


class SearchMeta(BaseModel):
    data_source: SearchDataSource
    ranking_mode: RankingMode
    enrichment_mode: EnrichmentMode
    fallback_reasons: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    options: list[FlightOption] = Field(max_length=3)
    guidance: SearchGuidance
    meta: SearchMeta
    trip_plan: str = ""

    @classmethod
    def from_contract(cls, result: SearchResultContract) -> SearchResponse:
        return cls(
            options=[
                FlightOption(
                    option_id=item.option_id,
                    destination_city=item.destination_city,
                    origin_airport=item.origin_airport,
                    destination_airport=item.destination_airport,
                    price_usd=item.price_usd,
                    score=item.score,
                    reason=item.reason,
                    trip_plan=item.trip_plan,
                    theme_explanation=item.theme_explanation,
                    highlights=list(item.highlights),
                    tradeoff=item.tradeoff,
                    caveat=item.caveat,
                    trip_style=item.trip_style,
                    vibe=item.vibe,
                )
                for item in result.options
            ],
            guidance=SearchGuidance(
                improvement_hint=result.guidance.improvement_hint,
                counterfactual=result.guidance.counterfactual,
            ),
            meta=SearchMeta(
                data_source=result.meta.data_source,
                ranking_mode=result.meta.ranking_mode,
                enrichment_mode=result.meta.enrichment_mode,
                fallback_reasons=result.meta.fallback_reasons,
            ),
            trip_plan=result.trip_plan,
        )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "options": [
                    {
                        "option_id": "opt_bcn_001",
                        "destination_city": "Barcelona",
                        "origin_airport": "BEG",
                        "destination_airport": "BCN",
                        "price_usd": 640,
                        "score": 0.92,
                        "reason": "Beach + culture fit and good weather in selected window.",
                        "theme_explanation": (
                            "Beach and history come through clearly in this option."
                        ),
                        "highlights": [
                            "Strong beach and city mix",
                            "Good price for a classic summer route",
                        ],
                        "tradeoff": "Nightlife is stronger than family comfort here.",
                        "caveat": "Less suitable if you want a quiet slow-paced trip.",
                        "trip_style": "Coastal city break",
                        "vibe": "Lively coastal energy",
                    },
                    {
                        "option_id": "opt_ath_002",
                        "destination_city": "Athens",
                        "origin_airport": "BEG",
                        "destination_airport": "ATH",
                        "price_usd": 590,
                        "score": 0.88,
                        "reason": "History + gastronomy fit with balanced budget usage.",
                        "theme_explanation": "History and gastronomy are the clearest fit here.",
                        "highlights": [
                            "Strong historical depth",
                            "Reliable gastronomy signal",
                        ],
                        "tradeoff": "Beach value is present but not as dominant as the city side.",
                        "caveat": "Not the strongest pick if sea time is the only priority.",
                        "trip_style": "Culture-led city break",
                        "vibe": "Historic city with food depth",
                    },
                    {
                        "option_id": "opt_lis_003",
                        "destination_city": "Lisbon",
                        "origin_airport": "BEG",
                        "destination_airport": "LIS",
                        "price_usd": 710,
                        "score": 0.84,
                        "reason": "Strong nightlife and city activities within total budget.",
                        "theme_explanation": "Nightlife and city energy lead the match here.",
                        "highlights": [
                            "Lively evening scene",
                            "Good city-break energy",
                        ],
                        "tradeoff": "Beach time is weaker than evening and city activity value.",
                        "caveat": "Less ideal if you want a quiet family rhythm.",
                        "trip_style": "City break with late evenings",
                        "vibe": "Energetic urban escape",
                    },
                ],
                "guidance": {
                    "improvement_hint": (
                        "If beach is the main priority, remove history to widen the pool."
                    ),
                    "counterfactual": (
                        "If you optimize for family comfort, a calmer beach option may rank "
                        "above nightlife-heavy cities."
                    ),
                },
                "meta": {
                    "data_source": "fallback",
                    "ranking_mode": "deterministic",
                    "enrichment_mode": "llm",
                    "fallback_reasons": [
                        "provider_unavailable",
                    ],
                },
                "trip_plan": (
                    "Day 1: waterfront walk. Day 2: old town and bay viewpoints. Day 3: beach day."
                ),
            }
        }
    )
