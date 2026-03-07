from __future__ import annotations

from typing import Protocol


class CityResolver(Protocol):
    def resolve_city_names(self, iata_codes: list[str]) -> dict[str, str]: ...
