from app.api.schemas.search_response import SearchResponse
from app.application.dto.search_result import (
    SearchGuidanceResult,
    SearchMetaResult,
    SearchOptionResult,
    SearchResult,
)
from app.shared.enums import EnrichmentMode, RankingMode, SearchDataSource


def _option(
    option_id: str,
    destination_airport: str,
    price_usd: int,
    score: float,
) -> SearchOptionResult:
    return SearchOptionResult(
        option_id=option_id,
        destination_city=f"City {destination_airport}",
        origin_airport="BEG",
        destination_airport=destination_airport,
        price_usd=price_usd,
        score=score,
        reason="Strong thematic fit.",
        trip_plan="Day 1: arrival. Day 2: explore.",
        theme_explanation="Theme-led explanation.",
        highlights=("Highlight A", "Highlight B"),
        tradeoff="A clear tradeoff.",
        caveat="A clear caveat.",
        trip_style="City break",
        vibe="Balanced city energy",
    )


def test_search_response_from_contract_maps_fields() -> None:
    result = SearchResult(
        options=[
            _option("opt_001", "BCN", 640, 0.92),
            _option("opt_002", "ATH", 590, 0.88),
            _option("opt_003", "LIS", 710, 0.84),
        ],
        guidance=SearchGuidanceResult(
            improvement_hint="Improve by narrowing the theme mix.",
            counterfactual="If nightlife leads, another city may become stronger.",
        ),
        meta=SearchMetaResult(
            data_source=SearchDataSource.fallback,
            ranking_mode=RankingMode.deterministic,
            enrichment_mode=EnrichmentMode.llm,
            fallback_reasons=["provider_unavailable"],
        ),
        trip_plan="Day 1: arrival. Day 2: explore.",
    )

    response = SearchResponse.from_contract(result)

    assert response.meta.data_source == SearchDataSource.fallback
    assert response.meta.ranking_mode == RankingMode.deterministic
    assert response.meta.enrichment_mode == EnrichmentMode.llm
    assert response.meta.fallback_reasons == ["provider_unavailable"]
    assert [item.option_id for item in response.options] == ["opt_001", "opt_002", "opt_003"]
    assert response.options[0].theme_explanation == "Theme-led explanation."
    assert response.options[0].trip_plan == "Day 1: arrival. Day 2: explore."
    assert response.options[0].highlights == ["Highlight A", "Highlight B"]
    assert response.options[0].trip_style == "City break"
    assert response.guidance.improvement_hint == "Improve by narrowing the theme mix."


def test_search_response_from_contract_accepts_less_than_three_options() -> None:
    result = SearchResult(
        options=[
            _option("opt_001", "BCN", 640, 0.92),
            _option("opt_002", "ATH", 590, 0.88),
        ],
        guidance=SearchGuidanceResult(
            improvement_hint="Improve by narrowing the theme mix.",
            counterfactual="If nightlife leads, another city may become stronger.",
        ),
        meta=SearchMetaResult(
            data_source=SearchDataSource.live,
            ranking_mode=RankingMode.deterministic,
            enrichment_mode=EnrichmentMode.unavailable,
            fallback_reasons=[],
        ),
        trip_plan="",
    )

    response = SearchResponse.from_contract(result)

    assert len(response.options) == 2


def test_search_response_from_contract_allows_single_option() -> None:
    result = SearchResult(
        options=[
            _option("opt_001", "BCN", 640, 0.92),
        ],
        guidance=SearchGuidanceResult(
            improvement_hint="",
            counterfactual="",
        ),
        meta=SearchMetaResult(
            data_source=SearchDataSource.live,
            ranking_mode=RankingMode.deterministic,
            enrichment_mode=EnrichmentMode.unavailable,
            fallback_reasons=[],
        ),
        trip_plan="",
    )

    response = SearchResponse.from_contract(result)

    assert len(response.options) == 1
