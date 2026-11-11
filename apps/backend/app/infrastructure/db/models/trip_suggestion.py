from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class TripSuggestion(SQLModel, table=True):
    __tablename__ = "trip_suggestion"
    __table_args__ = (
        sa.UniqueConstraint(
            "query_key",
            "option_id",
            name="uq_trip_suggestion_query_option",
        ),
    )

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    query_key: str = Field(nullable=False, max_length=64, index=True)
    origin_city: str = Field(nullable=False, max_length=120)
    start_date: date = Field(nullable=False)
    end_date: date = Field(nullable=False)
    budget_usd: int = Field(nullable=False)
    travelers_count: int = Field(nullable=False, default=2)
    themes: list[str] = Field(
        sa_column=sa.Column(sa.JSON(), nullable=False),
    )
    option_id: str = Field(nullable=False, max_length=120)
    destination_city: str = Field(nullable=False, max_length=160)
    origin_airport: str = Field(nullable=False, max_length=16)
    destination_airport: str = Field(nullable=False, max_length=16)
    price_usd: int = Field(nullable=False)
    score: float = Field(nullable=False, default=0.0)
    reason: str = Field(nullable=False, default="", max_length=2000)
    trip_plan: str = Field(nullable=False, default="", max_length=12000)
    likes: int = Field(nullable=False, default=0)
    dislikes: int = Field(nullable=False, default=0)
    created_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
