from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_access_token, get_auth_api_service, get_current_user
from app.api.schemas.auth.requests import AuthCredentialsRequest
from app.api.schemas.auth.responses import AuthSessionResponse, AuthUserResponse
from app.api.services.auth_api_service import AuthApiService
from app.application.services.auth_service import AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthSessionResponse)
def register(
    payload: AuthCredentialsRequest,
    service: Annotated[AuthApiService, Depends(get_auth_api_service)],
) -> AuthSessionResponse:
    return service.register(payload)


@router.post("/login", response_model=AuthSessionResponse)
def login(
    payload: AuthCredentialsRequest,
    service: Annotated[AuthApiService, Depends(get_auth_api_service)],
) -> AuthSessionResponse:
    return service.login(payload)


@router.get("/me", response_model=AuthUserResponse)
def me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[AuthApiService, Depends(get_auth_api_service)],
) -> AuthUserResponse:
    return service.current_user_response(current_user)


@router.post("/logout")
def logout(
    _current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    access_token: Annotated[str | None, Depends(get_access_token)],
    service: Annotated[AuthApiService, Depends(get_auth_api_service)],
) -> dict[str, str]:
    return service.logout(access_token=access_token)
