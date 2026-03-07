from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

_ENGINE: Engine | None = None


def get_database_dsn() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://tickets_user:tickets_password@postgres:5432/tickets_app",
    )


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(get_database_dsn(), pool_pre_ping=True)
    return _ENGINE


@contextmanager
def get_session() -> Session:
    with Session(get_engine()) as session:
        yield session
