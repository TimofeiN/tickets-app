from __future__ import annotations

import os


def get_database_dsn() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://tickets_user:tickets_password@postgres:5432/tickets_app",
    )


def get_llm_shortlist_limit() -> int:
    raw = os.getenv("LLM_SHORTLIST_LIMIT", "8")
    try:
        value = int(raw)
    except ValueError:
        return 8
    return max(3, min(value, 12))
