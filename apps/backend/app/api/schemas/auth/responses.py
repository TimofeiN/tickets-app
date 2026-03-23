from __future__ import annotations

from pydantic import BaseModel


class AuthUserResponse(BaseModel):
    id: str
    email: str


class AuthSessionResponse(BaseModel):
    access_token: str
    user: AuthUserResponse
