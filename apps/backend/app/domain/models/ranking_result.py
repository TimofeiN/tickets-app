from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RankedOption:
    option_id: str
    reason: str


@dataclass(frozen=True)
class RankingResult:
    ranked_options: tuple[RankedOption, RankedOption, RankedOption]
