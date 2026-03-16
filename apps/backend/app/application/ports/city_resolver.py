from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ResolvedCityName:
    iata_code: str
    city_name: str


class CityResolver(Protocol):
    def resolve_city_names(self, iata_codes: list[str]) -> list[ResolvedCityName]: ...
