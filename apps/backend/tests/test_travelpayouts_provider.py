from datetime import date

import pytest

from app.application.ports.flight_search_provider import FlightOffer
from app.core.errors import ProviderUnavailableError
from app.domain.models.trip_preferences import TripPreferences
from app.infrastructure.providers.travelpayouts_provider import TravelpayoutsProvider
from app.shared.enums import DatesMode, SearchDataSource


def _strict_preferences() -> TripPreferences:
    return TripPreferences(
        origin_city="Belgrade",
        dates_mode=DatesMode.strict,
        themes=("beach",),
        budget_usd=2000,
        travelers_count=2,
        strict_start_date=date(2026, 6, 10),
        strict_end_date=date(2026, 6, 17),
    )


def test_fetch_live_offers_requires_origin_airports() -> None:
    provider = TravelpayoutsProvider(
        api_token="token",
        marker=None,
        base_url="https://api.travelpayouts.com",
        timeout_sec=3.0,
    )

    with pytest.raises(
        ProviderUnavailableError,
        match="origin city is not mapped to known airports",
    ):
        provider._fetch_live_offers(_strict_preferences(), origin_airports=[])


def test_fetch_live_offers_queries_all_origins_and_merges_results(monkeypatch) -> None:
    provider = TravelpayoutsProvider(
        api_token="token",
        marker=None,
        base_url="https://api.travelpayouts.com",
        timeout_sec=3.0,
    )

    calls: list[str] = []

    async def _fake_fetch_for_origin(self, client, origin_airport, preferences):
        del self, client, preferences
        calls.append(origin_airport)
        if origin_airport == "BEG":
            return [
                FlightOffer(
                    origin_airport="BEG",
                    destination_airport="PAR",
                    destination_city="Paris",
                    price_usd=100,
                    departure_date=date(2026, 6, 10),
                    return_date=date(2026, 6, 17),
                ),
                FlightOffer(
                    origin_airport="BEG",
                    destination_airport="MAD",
                    destination_city="Madrid",
                    price_usd=220,
                    departure_date=date(2026, 6, 10),
                    return_date=date(2026, 6, 17),
                ),
            ]
        return [
            FlightOffer(
                origin_airport="INI",
                destination_airport="PAR",
                destination_city="Paris",
                price_usd=100,
                departure_date=date(2026, 6, 10),
                return_date=date(2026, 6, 17),
            ),
            FlightOffer(
                origin_airport="INI",
                destination_airport="ROM",
                destination_city="Rome",
                price_usd=180,
                departure_date=date(2026, 6, 10),
                return_date=date(2026, 6, 17),
            ),
        ]

    monkeypatch.setattr(
        TravelpayoutsProvider,
        "_fetch_live_offers_for_origin",
        _fake_fetch_for_origin,
    )

    offers = provider._fetch_live_offers(_strict_preferences(), origin_airports=["BEG", "INI"])

    assert set(calls) == {"BEG", "INI"}
    assert len(offers) == 4
    assert {
        (offer.origin_airport, offer.destination_airport, offer.price_usd) for offer in offers
    } == {
        ("BEG", "PAR", 100),
        ("BEG", "MAD", 220),
        ("INI", "PAR", 100),
        ("INI", "ROM", 180),
    }


def test_get_offers_returns_live_source() -> None:
    provider = TravelpayoutsProvider(
        api_token="token",
        marker=None,
        base_url="https://api.travelpayouts.com",
        timeout_sec=3.0,
    )
    expected_offers = [
        FlightOffer(
            origin_airport="BEG",
            destination_airport="ATH",
            destination_city="Athens",
            price_usd=180,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
        )
    ]

    provider._fetch_live_offers = lambda preferences, *, origin_airports: expected_offers  # type: ignore[method-assign]
    result = provider.get_offers(_strict_preferences(), origin_airports=["BEG"])

    assert result.offers == expected_offers
    assert result.source == SearchDataSource.live
