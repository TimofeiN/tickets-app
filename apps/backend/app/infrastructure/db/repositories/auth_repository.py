from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, select

from app.core.errors import AccountAlreadyExistsError, DataAccessError
from app.infrastructure.db.models.user_account import UserAccount
from app.infrastructure.db.models.user_session import UserSession

logger = logging.getLogger(__name__)


class AuthRepository:
    def __init__(self, *, session: Session) -> None:
        self.session = session

    def create_user(self, *, email: str, password_hash: str) -> UserAccount:
        user = UserAccount(
            email=email,
            password_hash=password_hash,
        )
        try:
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            return user
        except IntegrityError as exc:
            self.session.rollback()
            logger.info("auth_repository_create_user_conflict email=%s", email)
            raise AccountAlreadyExistsError("email already exists") from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("auth_repository_create_user_failed reason=%s", str(exc))
            raise DataAccessError("user create failed") from exc

    def find_user_by_email(self, *, email: str) -> UserAccount | None:
        try:
            return self.session.exec(select(UserAccount).where(UserAccount.email == email)).first()
        except SQLAlchemyError as exc:
            logger.exception("auth_repository_find_user_by_email_failed reason=%s", str(exc))
            raise DataAccessError("user lookup failed") from exc

    def find_user_by_id(self, *, user_id: str) -> UserAccount | None:
        try:
            return self.session.get(UserAccount, user_id)
        except SQLAlchemyError as exc:
            logger.exception("auth_repository_find_user_by_id_failed reason=%s", str(exc))
            raise DataAccessError("user lookup failed") from exc

    def touch_last_login(self, *, user_id: str, logged_in_at: datetime) -> None:
        try:
            user = self.session.get(UserAccount, user_id)
            if user is None:
                return
            user.last_login_at = logged_in_at
            self.session.add(user)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("auth_repository_touch_last_login_failed reason=%s", str(exc))
            raise DataAccessError("user update failed") from exc

    def create_session(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> UserSession:
        session_model = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        try:
            self.session.add(session_model)
            self.session.commit()
            self.session.refresh(session_model)
            return session_model
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("auth_repository_create_session_failed reason=%s", str(exc))
            raise DataAccessError("session create failed") from exc

    def find_user_by_token_hash(
        self,
        *,
        token_hash: str,
        now: datetime,
    ) -> UserAccount | None:
        try:
            session_model = self.session.exec(
                select(UserSession).where(UserSession.token_hash == token_hash)
            ).first()
            expires_at = _normalize_datetime(session_model.expires_at) if session_model else None
            if (
                session_model is None
                or expires_at is None
                or expires_at <= _normalize_datetime(now)
            ):
                return None
            return self.session.get(UserAccount, session_model.user_id)
        except SQLAlchemyError as exc:
            logger.exception("auth_repository_find_user_by_token_hash_failed reason=%s", str(exc))
            raise DataAccessError("session lookup failed") from exc

    def delete_session_by_token_hash(self, *, token_hash: str) -> None:
        try:
            session_model = self.session.exec(
                select(UserSession).where(UserSession.token_hash == token_hash)
            ).first()
            if session_model is None:
                return
            self.session.delete(session_model)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("auth_repository_delete_session_failed reason=%s", str(exc))
            raise DataAccessError("session delete failed") from exc


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
