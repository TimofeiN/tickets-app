from __future__ import annotations

from enum import StrEnum


class DatesMode(StrEnum):
    strict = "strict"
    flexible = "flexible"


class TripTheme(StrEnum):
    beach = "beach"
    history = "history"
    active_summer = "active_summer"
    active_winter = "active_winter"
    gastronomy = "gastronomy"
    family = "family"
    nightlife = "nightlife"


class SearchDataSource(StrEnum):
    live = "live"
    fallback = "fallback"


class RankingMode(StrEnum):
    llm = "llm"
    deterministic = "deterministic"


class EnrichmentMode(StrEnum):
    llm = "llm"
    unavailable = "unavailable"
