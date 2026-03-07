from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.types import SearchDataSource
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences


@dataclass(frozen=True)
class FlightSearchResult:
    candidates: list[FlightCandidate]
    source: SearchDataSource
    fallback_reason: str | None = None


class FlightSearchProvider(Protocol):
    def get_candidates(self, preferences: TripPreferences) -> FlightSearchResult: ...
