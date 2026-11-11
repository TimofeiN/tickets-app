from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.shared.enums import ReactionType


class TripSuggestionReaction(SQLModel, table=True):
    __tablename__ = "trip_suggestion_reaction"
    __table_args__ = (
        sa.UniqueConstraint(
            "user_id",
            "suggestion_id",
            name="uq_trip_suggestion_reaction_user_suggestion",
        ),
    )

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    user_id: str = Field(
        sa_column=sa.Column(
            sa.Text(),
            sa.ForeignKey("user_account.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    suggestion_id: str = Field(
        sa_column=sa.Column(
            sa.Text(),
            sa.ForeignKey("trip_suggestion.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    reaction: ReactionType = Field(
        sa_column=sa.Column(
            sa.Enum(ReactionType, native_enum=False, length=16),
            nullable=False,
        )
    )
    created_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
