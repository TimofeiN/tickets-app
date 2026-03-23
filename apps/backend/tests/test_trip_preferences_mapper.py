from app.api.mappers.trip_preferences_mapper import to_trip_preferences
from app.api.schemas.search.request import SearchRequest
from app.shared.enums import DatesMode


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


def test_search_request_rejects_flexible_mode_until_implemented() -> None:
    try:
        SearchRequest(
            origin_city="Belgrade",
            dates_mode="flexible",
            themes=["beach"],
            budget_usd=1800,
            travelers_count=2,
        )
    except ValueError as exc:
        assert "future implementation" in str(exc)
    else:
        raise AssertionError("flexible mode should be rejected")
