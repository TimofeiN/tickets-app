from __future__ import annotations

from dataclasses import dataclass

from app.shared.enums import EnrichmentMode, RankingMode, SearchDataSource


@dataclass(frozen=True)
class SearchOptionResult:
    option_id: str
    destination_city: str
    origin_airport: str
    destination_airport: str
    price_usd: int
    score: float
    reason: str
    trip_plan: str
    suggestion_id: str | None = None
    likes: int = 0
    dislikes: int = 0
    theme_explanation: str = ""
    highlights: tuple[str, ...] = ()
    tradeoff: str = ""
    caveat: str = ""
    trip_style: str = ""
    vibe: str = ""


@dataclass(frozen=True)
class SearchGuidanceResult:
    improvement_hint: str
    counterfactual: str


@dataclass(frozen=True)
class SearchMetaResult:
    data_source: SearchDataSource
    ranking_mode: RankingMode
    enrichment_mode: EnrichmentMode
    fallback_reasons: list[str]


@dataclass(frozen=True)
class SearchResult:
    options: list[SearchOptionResult]
    guidance: SearchGuidanceResult
    meta: SearchMetaResult
    trip_plan: str
