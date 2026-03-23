from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class UserSession(SQLModel, table=True):
    __tablename__ = "user_session"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    user_id: str = Field(foreign_key="user_account.id", nullable=False, index=True)
    token_hash: str = Field(index=True, unique=True, nullable=False, max_length=128)
    expires_at: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )
    created_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
