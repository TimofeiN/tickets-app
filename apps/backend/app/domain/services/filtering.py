from __future__ import annotations

from app.core.errors import DomainInvariantError
from app.core.types import DatesMode
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences


def filter_candidates(
    candidates: list[FlightCandidate],
    preferences: TripPreferences,
) -> list[FlightCandidate]:
    filtered_by_budget = _filter_by_budget(candidates, preferences)
    return _filter_by_dates(filtered_by_budget, preferences)


def _filter_by_budget(
    candidates: list[FlightCandidate],
    preferences: TripPreferences,
) -> list[FlightCandidate]:
    per_traveler_budget = preferences.budget_usd / preferences.travelers_count
    return [candidate for candidate in candidates if candidate.price_usd <= per_traveler_budget]


def _filter_by_dates(
    candidates: list[FlightCandidate],
    preferences: TripPreferences,
) -> list[FlightCandidate]:
    if preferences.dates_mode == DatesMode.strict:
        if preferences.strict_start_date is None or preferences.strict_end_date is None:
            raise DomainInvariantError("strict dates are required for strict mode")
        return [
            candidate
            for candidate in candidates
            if candidate.departure_date >= preferences.strict_start_date
            and candidate.return_date <= preferences.strict_end_date
        ]

    if (
        preferences.flexible_year is None
        or preferences.flexible_month is None
        or preferences.flexible_trip_length_days is None
    ):
        raise DomainInvariantError("flexible dates payload is incomplete")

    return [
        candidate
        for candidate in candidates
        if _matches_flexible_window(
            candidate,
            preferences.flexible_year,
            preferences.flexible_month,
            preferences.flexible_trip_length_days,
        )
    ]


def _matches_flexible_window(
    candidate: FlightCandidate,
    year: int,
    month: int,
    trip_length_days: int,
) -> bool:
    if candidate.departure_date.year != year or candidate.departure_date.month != month:
        return False

    actual_length_days = (candidate.return_date - candidate.departure_date).days
    return actual_length_days == trip_length_days
