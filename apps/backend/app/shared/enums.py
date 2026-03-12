from __future__ import annotations

from enum import Enum


class DatesMode(str, Enum):
    strict = "strict"
    flexible = "flexible"


class TripTheme(str, Enum):
    beach = "beach"
    history = "history"
    active_summer = "active_summer"
    active_winter = "active_winter"
    gastronomy = "gastronomy"
    family = "family"
    nightlife = "nightlife"


class SearchDataSource(str, Enum):
    live = "live"
    fallback = "fallback"


class RankingMode(str, Enum):
    llm = "llm"
    deterministic = "deterministic"


class EnrichmentMode(str, Enum):
    llm = "llm"
    unavailable = "unavailable"
