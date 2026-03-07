from app.api.mappers.trip_preferences_mapper import to_trip_preferences
from app.api.schemas.search_request import SearchRequest
from app.core.types import DatesMode


def test_to_trip_preferences_maps_strict_payload() -> None:
    payload = SearchRequest(
        origin_city="Belgrade",
        dates_mode="strict",
        strict_dates={"start_date": "2026-06-10", "end_date": "2026-06-17"},
        themes=["beach", "history"],
        budget_usd=2000,
        travelers_count=2,
    )

    preferences = to_trip_preferences(payload)

    assert preferences.origin_city == "Belgrade"
    assert preferences.dates_mode == DatesMode.strict
    assert preferences.strict_start_date is not None
    assert preferences.strict_end_date is not None
    assert preferences.flexible_year is None


def test_to_trip_preferences_maps_flexible_payload() -> None:
    payload = SearchRequest(
        origin_city="Belgrade",
        dates_mode="flexible",
        flexible_dates={"year": 2026, "month": 7, "trip_length_days": 7},
        themes=["beach"],
        budget_usd=1800,
        travelers_count=2,
    )

    preferences = to_trip_preferences(payload)

    assert preferences.dates_mode == DatesMode.flexible
    assert preferences.flexible_year == 2026
    assert preferences.flexible_month == 7
    assert preferences.flexible_trip_length_days == 7
    assert preferences.strict_start_date is None
    assert preferences.strict_end_date is None
