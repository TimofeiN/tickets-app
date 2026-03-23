from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class UserAccount(SQLModel, table=True):
    __tablename__ = "user_account"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    email: str = Field(index=True, unique=True, nullable=False, max_length=320)
    password_hash: str = Field(nullable=False, max_length=512)
    created_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    last_login_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True),
    )
