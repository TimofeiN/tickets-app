from __future__ import annotations

import logging

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from app.application.ports.origin_airport_resolver import OriginAirportResolver
from app.core.errors import DataAccessError
from app.infrastructure.db.models.iata_city_map import IataCityMap
from app.infrastructure.db.session import get_session

logger = logging.getLogger(__name__)


class OriginAirportRepository(OriginAirportResolver):
    def resolve_airports(self, origin_city: str) -> list[str]:
        normalized_city = origin_city.strip().lower()
        if not normalized_city:
            return []

        try:
            with get_session() as session:
                rows = session.exec(
                    select(IataCityMap.iata_code)
                    .where(func.lower(IataCityMap.city_name) == normalized_city)
                    .where(IataCityMap.airport_name.is_not(None))
                    .where(func.length(func.trim(IataCityMap.airport_name)) > 0)
                    .order_by(IataCityMap.iata_code.asc())
                ).all()
        except SQLAlchemyError as exc:
            logger.exception("origin_airport_repository_failed reason=%s", str(exc))
            raise DataAccessError("origin airport resolver query failed") from exc

        return [code.upper() for code in rows if code and len(code) == 3]
