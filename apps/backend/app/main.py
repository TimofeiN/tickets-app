from fastapi import FastAPI

from app.logging import configure_logging
from app.middleware import setup_middleware
from app.providers.travelpayouts import TravelpayoutsClient
from app.schemas import FlightOption, SearchRequest, SearchResponse
from app.services.filtering import (
    build_reason,
    filter_candidates,
    pick_with_fallback,
    score_candidate,
)
from app.services.iata_resolver import IataCityResolver

configure_logging()
app = FastAPI(title="tickets_app backend", version="0.1.0")
setup_middleware(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest) -> SearchResponse:
    provider = TravelpayoutsClient.from_env()
    all_candidates = provider.get_candidates(payload)

    filtered_candidates = filter_candidates(all_candidates, payload)
    selected_candidates = pick_with_fallback(filtered_candidates, all_candidates, payload)
    city_names_by_iata = IataCityResolver().resolve_city_names(
        [candidate.destination_airport for candidate in selected_candidates]
    )

    options = [
        FlightOption(
            option_id=candidate.option_id,
            destination_city=city_names_by_iata.get(
                candidate.destination_airport.upper(),
                candidate.destination_city,
            ),
            origin_airport=candidate.origin_airport,
            destination_airport=candidate.destination_airport,
            price_usd=candidate.price_usd,
            score=score_candidate(candidate, payload),
            reason=build_reason(candidate, payload),
        )
        for candidate in selected_candidates
    ]

    return SearchResponse(options=options)
