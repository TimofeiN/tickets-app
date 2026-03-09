from datetime import date

from app.core.types import DatesMode
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences
from app.domain.services.scoring import pick_with_fallback, score_candidate


def test_score_candidate_uses_per_traveler_budget() -> None:
    candidate = FlightCandidate(
        option_id="opt_001",
        destination_city="City",
        origin_airport="BEG",
        destination_airport="BCN",
        price_usd=450,
        departure_date=date(2026, 6, 10),
        return_date=date(2026, 6, 17),
        themes=frozenset({"beach", "history"}),
    )
    preferences_two_travelers = TripPreferences(
        origin_city="Belgrade",
        dates_mode=DatesMode.strict,
        themes=("beach", "history"),
        budget_usd=2000,
        travelers_count=2,
    )
    preferences_four_travelers = TripPreferences(
        origin_city="Belgrade",
        dates_mode=DatesMode.strict,
        themes=("beach", "history"),
        budget_usd=2000,
        travelers_count=4,
    )

    score_two_travelers = score_candidate(candidate, preferences_two_travelers)
    score_four_travelers = score_candidate(candidate, preferences_four_travelers)

    assert score_four_travelers < score_two_travelers


def _candidate(
    *,
    option_id: str,
    destination_airport: str,
    price_usd: int,
) -> FlightCandidate:
    return FlightCandidate(
        option_id=option_id,
        destination_city="City",
        origin_airport="BEG",
        destination_airport=destination_airport,
        price_usd=price_usd,
        departure_date=date(2026, 6, 10),
        return_date=date(2026, 6, 17),
        themes=frozenset({"beach"}),
    )


def test_pick_with_fallback_prefers_cheapest_unique_destinations() -> None:
    preferences = TripPreferences(
        origin_city="Belgrade",
        dates_mode=DatesMode.strict,
        themes=("beach",),
        budget_usd=2000,
        travelers_count=2,
    )
    filtered = [
        _candidate(option_id="a1", destination_airport="ATH", price_usd=180),
        _candidate(option_id="a2", destination_airport="ATH", price_usd=130),
        _candidate(option_id="b1", destination_airport="BCN", price_usd=160),
        _candidate(option_id="c1", destination_airport="CDG", price_usd=140),
    ]

    picked = pick_with_fallback(filtered, filtered, preferences)

    assert [item.option_id for item in picked] == ["a2", "c1", "b1"]
    assert len({item.destination_airport for item in picked}) == len(picked)


def test_pick_with_fallback_can_return_less_than_three() -> None:
    preferences = TripPreferences(
        origin_city="Belgrade",
        dates_mode=DatesMode.strict,
        themes=("beach",),
        budget_usd=2000,
        travelers_count=2,
    )
    filtered = [
        _candidate(option_id="a1", destination_airport="ATH", price_usd=180),
        _candidate(option_id="a2", destination_airport="ATH", price_usd=130),
    ]
    all_candidates = [
        _candidate(option_id="a1", destination_airport="ATH", price_usd=180),
        _candidate(option_id="a2", destination_airport="ATH", price_usd=130),
    ]

    picked = pick_with_fallback(filtered, all_candidates, preferences)

    assert [item.option_id for item in picked] == ["a2"]
