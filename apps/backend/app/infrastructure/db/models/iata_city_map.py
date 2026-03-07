from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class IataCityMap(SQLModel, table=True):
    __tablename__ = "iata_city_map"

    iata_code: str = Field(primary_key=True, max_length=3)
    city_code: str = Field(max_length=3, index=True)
    city_name: str
    airport_name: str | None = None
    country_code: str | None = Field(default=None, max_length=3)
    source: str
    updated_at: datetime | None = None
