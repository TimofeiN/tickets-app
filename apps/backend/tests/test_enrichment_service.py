import json
from datetime import date

from app.application.services.enrichment_service import (
    EnrichmentContext,
    EnrichmentService,
    build_empty_enrichment,
)
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences
from app.shared.enums import DatesMode


def _preferences() -> TripPreferences:
    return TripPreferences(
        origin_city="Belgrade",
        dates_mode=DatesMode.strict,
        themes=("beach", "history", "family"),
        budget_usd=2000,
        travelers_count=2,
        strict_start_date=date(2026, 6, 10),
        strict_end_date=date(2026, 6, 17),
    )


def _candidates() -> list[FlightCandidate]:
    return [
        FlightCandidate(
            option_id="opt1",
            destination_city="Barcelona",
            origin_airport="BEG",
            destination_airport="BCN",
            price_usd=640,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
            themes=frozenset({"beach", "history", "nightlife"}),
        ),
        FlightCandidate(
            option_id="opt2",
            destination_city="Tivat",
            origin_airport="BEG",
            destination_airport="TIV",
            price_usd=320,
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 17),
            themes=frozenset({"beach", "family", "active_summer"}),
        ),
    ]


def _context() -> EnrichmentContext:
    return EnrichmentContext(
        selected_count=2,
        filtered_count=2,
        constraints_relaxed=False,
        data_source="live",
        ranking_mode="llm",
    )


class _FakeProvider:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def complete(self, *, system_prompt: str, user_prompt: str, output_model):  # noqa: ANN001
        assert system_prompt
        assert user_prompt
        assert output_model.__name__ == "_LLMEnrichmentOutputSchema"
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.payload


def test_enrichment_service_maps_llm_response() -> None:
    provider = _FakeProvider(
        json.dumps(
            {
                "options": [
                    {
                        "option_id": "opt1",
                        "theme_explanation": "Beach and history are the core match.",
                        "highlights": [
                            {"text": "Strong beach and city mix"},
                            {"text": "Good summer energy"},
                        ],
                        "tradeoff": "Family fit is weaker than city energy.",
                        "caveat": "Less calm than a slower family beach trip.",
                        "trip_style": "Coastal city break",
                        "vibe": "Lively coastal energy",
                    },
                    {
                        "option_id": "opt2",
                        "theme_explanation": "Beach and family fit lead the value here.",
                        "highlights": [
                            {"text": "Family-friendly coastline"},
                        ],
                        "tradeoff": "History depth is weaker than comfort and sea time.",
                        "caveat": "Less suitable if culture is the main driver.",
                        "trip_style": "Family beach holiday",
                        "vibe": "Easy family-friendly pace",
                    },
                ],
                "guidance": {
                    "improvement_hint": "Raise budget slightly for stronger coastal choices.",
                    "counterfactual": (
                        "If nightlife matters most, the city-heavy option becomes stronger."
                    ),
                },
            }
        )
    )
    service = EnrichmentService(provider)

    enrichment = service.enrich(_preferences(), _candidates(), _context())

    assert enrichment.insights_by_option_id["opt1"].trip_style == "Coastal city break"
    assert enrichment.insights_by_option_id["opt2"].vibe == "Easy family-friendly pace"
    assert enrichment.insights_by_option_id["opt1"].highlights == (
        "Strong beach and city mix",
        "Good summer energy",
    )
    assert enrichment.guidance.improvement_hint.startswith("Raise budget slightly")

    assert provider.last_system_prompt is not None
    assert "Do not invent attractions" in provider.last_system_prompt
    assert "theme_explanation must connect the user's selected themes" in (
        provider.last_system_prompt
    )

    assert provider.last_user_prompt is not None
    request_payload = json.loads(provider.last_user_prompt)
    assert request_payload["request"]["themes"] == [
        {
            "key": "beach",
            "intent": "sea time, warm-weather ease, and a beach-centered trip rhythm",
        },
        {
            "key": "family",
            "intent": "comfort, calmer pacing, and easy planning for a family-style trip",
        },
        {
            "key": "history",
            "intent": "old-city atmosphere, culture, and time around historic places",
        },
    ]


def test_build_empty_enrichment_returns_blank_business_fields() -> None:
    enrichment = build_empty_enrichment(_preferences(), _candidates(), _context())

    assert set(enrichment.insights_by_option_id) == {"opt1", "opt2"}
    assert enrichment.insights_by_option_id["opt1"].theme_explanation == ""
    assert enrichment.insights_by_option_id["opt1"].highlights == ()
    assert enrichment.insights_by_option_id["opt1"].tradeoff == ""
    assert enrichment.insights_by_option_id["opt1"].caveat == ""
    assert enrichment.insights_by_option_id["opt1"].trip_style == ""
    assert enrichment.insights_by_option_id["opt1"].vibe == ""
    assert enrichment.guidance.improvement_hint == ""
    assert enrichment.guidance.counterfactual == ""
