from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences
from app.shared.enums import SearchDataSource


@dataclass(frozen=True)
class FlightSearchResult:
    candidates: list[FlightCandidate]
    source: SearchDataSource


@dataclass(frozen=True)
class FlightOffer:
    origin_airport: str
    destination_airport: str
    destination_city: str
    price_usd: int
    departure_date: date
    return_date: date
    stops_count: int | None = None
    travel_time_minutes: int | None = None


@dataclass(frozen=True)
class FlightProviderResult:
    offers: list[FlightOffer]
    source: SearchDataSource


class FlightSearchProvider(Protocol):
    def get_offers(
        self,
        preferences: TripPreferences,
        *,
        origin_airports: list[str],
    ) -> FlightProviderResult: ...
