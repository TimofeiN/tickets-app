from __future__ import annotations

import json
from datetime import date

import pytest
from pydantic import ValidationError

from app.api.mappers.trip_preferences_mapper import to_trip_preferences
from app.api.schemas.search.request import SearchRequest
from app.application.dto.search_pipeline import FactualShortlistedOption
from app.application.ports.llm_provider import LLMProvider, LLMProviderError
from app.application.services.semantic_scoring_service import (
    LLMResponseValidationError,
    SemanticScoringService,
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


def _candidate(option_id: str, price_usd: int) -> FactualShortlistedOption:
    return FactualShortlistedOption(
        candidate=FlightCandidate(
            option_id=option_id,
            destination_city="City",
            origin_airport="BEG",
            destination_airport="DST",
            price_usd=price_usd,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
            themes=frozenset(),
        ),
        factual_score=0.75,
    )


class _FakeProvider(LLMProvider):
    def __init__(self, response_text: str | None = None, error: Exception | None = None) -> None:
        self.response_text = response_text
        self.error = error

    def complete(self, *, system_prompt: str, user_prompt: str, output_model):
        if self.error is not None:
            raise self.error
        assert system_prompt
        assert user_prompt
        assert output_model.__name__ == "_SemanticScoringOutputSchema"
        assert self.response_text is not None
        return self.response_text


def test_score_success_with_valid_schema() -> None:
    output_text = json.dumps(
        {
            "scores": [
                {
                    "option_id": "opt1",
                    "theme_fit_score": 0.82,
                    "confidence": 0.71,
                    "matched_themes": ["beach", "history"],
                    "reason_short": "Strong fit for beach and history.",
                },
                {
                    "option_id": "opt2",
                    "theme_fit_score": 0.74,
                    "confidence": 0.66,
                    "matched_themes": ["history"],
                    "reason_short": "Better for history than beach.",
                },
                {
                    "option_id": "opt3",
                    "theme_fit_score": 0.61,
                    "confidence": 0.58,
                    "matched_themes": ["beach"],
                    "reason_short": "Reasonable beach-oriented fallback.",
                },
            ]
        }
    )
    output = SemanticScoringService.score(
        llm_provider=_FakeProvider(response_text=output_text),
        preferences=to_trip_preferences(_payload()),
        shortlist=[_candidate("opt1", 620), _candidate("opt2", 570), _candidate("opt3", 700)],
    )

    assert [item.option_id for item in output.scores] == ["opt1", "opt2", "opt3"]
    assert output.scores[0].matched_themes == ("beach", "history")


def test_score_rejects_unknown_option_id() -> None:
    output_text = json.dumps(
        {
            "scores": [
                {
                    "option_id": "opt1",
                    "theme_fit_score": 0.82,
                    "confidence": 0.71,
                    "matched_themes": ["beach"],
                    "reason_short": "Good.",
                },
                {
                    "option_id": "opt2",
                    "theme_fit_score": 0.74,
                    "confidence": 0.66,
                    "matched_themes": ["history"],
                    "reason_short": "Good.",
                },
                {
                    "option_id": "foreign",
                    "theme_fit_score": 0.61,
                    "confidence": 0.58,
                    "matched_themes": [],
                    "reason_short": "Good.",
                },
            ]
        }
    )
    with pytest.raises(LLMResponseValidationError):
        SemanticScoringService.score(
            llm_provider=_FakeProvider(response_text=output_text),
            preferences=to_trip_preferences(_payload()),
            shortlist=[_candidate("opt1", 620), _candidate("opt2", 570), _candidate("opt3", 700)],
        )


def test_score_rejects_invalid_score_range() -> None:
    output_text = json.dumps(
        {
            "scores": [
                {
                    "option_id": "opt1",
                    "theme_fit_score": 1.2,
                    "confidence": 0.71,
                    "matched_themes": ["beach"],
                    "reason_short": "Good.",
                }
            ]
        }
    )
    with pytest.raises(ValidationError):
        SemanticScoringService.score(
            llm_provider=_FakeProvider(response_text=output_text),
            preferences=to_trip_preferences(_payload()),
            shortlist=[_candidate("opt1", 620)],
        )


def test_score_bubbles_provider_errors() -> None:
    with pytest.raises(LLMProviderError):
        SemanticScoringService.score(
            llm_provider=_FakeProvider(error=LLMProviderError("timeout")),
            preferences=to_trip_preferences(_payload()),
            shortlist=[_candidate("opt1", 620), _candidate("opt2", 570), _candidate("opt3", 700)],
        )
