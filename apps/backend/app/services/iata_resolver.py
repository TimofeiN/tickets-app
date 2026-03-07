from __future__ import annotations

import logging

from sqlalchemy import func
from sqlmodel import select

from app.db import get_session
from app.models.iata_city_map import IataCityMap

logger = logging.getLogger(__name__)


class IataCityResolver:
    def resolve_city_names(self, iata_codes: list[str]) -> dict[str, str]:
        normalized_codes = sorted({code.strip().upper() for code in iata_codes if code.strip()})
        if not normalized_codes:
            return {}

        try:
            with get_session() as session:
                by_iata_rows = session.exec(
                    select(IataCityMap).where(IataCityMap.iata_code.in_(normalized_codes))
                ).all()

                unresolved = [
                    code
                    for code in normalized_codes
                    if code not in {row.iata_code.upper() for row in by_iata_rows}
                ]
                by_city_code_rows: list[tuple[str, str]] = []
                if unresolved:
                    by_city_code_rows = session.exec(
                        select(
                            IataCityMap.city_code,
                            func.min(IataCityMap.city_name),
                        )
                        .where(IataCityMap.city_code.in_(unresolved))
                        .group_by(IataCityMap.city_code)
                    ).all()
        except Exception as exc:
            logger.warning("iata_city_resolver_failed reason=%s", str(exc))
            return {}

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
        return resolved
