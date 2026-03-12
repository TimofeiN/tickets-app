from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.enums import DatesMode, TripTheme


class StrictDates(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_range(self) -> "StrictDates":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class FlexibleDates(BaseModel):
    year: int = Field(ge=2026, le=2100)
    month: int = Field(ge=1, le=12)
    trip_length_days: int = Field(ge=2, le=21)


class SearchRequest(BaseModel):
    origin_city: str = Field(min_length=2, max_length=120)
    dates_mode: DatesMode
    strict_dates: StrictDates | None = None
    themes: list[TripTheme] = Field(min_length=1, max_length=5)
    budget_usd: int = Field(ge=100, le=50000)
    travelers_count: int = Field(default=2, ge=1, le=10)
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_city": "Belgrade",
                "dates_mode": "strict",
                "strict_dates": {"start_date": "2026-06-10", "end_date": "2026-06-17"},
                "themes": ["beach", "history"],
                "budget_usd": 2000,
                "travelers_count": 2,
            }
        }
    )

    @model_validator(mode="after")
    def validate_dates_payload(self) -> "SearchRequest":
        if self.dates_mode != DatesMode.strict:
            raise ValueError("dates_mode='flexible' is reserved for future implementation")
        if self.strict_dates is None:
            raise ValueError("strict_dates is required when dates_mode='strict'")
        return self
