from datetime import date

from app.core.errors import DataAccessError
from app.core.types import DatesMode
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences
from app.infrastructure.providers.travelpayouts_provider import TravelpayoutsProvider


def test_resolve_airports_uses_injected_resolver() -> None:
    provider = TravelpayoutsProvider(
        api_token=None,
        marker=None,
        base_url="https://api.travelpayouts.com",
        timeout_sec=3.0,
        origin_airport_resolver=lambda city: [" beg ", "BEG", "INI"] if city == "Belgrade" else [],
    )

    assert provider._resolve_airports("Belgrade") == ["BEG", "INI"]


def test_resolve_airports_returns_empty_on_data_access_error() -> None:
    def _raise_data_access_error(_: str) -> list[str]:
        raise DataAccessError("db unavailable")

    provider = TravelpayoutsProvider(
        api_token=None,
        marker=None,
        base_url="https://api.travelpayouts.com",
        timeout_sec=3.0,
        origin_airport_resolver=_raise_data_access_error,
    )

    assert provider._resolve_airports("Belgrade") == []


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


def test_fetch_live_candidates_queries_all_origins_and_deduplicates(monkeypatch) -> None:  # noqa: ANN001
    provider = TravelpayoutsProvider(
        api_token="token",
        marker=None,
        base_url="https://api.travelpayouts.com",
        timeout_sec=3.0,
        origin_airport_resolver=lambda _: ["BEG", "INI"],
    )

    calls: list[str] = []

    async def _fake_fetch_for_origin(self, client, origin_airport, preferences):  # noqa: ANN001, ARG001
        calls.append(origin_airport)
        if origin_airport == "BEG":
            return [
                FlightCandidate(
                    option_id="tp_beg_par_001",
                    destination_city="Paris",
                    origin_airport="BEG",
                    destination_airport="PAR",
                    price_usd=100,
                    departure_date=date(2026, 6, 10),
                    return_date=date(2026, 6, 17),
                    themes=frozenset({"beach"}),
                ),
                FlightCandidate(
                    option_id="tp_beg_mad_001",
                    destination_city="Madrid",
                    origin_airport="BEG",
                    destination_airport="MAD",
                    price_usd=220,
                    departure_date=date(2026, 6, 10),
                    return_date=date(2026, 6, 17),
                    themes=frozenset({"beach"}),
                ),
            ]
        return [
            FlightCandidate(
                option_id="tp_ini_par_001",
                destination_city="Paris",
                origin_airport="INI",
                destination_airport="PAR",
                price_usd=100,
                departure_date=date(2026, 6, 10),
                return_date=date(2026, 6, 17),
                themes=frozenset({"beach"}),
            ),
            FlightCandidate(
                option_id="tp_ini_rom_001",
                destination_city="Rome",
                origin_airport="INI",
                destination_airport="ROM",
                price_usd=180,
                departure_date=date(2026, 6, 10),
                return_date=date(2026, 6, 17),
                themes=frozenset({"beach"}),
            ),
        ]

    monkeypatch.setattr(
        TravelpayoutsProvider,
        "_fetch_live_candidates_for_origin",
        _fake_fetch_for_origin,
    )

    candidates = provider._fetch_live_candidates(_strict_preferences())

    assert set(calls) == {"BEG", "INI"}
    assert len(candidates) == 3
    assert {(c.destination_airport, c.price_usd) for c in candidates} == {
        ("PAR", 100),
        ("MAD", 220),
        ("ROM", 180),
    }
    assert any(c.destination_airport == "PAR" and c.origin_airport == "BEG" for c in candidates)
