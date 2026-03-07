from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DatesMode(str, Enum):
    strict = "strict"
    flexible = "flexible"


class TripTheme(str, Enum):
    beach = "beach"
    history = "history"
    active_summer = "active_summer"
    active_winter = "active_winter"
    gastronomy = "gastronomy"
    family = "family"
    nightlife = "nightlife"


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
    flexible_dates: FlexibleDates | None = None
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
        if self.dates_mode == DatesMode.strict:
            if self.strict_dates is None:
                raise ValueError("strict_dates is required when dates_mode='strict'")
            if self.flexible_dates is not None:
                raise ValueError("flexible_dates must be empty when dates_mode='strict'")
        if self.dates_mode == DatesMode.flexible:
            if self.flexible_dates is None:
                raise ValueError("flexible_dates is required when dates_mode='flexible'")
            if self.strict_dates is not None:
                raise ValueError("strict_dates must be empty when dates_mode='flexible'")
        return self


class FlightOption(BaseModel):
    option_id: str
    destination_city: str
    origin_airport: str
    destination_airport: str
    price_usd: int
    score: float = Field(ge=0, le=1)
    reason: str


class SearchResponse(BaseModel):
    options: list[FlightOption] = Field(min_length=3, max_length=3)
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "options": [
                    {
                        "option_id": "opt_bcn_001",
                        "destination_city": "Barcelona",
                        "origin_airport": "BEG",
                        "destination_airport": "BCN",
                        "price_usd": 640,
                        "score": 0.92,
                        "reason": "Beach + culture fit and good weather in selected window.",
                    },
                    {
                        "option_id": "opt_ath_002",
                        "destination_city": "Athens",
                        "origin_airport": "BEG",
                        "destination_airport": "ATH",
                        "price_usd": 590,
                        "score": 0.88,
                        "reason": "History + gastronomy fit with balanced budget usage.",
                    },
                    {
                        "option_id": "opt_lis_003",
                        "destination_city": "Lisbon",
                        "origin_airport": "BEG",
                        "destination_airport": "LIS",
                        "price_usd": 710,
                        "score": 0.84,
                        "reason": "Strong nightlife and city activities within total budget.",
                    },
                ]
            }
        }
    )
