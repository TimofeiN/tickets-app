from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_optional_current_user,
    get_search_api_service,
)
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
