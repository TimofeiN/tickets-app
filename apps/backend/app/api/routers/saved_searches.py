from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_saved_search_api_service
from app.api.schemas.search.saved import (
    SavedSearchDetailResponse,
    SavedSearchSummaryResponse,
)
from app.api.services.saved_search_api_service import SavedSearchApiService
from app.application.services.auth_service import AuthenticatedUser

router = APIRouter(tags=["saved-searches"])


@router.get("/searches", response_model=list[SavedSearchSummaryResponse])
def list_saved_searches(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SavedSearchApiService, Depends(get_saved_search_api_service)],
) -> list[SavedSearchSummaryResponse]:
    return service.list_saved_searches(current_user=current_user)


@router.get("/searches/{saved_search_id}", response_model=SavedSearchDetailResponse)
def get_saved_search(
    saved_search_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SavedSearchApiService, Depends(get_saved_search_api_service)],
) -> SavedSearchDetailResponse:
    return service.get_saved_search(
        current_user=current_user,
        saved_search_id=saved_search_id,
    )
