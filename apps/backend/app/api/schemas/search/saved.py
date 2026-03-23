from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class SavedSearchSummaryResponse(BaseModel):
    id: str
    created_at: datetime
    origin_city: str
    start_date: date
    end_date: date
    budget_usd: int
    themes: list[str]
    summary_destination: str | None = None
    summary_price_usd: int | None = None
    options_count: int = 0


class SavedSearchDetailResponse(SavedSearchSummaryResponse):
    request_payload: dict[str, object]
    response_payload: dict[str, object]
