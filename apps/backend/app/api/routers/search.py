from fastapi import APIRouter, Depends

from app.api.deps import get_search_service
from app.api.mappers.trip_preferences_mapper import to_trip_preferences
from app.api.schemas.search_request import SearchRequest
from app.api.schemas.search_response import SearchResponse
from app.application.services.search_service import SearchService

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    preferences = to_trip_preferences(payload)
    result = service.search(preferences)
    return SearchResponse.from_contract(result)
