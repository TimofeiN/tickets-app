from __future__ import annotations

from dataclasses import dataclass

from app.core.types import RankingMode, SearchDataSource


@dataclass(frozen=True)
class SearchOptionResult:
    option_id: str
    destination_city: str
    origin_airport: str
    destination_airport: str
    price_usd: int
    score: float
    reason: str


@dataclass(frozen=True)
class SearchMetaResult:
    data_source: SearchDataSource
    ranking_mode: RankingMode
    constraints_relaxed: bool
    fallback_reasons: list[str]


@dataclass(frozen=True)
class SearchResult:
    options: list[SearchOptionResult]
    meta: SearchMetaResult
