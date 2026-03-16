from fastapi.testclient import TestClient

from app.api.deps import get_search_service
from app.core.errors import ProviderUnavailableError
from app.main import app


class _FailingSearchService:
    def search(self, preferences):
        del preferences
        raise ProviderUnavailableError("provider timeout token=secret_token")


def test_app_error_returns_frontend_contract() -> None:
    app.dependency_overrides[get_search_service] = lambda: _FailingSearchService()
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

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "provider_unavailable"
    assert body["error"]["message"] == "Flight provider is temporarily unavailable"
    assert "secret_token" not in response.text


def test_validation_error_returns_frontend_contract() -> None:
    client = TestClient(app)
    payload = {
        "origin_city": "Belgrade",
        "dates_mode": "strict",
        "themes": ["beach"],
        "budget_usd": 1500,
    }

    response = client.post("/search", json=payload)
    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Invalid request payload"
    assert isinstance(body["detail"], list)
