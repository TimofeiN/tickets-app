from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, select

from app.application.ports.city_resolver import CityResolver, ResolvedCityName
from app.core.errors import DataAccessError
from app.infrastructure.db.models.iata_city_map import IataCityMap
from app.infrastructure.db.session import get_session

logger = logging.getLogger(__name__)


class IataCityRepository(CityResolver):
    def resolve_city_names(self, iata_codes: list[str]) -> list[ResolvedCityName]:
        normalized_codes = sorted({code.strip().upper() for code in iata_codes if code.strip()})
        if not normalized_codes:
            return []

        try:
            with get_session() as session:
                by_iata_rows = session.exec(
                    select(IataCityMap).where(col(IataCityMap.iata_code).in_(normalized_codes))
                ).all()

                unresolved = [
                    code
                    for code in normalized_codes
                    if code not in {row.iata_code.upper() for row in by_iata_rows}
                ]
                by_city_code_rows: Sequence[tuple[str, str]] = ()
                if unresolved:
                    by_city_code_rows = session.exec(
                        select(
                            IataCityMap.city_code,
                            func.min(IataCityMap.city_name),
                        )
                        .where(col(IataCityMap.city_code).in_(unresolved))
                        .group_by(IataCityMap.city_code)
                    ).all()
        except SQLAlchemyError as exc:
            logger.exception("iata_city_resolver_failed reason=%s", str(exc))
            raise DataAccessError("iata city resolver query failed") from exc

        resolved = {
            row.iata_code.upper(): row.city_name
            for row in by_iata_rows
            if row.iata_code and row.city_name
        }
        resolved.update(
            {
                city_code.upper(): city_name
                for city_code, city_name in by_city_code_rows
                if city_code and city_name
            }
        )
        logger.info(
            "iata_city_resolver_completed requested=%s resolved=%s",
            len(normalized_codes),
            len(resolved),
        )
        return [
            ResolvedCityName(iata_code=code, city_name=resolved[code])
            for code in normalized_codes
            if code in resolved
        ]
