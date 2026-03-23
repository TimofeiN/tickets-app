from __future__ import annotations

from app.api.schemas.search.request import SearchRequest
from app.domain.models.trip_preferences import TripPreferences


def to_trip_preferences(payload: SearchRequest) -> TripPreferences:
    strict_start_date = payload.strict_dates.start_date if payload.strict_dates else None
    strict_end_date = payload.strict_dates.end_date if payload.strict_dates else None

    return TripPreferences(
        origin_city=payload.origin_city,
        dates_mode=payload.dates_mode,
        themes=tuple(theme.value for theme in payload.themes),
        budget_usd=payload.budget_usd,
        travelers_count=payload.travelers_count,
        strict_start_date=strict_start_date,
        strict_end_date=strict_end_date,
    )
