from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.core.settings import settings

_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(settings.database_dsn, pool_pre_ping=True)
    return _ENGINE


@contextmanager
def get_session() -> Session:
    with Session(get_engine()) as session:
        yield session
