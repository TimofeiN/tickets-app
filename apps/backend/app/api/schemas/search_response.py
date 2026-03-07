from __future__ import annotations

from typing import Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.core.types import RankingMode, SearchDataSource


class SearchOptionContract(Protocol):
    option_id: str
    destination_city: str
    origin_airport: str
    destination_airport: str
    price_usd: int
    score: float
    reason: str


class SearchMetaContract(Protocol):
    data_source: SearchDataSource
    ranking_mode: RankingMode
    constraints_relaxed: bool
    fallback_reasons: list[str]


class SearchResultContract(Protocol):
    options: Sequence[SearchOptionContract]
    meta: SearchMetaContract


class FlightOption(BaseModel):
    option_id: str
    destination_city: str
    origin_airport: str
    destination_airport: str
    price_usd: int
    score: float = Field(ge=0, le=1)
    reason: str


class SearchMeta(BaseModel):
    data_source: SearchDataSource
    ranking_mode: RankingMode
    constraints_relaxed: bool
    fallback_reasons: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    options: list[FlightOption] = Field(min_length=3, max_length=3)
    meta: SearchMeta

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
                )
                for item in result.options
            ],
            meta=SearchMeta(
                data_source=result.meta.data_source,
                ranking_mode=result.meta.ranking_mode,
                constraints_relaxed=result.meta.constraints_relaxed,
                fallback_reasons=result.meta.fallback_reasons,
            ),
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
                    },
                    {
                        "option_id": "opt_ath_002",
                        "destination_city": "Athens",
                        "origin_airport": "BEG",
                        "destination_airport": "ATH",
                        "price_usd": 590,
                        "score": 0.88,
                        "reason": "History + gastronomy fit with balanced budget usage.",
                    },
                    {
                        "option_id": "opt_lis_003",
                        "destination_city": "Lisbon",
                        "origin_airport": "BEG",
                        "destination_airport": "LIS",
                        "price_usd": 710,
                        "score": 0.84,
                        "reason": "Strong nightlife and city activities within total budget.",
                    },
                ],
                "meta": {
                    "data_source": "fallback",
                    "ranking_mode": "deterministic",
                    "constraints_relaxed": True,
                    "fallback_reasons": [
                        "provider unavailable: timeout",
                        "returned fewer than 3 matches after filters",
                    ],
                },
            }
        }
    )
