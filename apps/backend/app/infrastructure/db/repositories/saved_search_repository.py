from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from app.core.errors import DataAccessError
from app.infrastructure.db.models.saved_search import SavedSearch

logger = logging.getLogger(__name__)


class SavedSearchRepository:
    def __init__(self, *, session: Session) -> None:
        self.session = session

    def create_saved_search(
        self,
        *,
        user_id: str,
        origin_city: str,
        start_date: date,
        end_date: date,
        budget_usd: int,
        themes: list[str],
        summary_destination: str | None,
        summary_price_usd: int | None,
        options_count: int,
        request_payload: dict[str, object],
        response_payload: dict[str, object],
    ) -> SavedSearch:
        saved_search = SavedSearch(
            user_id=user_id,
            origin_city=origin_city,
            start_date=start_date,
            end_date=end_date,
            budget_usd=budget_usd,
            themes=themes,
            summary_destination=summary_destination,
            summary_price_usd=summary_price_usd,
            options_count=options_count,
            request_payload=request_payload,
            response_payload=response_payload,
        )
        try:
            self.session.add(saved_search)
            self.session.commit()
            self.session.refresh(saved_search)
            return saved_search
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("saved_search_repository_create_failed reason=%s", str(exc))
            raise DataAccessError("saved search create failed") from exc

    def list_for_user(self, *, user_id: str, limit: int = 20) -> list[SavedSearch]:
        try:
            statement = (
                select(SavedSearch)
                .where(SavedSearch.user_id == user_id)
                .order_by(col(SavedSearch.created_at).desc())
                .limit(limit)
            )
            return list(self.session.exec(statement).all())
        except SQLAlchemyError as exc:
            logger.exception("saved_search_repository_list_failed reason=%s", str(exc))
            raise DataAccessError("saved search list failed") from exc

    def find_for_user(self, *, user_id: str, saved_search_id: str) -> SavedSearch | None:
        try:
            statement = select(SavedSearch).where(
                SavedSearch.user_id == user_id,
                SavedSearch.id == saved_search_id,
            )
            return self.session.exec(statement).first()
        except SQLAlchemyError as exc:
            logger.exception("saved_search_repository_find_failed reason=%s", str(exc))
            raise DataAccessError("saved search lookup failed") from exc
