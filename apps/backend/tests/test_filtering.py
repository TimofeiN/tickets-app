from datetime import date

from app.api.mappers.trip_preferences_mapper import to_trip_preferences
from app.api.schemas.search.request import SearchRequest
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.services.filtering import filter_candidates


def _candidate(
    option_id: str,
    price_usd: int,
    departure_date: date,
    return_date: date,
) -> FlightCandidate:
    return FlightCandidate(
        option_id=option_id,
        destination_city="City",
        origin_airport="BEG",
        destination_airport="DST",
        price_usd=price_usd,
        departure_date=departure_date,
        return_date=return_date,
        themes=frozenset({"beach"}),
    )


def test_filter_candidates_strict_applies_budget_and_date_window() -> None:
    payload = SearchRequest(
        origin_city="Belgrade",
        dates_mode="strict",
        strict_dates={"start_date": "2026-06-10", "end_date": "2026-06-17"},
        themes=["beach"],
        budget_usd=1200,
        travelers_count=2,
    )
    candidates = [
        _candidate("keep", 500, date(2026, 6, 10), date(2026, 6, 17)),
        _candidate("too_expensive", 700, date(2026, 6, 10), date(2026, 6, 17)),
        _candidate("outside_dates", 450, date(2026, 6, 20), date(2026, 6, 27)),
    ]

    filtered = filter_candidates(candidates, to_trip_preferences(payload))

    assert [candidate.option_id for candidate in filtered] == ["keep"]


def test_filter_candidates_returns_empty_when_no_budget_fit() -> None:
    payload = SearchRequest(
        origin_city="Belgrade",
        dates_mode="strict",
        strict_dates={"start_date": "2026-06-10", "end_date": "2026-06-17"},
        themes=["beach"],
        budget_usd=400,
        travelers_count=2,
    )
    candidates = [_candidate("too_expensive", 300, date(2026, 6, 10), date(2026, 6, 17))]

    filtered = filter_candidates(candidates, to_trip_preferences(payload))

    assert filtered == []
