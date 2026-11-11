from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from app.core.errors import DataAccessError, TripSuggestionNotFoundError
from app.infrastructure.db.models.trip_suggestion import TripSuggestion
from app.infrastructure.db.models.trip_suggestion_reaction import TripSuggestionReaction
from app.shared.enums import ReactionType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TripSuggestionOptionData:
    option_id: str
    destination_city: str
    origin_airport: str
    destination_airport: str
    price_usd: int
    score: float
    reason: str
    trip_plan: str


class TripSuggestionRepository:
    def __init__(self, *, session: Session) -> None:
        self.session = session

    def list_top_for_query(
        self,
        *,
        query_key: str,
        limit: int = 3,
    ) -> list[TripSuggestion]:
        try:
            rating_expr = col(TripSuggestion.likes) - col(TripSuggestion.dislikes)
            statement = (
                select(TripSuggestion)
                .where(TripSuggestion.query_key == query_key)
                .order_by(
                    rating_expr.desc(),
                    col(TripSuggestion.likes).desc(),
                    col(TripSuggestion.created_at).desc(),
                )
                .limit(limit)
            )
            return list(self.session.exec(statement).all())
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("trip_suggestion_repository_list_failed reason=%s", str(exc))
            raise DataAccessError("trip suggestion list failed") from exc

    def save_suggestions(
        self,
        *,
        query_key: str,
        origin_city: str,
        start_date: date,
        end_date: date,
        budget_usd: int,
        travelers_count: int,
        themes: list[str],
        options: list[TripSuggestionOptionData],
    ) -> list[TripSuggestion]:
        saved: list[TripSuggestion] = []
        try:
            for item in options:
                existing = self._find_existing_option(
                    query_key=query_key,
                    option_id=item.option_id,
                )
                if existing is not None:
                    saved.append(existing)
                    continue

                suggestion = TripSuggestion(
                    query_key=query_key,
                    origin_city=origin_city,
                    start_date=start_date,
                    end_date=end_date,
                    budget_usd=budget_usd,
                    travelers_count=travelers_count,
                    themes=themes,
                    option_id=item.option_id,
                    destination_city=item.destination_city,
                    origin_airport=item.origin_airport,
                    destination_airport=item.destination_airport,
                    price_usd=item.price_usd,
                    score=item.score,
                    reason=item.reason,
                    trip_plan=item.trip_plan,
                )
                self.session.add(suggestion)
                saved.append(suggestion)

            self.session.commit()
            for saved_item in saved:
                self.session.refresh(saved_item)
            return saved
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("trip_suggestion_repository_save_failed reason=%s", str(exc))
            raise DataAccessError("trip suggestion save failed") from exc

    def record_reaction(
        self,
        *,
        user_id: str,
        suggestion_id: str,
        reaction: ReactionType,
    ) -> TripSuggestion:
        try:
            suggestion = self.session.get(TripSuggestion, suggestion_id)
            if suggestion is None:
                raise TripSuggestionNotFoundError("trip suggestion not found")

            reaction_row = self._find_user_reaction(
                user_id=user_id,
                suggestion_id=suggestion_id,
            )

            if reaction_row is None:
                reaction_row = TripSuggestionReaction(
                    user_id=user_id,
                    suggestion_id=suggestion_id,
                    reaction=reaction,
                )
                self.session.add(reaction_row)
                self._increment_reaction_counter(suggestion=suggestion, reaction=reaction)
            elif reaction_row.reaction != reaction:
                self._decrement_reaction_counter(
                    suggestion=suggestion,
                    reaction=reaction_row.reaction,
                )
                self._increment_reaction_counter(suggestion=suggestion, reaction=reaction)
                reaction_row.reaction = reaction

            self.session.add(suggestion)
            self.session.commit()
            self.session.refresh(suggestion)
            return suggestion
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("trip_suggestion_repository_reaction_failed reason=%s", str(exc))
            raise DataAccessError("trip suggestion reaction failed") from exc

    def _find_existing_option(
        self,
        *,
        query_key: str,
        option_id: str,
    ) -> TripSuggestion | None:
        statement = select(TripSuggestion).where(
            TripSuggestion.query_key == query_key,
            TripSuggestion.option_id == option_id,
        )
        return self.session.exec(statement).first()

    def _find_user_reaction(
        self,
        *,
        user_id: str,
        suggestion_id: str,
    ) -> TripSuggestionReaction | None:
        statement = select(TripSuggestionReaction).where(
            TripSuggestionReaction.user_id == user_id,
            TripSuggestionReaction.suggestion_id == suggestion_id,
        )
        return self.session.exec(statement).first()

    @staticmethod
    def _increment_reaction_counter(
        *,
        suggestion: TripSuggestion,
        reaction: ReactionType,
    ) -> None:
        if reaction == ReactionType.like:
            suggestion.likes += 1
            return
        suggestion.dislikes += 1

    @staticmethod
    def _decrement_reaction_counter(
        *,
        suggestion: TripSuggestion,
        reaction: ReactionType,
    ) -> None:
        if reaction == ReactionType.like and suggestion.likes > 0:
            suggestion.likes -= 1
            return
        if reaction == ReactionType.dislike and suggestion.dislikes > 0:
            suggestion.dislikes -= 1
