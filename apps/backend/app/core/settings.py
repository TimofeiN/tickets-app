from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    database_dsn: str = Field(
        default=("postgresql+psycopg://tickets_user:tickets_password@postgres:5432/tickets_app"),
        alias="DATABASE_URL",
    )

    # tickets provider
    travelpayouts_api_token: str | None = Field(default=None, alias="TRAVELPAYOUTS_API_TOKEN")
    travelpayouts_marker: str | None = Field(default=None, alias="TRAVELPAYOUTS_MARKER")
    travelpayouts_base_url: str = Field(
        default="https://api.travelpayouts.com",
        alias="TRAVELPAYOUTS_BASE_URL",
    )
    travelpayouts_timeout_sec: float = Field(
        default=6.0,
        ge=1.0,
        alias="TRAVELPAYOUTS_TIMEOUT_SEC",
    )
    travelpayouts_data_base_url: str = Field(
        default="https://api.travelpayouts.com/data",
        alias="TRAVELPAYOUTS_DATA_BASE_URL",
    )
    travelpayouts_data_lang: str = Field(default="en", alias="TRAVELPAYOUTS_DATA_LANG")

    # openai provider
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_timeout_sec: float = Field(default=20.0, ge=0.5, alias="OPENAI_TIMEOUT_SEC")
    openai_max_tokens: int = Field(default=300, ge=64, le=1500, alias="OPENAI_MAX_TOKENS")
    openai_retry_count: int = Field(default=1, ge=0, le=3, alias="OPENAI_RETRY_COUNT")
    openai_retry_backoff_ms: int = Field(
        default=150,
        ge=50,
        le=5000,
        alias="OPENAI_RETRY_BACKOFF_MS",
    )

    # app config
    shortlist_limit: int = Field(default=8, ge=3, le=12)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
