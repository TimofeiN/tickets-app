from __future__ import annotations

from enum import Enum


class DatesMode(str, Enum):
    strict = "strict"
    flexible = "flexible"


class SearchDataSource(str, Enum):
    live = "live"
    fallback = "fallback"


class RankingMode(str, Enum):
    llm = "llm"
    deterministic = "deterministic"
