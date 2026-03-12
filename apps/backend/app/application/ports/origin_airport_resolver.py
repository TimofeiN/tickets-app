from __future__ import annotations

from typing import Protocol


class OriginAirportResolver(Protocol):
    def resolve_airports(self, origin_city: str) -> list[str]: ...
