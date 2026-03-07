from fastapi.testclient import TestClient

from app.main import app


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
    assert body["options"][0]["destination_city"] == "Barcelona"
    assert body["options"][0]["option_id"] == "opt_bcn_001"


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
