from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import get_search_service
from app.application.dto.search_result import (
    SearchGuidanceResult,
    SearchMetaResult,
    SearchOptionResult,
    SearchResult,
)
from app.infrastructure.db.session import get_db_session
from app.main import app
from app.shared.enums import EnrichmentMode, RankingMode, SearchDataSource


class _FakeSearchService:
    def search(self, preferences) -> SearchResult:
        del preferences
        return SearchResult(
            options=[
                SearchOptionResult(
                    option_id="opt_001",
                    destination_city="Barcelona",
                    origin_airport="BEG",
                    destination_airport="BCN",
                    price_usd=640,
                    score=0.91,
                    reason="Strong thematic fit.",
                    trip_plan="Day 1: arrival. Day 2: old town.",
                )
            ],
            guidance=SearchGuidanceResult(improvement_hint="", counterfactual=""),
            meta=SearchMetaResult(
                data_source=SearchDataSource.live,
                ranking_mode=RankingMode.llm,
                enrichment_mode=EnrichmentMode.llm,
                fallback_reasons=[],
            ),
            trip_plan="Day 1: arrival. Day 2: old town.",
        )


class _SwitchableSearchService:
    def __init__(self) -> None:
        self.calls = 0
        self._result = self._build_result(
            option_id="opt_001",
            destination_city="Barcelona",
            destination_airport="BCN",
            price_usd=640,
            score=0.91,
            reason="Strong thematic fit.",
        )

    def set_result(
        self,
        *,
        option_id: str,
        destination_city: str,
        destination_airport: str,
        price_usd: int,
        score: float,
        reason: str,
    ) -> None:
        self._result = self._build_result(
            option_id=option_id,
            destination_city=destination_city,
            destination_airport=destination_airport,
            price_usd=price_usd,
            score=score,
            reason=reason,
        )

    def search(self, preferences) -> SearchResult:
        del preferences
        self.calls += 1
        return self._result

    @staticmethod
    def _build_result(
        *,
        option_id: str,
        destination_city: str,
        destination_airport: str,
        price_usd: int,
        score: float,
        reason: str,
    ) -> SearchResult:
        return SearchResult(
            options=[
                SearchOptionResult(
                    option_id=option_id,
                    destination_city=destination_city,
                    origin_airport="BEG",
                    destination_airport=destination_airport,
                    price_usd=price_usd,
                    score=score,
                    reason=reason,
                    trip_plan="Day 1: arrival. Day 2: old town.",
                )
            ],
            guidance=SearchGuidanceResult(improvement_hint="", counterfactual=""),
            meta=SearchMetaResult(
                data_source=SearchDataSource.live,
                ranking_mode=RankingMode.llm,
                enrichment_mode=EnrichmentMode.llm,
                fallback_reasons=[],
            ),
            trip_plan="Day 1: arrival. Day 2: old town.",
        )


def _install_sqlite_sessions() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def _override_get_db_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session


def test_auth_and_saved_search_flow() -> None:
    _install_sqlite_sessions()
    app.dependency_overrides[get_search_service] = lambda: _FakeSearchService()
    client = TestClient(app)

    register_response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "supersecret"},
    )

    assert register_response.status_code == 200
    auth_body = register_response.json()
    token = auth_body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@example.com"

    search_response = client.post(
        "/search",
        headers=headers,
        json={
            "origin_city": "Belgrade",
            "dates_mode": "strict",
            "strict_dates": {
                "start_date": "2026-06-10",
                "end_date": "2026-06-13",
            },
            "themes": ["beach", "history"],
            "budget_usd": 2000,
            "travelers_count": 2,
        },
    )

    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["saved_search_id"]

    saved_searches_response = client.get("/searches", headers=headers)
    assert saved_searches_response.status_code == 200
    saved_searches_body = saved_searches_response.json()
    assert len(saved_searches_body) == 1
    assert saved_searches_body[0]["summary_destination"] == "Barcelona"
    assert saved_searches_body[0]["options_count"] == 1

    detail_response = client.get(
        f"/searches/{search_body['saved_search_id']}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["request_payload"]["origin_city"] == "Belgrade"
    assert detail_body["response_payload"]["options"][0]["destination_city"] == "Barcelona"

    logout_response = client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == 200

    me_after_logout = client.get("/auth/me", headers=headers)
    assert me_after_logout.status_code == 401

    app.dependency_overrides.clear()


def test_saved_searches_require_auth() -> None:
    _install_sqlite_sessions()
    client = TestClient(app)

    response = client.get("/searches")

    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_search_uses_cached_suggestions_for_same_query() -> None:
    _install_sqlite_sessions()
    switchable_service = _SwitchableSearchService()
    app.dependency_overrides[get_search_service] = lambda: switchable_service
    client = TestClient(app)
    payload = {
        "origin_city": "Belgrade",
        "dates_mode": "strict",
        "strict_dates": {
            "start_date": "2026-06-10",
            "end_date": "2026-06-13",
        },
        "themes": ["beach", "history"],
        "budget_usd": 2000,
        "travelers_count": 2,
    }

    first_response = client.post("/search", json=payload)
    assert first_response.status_code == 200
    first_body = first_response.json()
    first_suggestion_id = first_body["options"][0]["suggestion_id"]
    assert first_suggestion_id
    assert first_body["options"][0]["destination_city"] == "Barcelona"
    assert switchable_service.calls == 1

    switchable_service.set_result(
        option_id="opt_999",
        destination_city="Rome",
        destination_airport="FCO",
        price_usd=999,
        score=0.12,
        reason="This should not be returned while cache exists.",
    )

    second_response = client.post("/search", json=payload)
    assert second_response.status_code == 200
    second_body = second_response.json()
    assert second_body["options"][0]["destination_city"] == "Barcelona"
    assert second_body["options"][0]["suggestion_id"] == first_suggestion_id
    assert second_body["meta"]["ranking_mode"] == "deterministic"
    assert switchable_service.calls == 1

    app.dependency_overrides.clear()


def test_user_reaction_updates_suggestion_rating() -> None:
    _install_sqlite_sessions()
    app.dependency_overrides[get_search_service] = lambda: _FakeSearchService()
    client = TestClient(app)

    register_response = client.post(
        "/auth/register",
        json={"email": "reactions@example.com", "password": "supersecret"},
    )
    assert register_response.status_code == 200
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    search_payload = {
        "origin_city": "Belgrade",
        "dates_mode": "strict",
        "strict_dates": {
            "start_date": "2026-06-10",
            "end_date": "2026-06-13",
        },
        "themes": ["beach", "history"],
        "budget_usd": 2000,
        "travelers_count": 2,
    }
    search_response = client.post("/search", json=search_payload)
    assert search_response.status_code == 200
    suggestion_id = search_response.json()["options"][0]["suggestion_id"]
    assert suggestion_id

    like_response = client.post(
        f"/search/suggestions/{suggestion_id}/reaction",
        headers=headers,
        json={"reaction": "like"},
    )
    assert like_response.status_code == 200
    like_body = like_response.json()
    assert like_body["likes"] == 1
    assert like_body["dislikes"] == 0
    assert like_body["reaction"] == "like"

    dislike_response = client.post(
        f"/search/suggestions/{suggestion_id}/reaction",
        headers=headers,
        json={"reaction": "dislike"},
    )
    assert dislike_response.status_code == 200
    dislike_body = dislike_response.json()
    assert dislike_body["likes"] == 0
    assert dislike_body["dislikes"] == 1
    assert dislike_body["reaction"] == "dislike"

    cached_response = client.post("/search", json=search_payload)
    assert cached_response.status_code == 200
    cached_option = cached_response.json()["options"][0]
    assert cached_option["suggestion_id"] == suggestion_id
    assert cached_option["likes"] == 0
    assert cached_option["dislikes"] == 1

    app.dependency_overrides.clear()
