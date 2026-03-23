from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from app.application.ports.origin_airport_resolver import OriginAirportResolver
from app.core.errors import DataAccessError
from app.infrastructure.db.models.iata_city_map import IataCityMap

logger = logging.getLogger(__name__)


class OriginAirportRepository(OriginAirportResolver):
    def __init__(self, *, session: Session) -> None:
        self.session = session

    def resolve_airports(self, origin_city: str) -> list[str]:
        normalized_city = origin_city.strip().lower()
        if not normalized_city:
            return []

        try:
            rows = self.session.exec(
                select(
                    IataCityMap.iata_code,
                    IataCityMap.city_code,
                    IataCityMap.country_code,
                )
                .where(func.lower(col(IataCityMap.city_name)) == normalized_city)
                .where(col(IataCityMap.airport_name).is_not(None))
                .where(func.length(func.trim(col(IataCityMap.airport_name))) > 0)
                .where(col(IataCityMap.is_flightable).is_(True))
                .order_by(
                    col(IataCityMap.country_code).asc(),
                    col(IataCityMap.city_code).asc(),
                    col(IataCityMap.iata_code).asc(),
                )
            ).all()
        except SQLAlchemyError as exc:
            logger.exception("origin_airport_repository_failed reason=%s", str(exc))
            raise DataAccessError("origin airport resolver query failed") from exc

        grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
        for iata_code, city_code, country_code in rows:
            normalized_iata = (iata_code or "").strip().upper()
            normalized_city_code = (city_code or "").strip().upper()
            normalized_country_code = (country_code or "").strip().upper()
            if len(normalized_iata) != 3 or len(normalized_city_code) != 3:
                continue
            grouped[(normalized_city_code, normalized_country_code)].append(normalized_iata)

        if not grouped:
            return []

        best_group_key, best_group_codes = max(
            grouped.items(),
            key=lambda item: (
                sum(code != item[0][0] for code in item[1]),
                len(item[1]),
            ),
        )

        city_code = best_group_key[0]
        selected_codes: list[str] = []
        if city_code in best_group_codes:
            selected_codes.append(city_code)
        selected_codes.extend(code for code in best_group_codes if code != city_code)

        deduplicated: list[str] = []
        seen: set[str] = set()
        for code in selected_codes:
            if code in seen:
                continue
            seen.add(code)
            deduplicated.append(code)
        return deduplicated
