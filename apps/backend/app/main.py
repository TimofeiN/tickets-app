from fastapi import FastAPI

from app.middleware import setup_middleware
from app.schemas import FlightOption, SearchRequest, SearchResponse

app = FastAPI(title="tickets_app backend", version="0.1.0")
setup_middleware(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest) -> SearchResponse:
    # MVP mock response to unblock FE integration and API contract discussion.
    _ = payload
    options = [
        FlightOption(
            option_id="opt_bcn_001",
            destination_city="Barcelona",
            origin_airport="BEG",
            destination_airport="BCN",
            price_usd=640,
            score=0.92,
            reason="Beach + culture fit and good weather in selected window.",
        ),
        FlightOption(
            option_id="opt_ath_002",
            destination_city="Athens",
            origin_airport="BEG",
            destination_airport="ATH",
            price_usd=590,
            score=0.88,
            reason="History + gastronomy fit with balanced budget usage.",
        ),
        FlightOption(
            option_id="opt_lis_003",
            destination_city="Lisbon",
            origin_airport="BEG",
            destination_airport="LIS",
            price_usd=710,
            score=0.84,
            reason="Strong nightlife and city activities within total budget.",
        ),
    ]
    return SearchResponse(options=options)
