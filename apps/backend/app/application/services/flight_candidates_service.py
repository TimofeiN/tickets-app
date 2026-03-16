from __future__ import annotations

import logging
from datetime import date

from app.application.ports.flight_search_provider import FlightOffer
from app.application.ports.origin_airport_resolver import OriginAirportResolver
from app.core.errors import DataAccessError
from app.domain.models.flight_candidate import FlightCandidate

logger = logging.getLogger(__name__)


class FlightCandidatesService:
    @staticmethod
    def resolve_origin_airports(
        *,
        origin_city: str,
        origin_airport_resolver: OriginAirportResolver,
    ) -> list[str]:
        try:
            resolved = origin_airport_resolver.resolve_airports(origin_city)
        except DataAccessError as exc:
            logger.warning("origin_airport_resolver_failed reason=%s", str(exc))
            return []

        normalized = [code.strip().upper() for code in resolved if code and code.strip()]
        seen: set[str] = set()
        unique: list[str] = []
        for code in normalized:
            if code in seen:
                continue
            seen.add(code)
            unique.append(code)
        return unique

    @classmethod
    def build_candidates_from_offers(
        cls,
        *,
        offers: list[FlightOffer],
    ) -> list[FlightCandidate]:
        candidates: list[FlightCandidate] = []
        for idx, offer in enumerate(offers, start=1):
            candidates.append(
                cls._build_candidate(
                    origin_airport=offer.origin_airport,
                    destination_airport=offer.destination_airport,
                    option_index=idx,
                    destination_city=offer.destination_city,
                    price_usd=offer.price_usd,
                    departure_date=offer.departure_date,
                    return_date=offer.return_date,
                    stops_count=offer.stops_count,
                    travel_time_minutes=offer.travel_time_minutes,
                )
            )
        return candidates

    @staticmethod
    def deduplicate_candidates(candidates: list[FlightCandidate]) -> list[FlightCandidate]:
        seen: set[tuple[str, date, date, int]] = set()
        unique: list[FlightCandidate] = []
        for candidate in candidates:
            key = (
                candidate.destination_airport.upper(),
                candidate.departure_date,
                candidate.return_date,
                candidate.price_usd,
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    @classmethod
    def _build_candidate(
        cls,
        *,
        origin_airport: str,
        destination_airport: str,
        option_index: int,
        destination_city: str,
        price_usd: int,
        departure_date: date,
        return_date: date,
        stops_count: int | None,
        travel_time_minutes: int | None,
    ) -> FlightCandidate:
        return FlightCandidate(
            option_id=f"tp_{origin_airport.lower()}_{destination_airport.lower()}_{option_index:03d}",
            destination_city=destination_city,
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            price_usd=price_usd,
            departure_date=departure_date,
            return_date=return_date,
            themes=frozenset(),
            stops_count=stops_count,
            travel_time_minutes=travel_time_minutes,
        )
