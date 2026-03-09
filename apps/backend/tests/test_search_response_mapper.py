from app.api.schemas.search_response import SearchResponse
from app.application.dto.search_result import SearchMetaResult, SearchOptionResult, SearchResult
from app.core.types import RankingMode, SearchDataSource


def test_search_response_from_contract_maps_fields() -> None:
    result = SearchResult(
        options=[
            SearchOptionResult(
                option_id="opt_001",
                destination_city="Barcelona",
                origin_airport="BEG",
                destination_airport="BCN",
                price_usd=640,
                score=0.92,
                reason="Strong thematic fit.",
            ),
            SearchOptionResult(
                option_id="opt_002",
                destination_city="Athens",
                origin_airport="BEG",
                destination_airport="ATH",
                price_usd=590,
                score=0.88,
                reason="Balanced value.",
            ),
            SearchOptionResult(
                option_id="opt_003",
                destination_city="Lisbon",
                origin_airport="BEG",
                destination_airport="LIS",
                price_usd=710,
                score=0.84,
                reason="Good fallback.",
            ),
        ],
        meta=SearchMetaResult(
            data_source=SearchDataSource.fallback,
            ranking_mode=RankingMode.deterministic,
            constraints_relaxed=True,
            fallback_reasons=["provider fallback: timeout"],
        ),
    )

    response = SearchResponse.from_contract(result)

    assert response.meta.data_source == SearchDataSource.fallback
    assert response.meta.ranking_mode == RankingMode.deterministic
    assert response.meta.constraints_relaxed is True
    assert response.meta.fallback_reasons == ["provider fallback: timeout"]
    assert [item.option_id for item in response.options] == ["opt_001", "opt_002", "opt_003"]


def test_search_response_from_contract_accepts_less_than_three_options() -> None:
    result = SearchResult(
        options=[
            SearchOptionResult(
                option_id="opt_001",
                destination_city="Barcelona",
                origin_airport="BEG",
                destination_airport="BCN",
                price_usd=640,
                score=0.92,
                reason="Strong thematic fit.",
            ),
            SearchOptionResult(
                option_id="opt_002",
                destination_city="Athens",
                origin_airport="BEG",
                destination_airport="ATH",
                price_usd=590,
                score=0.88,
                reason="Balanced value.",
            ),
        ],
        meta=SearchMetaResult(
            data_source=SearchDataSource.live,
            ranking_mode=RankingMode.deterministic,
            constraints_relaxed=True,
            fallback_reasons=["returned fewer than 3 matches after filters"],
        ),
    )

    response = SearchResponse.from_contract(result)

    assert len(response.options) == 2
