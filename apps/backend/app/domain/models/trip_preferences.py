from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.shared.enums import DatesMode


@dataclass(frozen=True)
class TripPreferences:
    origin_city: str
    dates_mode: DatesMode
    themes: tuple[str, ...]
    budget_usd: int
    travelers_count: int
    strict_start_date: date | None = None
    strict_end_date: date | None = None
    flexible_year: int | None = None
    flexible_month: int | None = None
    flexible_trip_length_days: int | None = None
