from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.errors import AuthenticationRequiredError, InvalidCredentialsError
from app.infrastructure.db.models.user_account import UserAccount
from app.infrastructure.db.repositories.auth_repository import AuthRepository

SESSION_TTL_DAYS = 30
PASSWORD_SALT_BYTES = 16
TOKEN_BYTES = 32


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str


@dataclass(frozen=True)
class AuthSessionResult:
    access_token: str
    user: AuthenticatedUser


class AuthService:
    def __init__(self, *, repository: AuthRepository) -> None:
        self.repository = repository

    def register(self, *, email: str, password: str) -> AuthSessionResult:
        normalized_email = _normalize_email(email)
        password_hash = _hash_password(password)
        user = self.repository.create_user(
            email=normalized_email,
            password_hash=password_hash,
        )
        return self._create_session_for_user(user)

    def login(self, *, email: str, password: str) -> AuthSessionResult:
        normalized_email = _normalize_email(email)
        user = self.repository.find_user_by_email(email=normalized_email)
        if user is None or not _verify_password(password, user.password_hash):
            raise InvalidCredentialsError("invalid login credentials")
        return self._create_session_for_user(user)

    def authenticate(self, *, access_token: str | None) -> AuthenticatedUser:
        if not access_token:
            raise AuthenticationRequiredError("missing access token")

        user = self.repository.find_user_by_token_hash(
            token_hash=_hash_token(access_token),
            now=datetime.now(UTC),
        )
        if user is None:
            raise AuthenticationRequiredError("invalid access token")
        return AuthenticatedUser(id=user.id, email=user.email)

    def authenticate_optional(self, *, access_token: str | None) -> AuthenticatedUser | None:
        if not access_token:
            return None
        user = self.repository.find_user_by_token_hash(
            token_hash=_hash_token(access_token),
            now=datetime.now(UTC),
        )
        if user is None:
            return None
        return AuthenticatedUser(id=user.id, email=user.email)

    def logout(self, *, access_token: str | None) -> None:
        if not access_token:
            return
        self.repository.delete_session_by_token_hash(token_hash=_hash_token(access_token))

    def _create_session_for_user(self, user: UserAccount) -> AuthSessionResult:
        access_token = secrets.token_urlsafe(TOKEN_BYTES)
        logged_in_at = datetime.now(UTC)
        self.repository.create_session(
            user_id=user.id,
            token_hash=_hash_token(access_token),
            expires_at=logged_in_at + timedelta(days=SESSION_TTL_DAYS),
        )
        self.repository.touch_last_login(user_id=user.id, logged_in_at=logged_in_at)
        return AuthSessionResult(
            access_token=access_token,
            user=AuthenticatedUser(id=user.id, email=user.email),
        )


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    hashed = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return f"{salt.hex()}:{hashed.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_hex, hash_hex = password_hash.split(":", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
    except ValueError:
        return False

    actual_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
