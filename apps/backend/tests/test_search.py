from datetime import date

from fastapi.testclient import TestClient

from app.api.deps import get_search_service
from app.application.ports.flight_search_provider import FlightSearchResult
from app.application.ports.llm_provider import LLMProviderError
from app.application.services.ranking_service import RankingService
from app.application.services.search_service import SearchService
from app.core.types import SearchDataSource
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences
from app.main import app


def _fixture_candidates() -> list[FlightCandidate]:
    return [
        FlightCandidate(
            option_id="opt_bcn_001",
            destination_city="Barcelona",
            origin_airport="BEG",
            destination_airport="BCN",
            price_usd=640,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
            themes=frozenset({"beach", "history", "nightlife"}),
        ),
        FlightCandidate(
            option_id="opt_ath_002",
            destination_city="Athens",
            origin_airport="BEG",
            destination_airport="ATH",
            price_usd=590,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
            themes=frozenset({"history", "beach", "gastronomy"}),
        ),
        FlightCandidate(
            option_id="opt_lis_003",
            destination_city="Lisbon",
            origin_airport="BEG",
            destination_airport="LIS",
            price_usd=710,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
            themes=frozenset({"nightlife", "history", "beach"}),
        ),
    ]


class _FakeFlightProvider:
    def get_candidates(self, preferences: TripPreferences) -> FlightSearchResult:  # noqa: ARG002
        return FlightSearchResult(candidates=_fixture_candidates(), source=SearchDataSource.live)


class _FakeCityResolver:
    def resolve_city_names(self, iata_codes: list[str]) -> dict[str, str]:
        return {code: f"City {code}" for code in iata_codes}


class _SuccessfulRankingService:
    def rank(self, preferences: TripPreferences, shortlist: list[FlightCandidate]):  # noqa: ARG002
        from app.domain.models.ranking_result import RankedOption, RankingResult

        return RankingResult(
            ranked_options=(
                RankedOption(option_id="opt_ath_002", reason="Best overall fit."),
                RankedOption(option_id="opt_bcn_001", reason="Great cultural match."),
                RankedOption(option_id="opt_lis_003", reason="Solid backup choice."),
            )
        )


class _FailingRankingService:
    def rank(self, preferences: TripPreferences, shortlist: list[FlightCandidate]):  # noqa: ARG002
        raise LLMProviderError("upstream timeout")


def _override_search_service(ranking_service: RankingService) -> SearchService:
    return SearchService(
        flight_provider=_FakeFlightProvider(),
        city_resolver=_FakeCityResolver(),
        ranking_service_factory=lambda: ranking_service,
        shortlist_limit=8,
    )


def test_search_strict_dates_success() -> None:
    client = TestClient(app)
    payload = {
        "origin_city": "Belgrade",
        "dates_mode": "strict",
        "strict_dates": {
            "start_date": "2026-06-10",
            "end_date": "2026-06-17",
        },
        "themes": ["beach", "history"],
        "budget_usd": 2000,
        "travelers_count": 2,
    }

    response = client.post("/search", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "options" in body
    assert len(body["options"]) == 3
    assert "meta" in body
    assert body["meta"]["data_source"] in {"live", "fallback"}
    assert body["meta"]["ranking_mode"] in {"llm", "deterministic"}
    assert isinstance(body["meta"]["constraints_relaxed"], bool)
    assert isinstance(body["meta"]["fallback_reasons"], list)

    for option in body["options"]:
        assert option["option_id"]
        assert option["destination_city"]
        assert option["origin_airport"]
        assert option["destination_airport"]
        assert option["price_usd"] > 0
        assert 0 <= option["score"] <= 1
        assert option["reason"]


def test_search_requires_matching_dates_payload() -> None:
    client = TestClient(app)
    payload = {
        "origin_city": "Belgrade",
        "dates_mode": "strict",
        "themes": ["beach"],
        "budget_usd": 1500,
    }

    response = client.post("/search", json=payload)

    assert response.status_code == 422


def test_search_uses_llm_ranking_when_available() -> None:
    app.dependency_overrides[get_search_service] = lambda: _override_search_service(
        _SuccessfulRankingService()  # type: ignore[arg-type]
    )
    client = TestClient(app)
    payload = {
        "origin_city": "Belgrade",
        "dates_mode": "strict",
        "strict_dates": {
            "start_date": "2026-06-10",
            "end_date": "2026-06-17",
        },
        "themes": ["beach", "history"],
        "budget_usd": 2000,
        "travelers_count": 2,
    }

    response = client.post("/search", json=payload)
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [item["option_id"] for item in body["options"]] == [
        "opt_ath_002",
        "opt_bcn_001",
        "opt_lis_003",
    ]
    assert [item["reason"] for item in body["options"]] == [
        "Best overall fit.",
        "Great cultural match.",
        "Solid backup choice.",
    ]
    assert body["meta"]["data_source"] == "live"
    assert body["meta"]["ranking_mode"] == "llm"
    assert body["meta"]["constraints_relaxed"] is False


def test_search_falls_back_to_deterministic_ranking_on_llm_failure() -> None:
    app.dependency_overrides[get_search_service] = lambda: _override_search_service(
        _FailingRankingService()  # type: ignore[arg-type]
    )
    client = TestClient(app)
    payload = {
        "origin_city": "Belgrade",
        "dates_mode": "strict",
        "strict_dates": {
            "start_date": "2026-06-10",
            "end_date": "2026-06-17",
        },
        "themes": ["beach", "history"],
        "budget_usd": 2000,
        "travelers_count": 2,
    }

    response = client.post("/search", json=payload)
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["options"]) == 3
    assert [item["option_id"] for item in body["options"]] == [
        "opt_ath_002",
        "opt_bcn_001",
        "opt_lis_003",
    ]
    assert body["meta"]["data_source"] == "live"
    assert body["meta"]["ranking_mode"] == "deterministic"
