from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_current_user,
    get_optional_current_user,
    get_search_api_service,
)
from app.api.schemas.search.reaction import SuggestionReactionRequest, SuggestionReactionResponse
from app.api.schemas.search.request import SearchRequest
from app.api.schemas.search.response import SearchResponse
from app.api.services.search_api_service import SearchApiService
from app.application.services.auth_service import AuthenticatedUser

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    service: Annotated[SearchApiService, Depends(get_search_api_service)],
    current_user: Annotated[AuthenticatedUser | None, Depends(get_optional_current_user)],
) -> SearchResponse:
    return service.run_search(
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/search/suggestions/{suggestion_id}/reaction",
    response_model=SuggestionReactionResponse,
)
def react_to_suggestion(
    suggestion_id: str,
    payload: SuggestionReactionRequest,
    service: Annotated[SearchApiService, Depends(get_search_api_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> SuggestionReactionResponse:
    return service.react_to_suggestion(
        suggestion_id=suggestion_id,
        reaction=payload.reaction,
        current_user=current_user,
    )
