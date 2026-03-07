from __future__ import annotations

import json
from datetime import date

import pytest

from app.api.mappers.trip_preferences_mapper import to_trip_preferences
from app.api.schemas.search_request import SearchRequest
from app.application.ports.llm_provider import LLMProvider, LLMProviderError
from app.application.services.ranking_service import (
    LLMResponseValidationError,
    RankingService,
)
from app.domain.models.flight_candidate import FlightCandidate


def _payload() -> SearchRequest:
    return SearchRequest(
        origin_city="Belgrade",
        dates_mode="strict",
        strict_dates={"start_date": "2026-06-10", "end_date": "2026-06-17"},
        themes=["beach", "history"],
        budget_usd=2000,
        travelers_count=2,
    )


def _candidate(option_id: str, price_usd: int) -> FlightCandidate:
    return FlightCandidate(
        option_id=option_id,
        destination_city="City",
        origin_airport="BEG",
        destination_airport="DST",
        price_usd=price_usd,
        departure_date=date(2026, 6, 10),
        return_date=date(2026, 6, 17),
        themes=frozenset({"beach", "history"}),
    )


class _FakeProvider(LLMProvider):
    def __init__(self, response_text: str | None = None, error: Exception | None = None) -> None:
        self.response_text = response_text
        self.error = error

    def complete(self, *, system_prompt: str, user_prompt: str, output_model):  # noqa: ANN001
        if self.error is not None:
            raise self.error
        assert system_prompt
        assert user_prompt
        assert output_model.__name__ == "_LLMRankingOutputSchema"
        assert self.response_text is not None
        return self.response_text


def test_rank_success_with_valid_schema() -> None:
    output_text = json.dumps(
        {
            "ranked_options": [
                {"option_id": "opt2", "reason": "Best thematic fit."},
                {"option_id": "opt1", "reason": "Strong price/value."},
                {"option_id": "opt3", "reason": "Good overall balance."},
            ]
        }
    )
    ranker = RankingService(llm_provider=_FakeProvider(response_text=output_text))

    output = ranker.rank(
        to_trip_preferences(_payload()),
        [_candidate("opt1", 620), _candidate("opt2", 570), _candidate("opt3", 700)],
    )

    assert [item.option_id for item in output.ranked_options] == ["opt2", "opt1", "opt3"]


def test_rank_rejects_unknown_option_id() -> None:
    output_text = json.dumps(
        {
            "ranked_options": [
                {"option_id": "opt2", "reason": "Good."},
                {"option_id": "opt1", "reason": "Good."},
                {"option_id": "foreign", "reason": "Good."},
            ]
        }
    )
    ranker = RankingService(llm_provider=_FakeProvider(response_text=output_text))

    with pytest.raises(LLMResponseValidationError):
        ranker.rank(
            to_trip_preferences(_payload()),
            [_candidate("opt1", 620), _candidate("opt2", 570), _candidate("opt3", 700)],
        )


def test_rank_bubbles_provider_errors() -> None:
    ranker = RankingService(llm_provider=_FakeProvider(error=LLMProviderError("timeout")))

    with pytest.raises(LLMProviderError):
        ranker.rank(
            to_trip_preferences(_payload()),
            [_candidate("opt1", 620), _candidate("opt2", 570), _candidate("opt3", 700)],
        )
