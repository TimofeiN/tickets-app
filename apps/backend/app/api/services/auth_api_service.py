from __future__ import annotations

from app.api.schemas.auth.requests import AuthCredentialsRequest
from app.api.schemas.auth.responses import AuthSessionResponse, AuthUserResponse
from app.application.services.auth_service import AuthenticatedUser, AuthService


class AuthApiService:
    def __init__(self, *, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    def register(self, payload: AuthCredentialsRequest) -> AuthSessionResponse:
        result = self.auth_service.register(email=payload.email, password=payload.password)
        return AuthSessionResponse(
            access_token=result.access_token,
            user=AuthUserResponse(id=result.user.id, email=result.user.email),
        )

    def login(self, payload: AuthCredentialsRequest) -> AuthSessionResponse:
        result = self.auth_service.login(email=payload.email, password=payload.password)
        return AuthSessionResponse(
            access_token=result.access_token,
            user=AuthUserResponse(id=result.user.id, email=result.user.email),
        )

    @staticmethod
    def current_user_response(current_user: AuthenticatedUser) -> AuthUserResponse:
        return AuthUserResponse(id=current_user.id, email=current_user.email)

    def logout(self, *, access_token: str | None) -> dict[str, str]:
        self.auth_service.logout(access_token=access_token)
        return {"status": "ok"}
