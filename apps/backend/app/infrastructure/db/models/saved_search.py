from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class SavedSearch(SQLModel, table=True):
    __tablename__ = "saved_search"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    user_id: str = Field(foreign_key="user_account.id", nullable=False, index=True)
    origin_city: str = Field(nullable=False, max_length=120)
    start_date: date = Field(nullable=False)
    end_date: date = Field(nullable=False)
    budget_usd: int = Field(nullable=False)
    themes: list[str] = Field(
        sa_column=sa.Column(sa.JSON(), nullable=False),
    )
    summary_destination: str | None = Field(default=None, nullable=True, max_length=160)
    summary_price_usd: int | None = Field(default=None, nullable=True)
    options_count: int = Field(nullable=False, default=0)
    request_payload: dict[str, object] = Field(
        sa_column=sa.Column(sa.JSON(), nullable=False),
    )
    response_payload: dict[str, object] = Field(
        sa_column=sa.Column(sa.JSON(), nullable=False),
    )
    created_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
