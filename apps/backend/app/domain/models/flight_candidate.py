from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class FlightCandidate:
    option_id: str
    destination_city: str
    origin_airport: str
    destination_airport: str
    price_usd: int
    departure_date: date
    return_date: date
    themes: frozenset[str]
    stops_count: int | None = None
    travel_time_minutes: int | None = None
    resolved_city_name: str = ""
