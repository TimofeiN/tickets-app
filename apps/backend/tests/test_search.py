import json
from datetime import date
from typing import ClassVar

from fastapi.testclient import TestClient

from app.api.deps import get_search_service, get_trip_suggestion_repository
from app.application.ports.city_resolver import ResolvedCityName
from app.application.ports.flight_search_provider import FlightOffer, FlightProviderResult
from app.application.ports.llm_provider import LLMProviderError
from app.application.services.search_service import SearchService
from app.domain.models.trip_preferences import TripPreferences
from app.main import app
from app.shared.enums import EnrichmentMode, SearchDataSource


def _fixture_offers() -> list[FlightOffer]:
    return [
        FlightOffer(
            origin_airport="BEG",
            destination_airport="BCN",
            destination_city="Barcelona",
            price_usd=640,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
        ),
        FlightOffer(
            origin_airport="BEG",
            destination_airport="ATH",
            destination_city="Athens",
            price_usd=590,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
        ),
        FlightOffer(
            origin_airport="BEG",
            destination_airport="LIS",
            destination_city="Lisbon",
            price_usd=710,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
        ),
    ]


class _FakeFlightProvider:
    def __init__(self, offers: list[FlightOffer] | None = None) -> None:
        self.offers = offers or _fixture_offers()

    def get_offers(
        self,
        preferences: TripPreferences,
        *,
        origin_airports: list[str],
    ) -> FlightProviderResult:
        del preferences
        assert origin_airports
        return FlightProviderResult(offers=self.offers, source=SearchDataSource.live)


class _TwoOptionFlightProvider(_FakeFlightProvider):
    def __init__(self) -> None:
        super().__init__(offers=_fixture_offers()[:2])


class _FakeOriginAirportResolver:
    def resolve_airports(self, origin_city: str) -> list[str]:
        del origin_city
        return ["BEG"]


class _FakeCityResolver:
    def resolve_city_names(self, iata_codes: list[str]) -> list[ResolvedCityName]:
        return [ResolvedCityName(iata_code=code, city_name=f"City {code}") for code in iata_codes]


class _SuccessfulLLMProvider:
    _scores_by_option_id: ClassVar[dict[str, tuple[float, float, tuple[str, ...], str]]] = {
        "tp_beg_ath_002": (0.95, 0.85, ("beach", "history"), "Best overall fit."),
        "tp_beg_bcn_001": (0.88, 0.80, ("beach", "history"), "Great cultural match."),
        "tp_beg_lis_003": (0.80, 0.72, ("beach",), "Solid backup choice."),
    }

    def complete(self, *, system_prompt: str, user_prompt: str, output_model):
        del system_prompt, output_model
        payload = json.loads(user_prompt)
        shortlist = payload["shortlist"]
        scores: list[dict[str, object]] = []
        for item in shortlist:
            option_id = item["option_id"]
            score = self._scores_by_option_id.get(
                option_id,
                (0.5, 0.5, (), "Neutral fit."),
            )
            scores.append(
                {
                    "option_id": option_id,
                    "theme_fit_score": score[0],
                    "confidence": score[1],
                    "matched_themes": list(score[2]),
                    "reason_short": score[3],
                }
            )
        return json.dumps({"scores": scores})

    def render_trip_summary(self, *, city: str, num_days: int, themes: str) -> str:
        return f"{city} for {num_days} days with {themes}"


class _FailingSemanticLLMProvider(_SuccessfulLLMProvider):
    def complete(self, *, system_prompt: str, user_prompt: str, output_model):
        del system_prompt, user_prompt, output_model
        raise LLMProviderError("upstream timeout")


class _NoCacheTripSuggestionRepository:
    def list_top_for_query(self, *, query_key: str, limit: int = 3) -> list[object]:
        del query_key, limit
        return []

    def save_suggestions(self, **kwargs) -> list[object]:
        del kwargs
        return []


def _override_search_service(
    llm_provider: object,
    *,
    flight_provider: object | None = None,
) -> SearchService:
    return SearchService(
        flight_provider=flight_provider or _FakeFlightProvider(),
        origin_airport_resolver=_FakeOriginAirportResolver(),
        city_resolver=_FakeCityResolver(),
        semantic_scoring_provider=llm_provider,  # type: ignore[arg-type]
        enrichment_provider=llm_provider,  # type: ignore[arg-type]
    )


def _install_search_overrides(
    llm_provider: object,
    *,
    flight_provider: object | None = None,
) -> None:
    app.dependency_overrides[get_search_service] = lambda: _override_search_service(
        llm_provider,
        flight_provider=flight_provider,
    )
    app.dependency_overrides[get_trip_suggestion_repository] = lambda: (
        _NoCacheTripSuggestionRepository()
    )


def test_search_strict_dates_success() -> None:
    _install_search_overrides(_SuccessfulLLMProvider())
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
    assert "options" in body
    assert len(body["options"]) == 3
    assert "meta" in body
    assert body["meta"]["data_source"] in {"live", "fallback"}
    assert body["meta"]["ranking_mode"] in {"llm", "deterministic"}
    assert body["meta"]["enrichment_mode"] in {"llm", "unavailable"}
    assert isinstance(body["meta"]["fallback_reasons"], list)

    for option in body["options"]:
        assert option["option_id"]
        assert option["destination_city"]
        assert option["origin_airport"]
        assert option["destination_airport"]
        assert option["price_usd"] > 0
        assert 0 <= option["score"] <= 1
        assert option["reason"]
        assert "theme_explanation" in option
        assert "highlights" in option
        assert "tradeoff" in option
        assert "caveat" in option
        assert "trip_style" in option
        assert "vibe" in option
    assert "guidance" in body
    assert "improvement_hint" in body["guidance"]
    assert "counterfactual" in body["guidance"]


def test_search_requires_matching_dates_payload() -> None:
    _install_search_overrides(_SuccessfulLLMProvider())
    client = TestClient(app)
    payload = {
        "origin_city": "Belgrade",
        "dates_mode": "strict",
        "themes": ["beach"],
        "budget_usd": 1500,
    }

    response = client.post("/search", json=payload)
    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_search_uses_llm_ranking_when_available() -> None:
    _install_search_overrides(_SuccessfulLLMProvider())
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
        "tp_beg_ath_002",
        "tp_beg_bcn_001",
        "tp_beg_lis_003",
    ]
    assert [item["reason"] for item in body["options"]] == [
        "Best overall fit.",
        "Great cultural match.",
        "Solid backup choice.",
    ]
    assert body["options"][0]["trip_plan"] == "City ATH for 7 days with beach, history"
    assert body["options"][0]["theme_explanation"] == ""
    assert body["options"][0]["highlights"] == []
    assert body["guidance"]["improvement_hint"] == ""
    assert body["meta"]["data_source"] == "live"
    assert body["meta"]["ranking_mode"] == "llm"
    assert body["meta"]["enrichment_mode"] == EnrichmentMode.llm


def test_search_falls_back_to_deterministic_ranking_on_llm_failure() -> None:
    _install_search_overrides(_FailingSemanticLLMProvider())
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
        "tp_beg_ath_002",
        "tp_beg_bcn_001",
        "tp_beg_lis_003",
    ]
    assert body["meta"]["data_source"] == "live"
    assert body["meta"]["ranking_mode"] == "deterministic"
    assert body["meta"]["enrichment_mode"] == EnrichmentMode.llm
    assert "ranking_unavailable" in body["meta"]["fallback_reasons"]


def test_search_can_return_two_options() -> None:
    _install_search_overrides(
        _FailingSemanticLLMProvider(),
        flight_provider=_TwoOptionFlightProvider(),
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
    assert len(body["options"]) == 2
    assert body["meta"]["enrichment_mode"] == EnrichmentMode.llm
