from __future__ import annotations

import logging

from app.shared.enums import RankingMode, SearchDataSource

logger = logging.getLogger(__name__)


def log_search_degradation_metrics(
    *,
    data_source: SearchDataSource,
    ranking_mode: RankingMode,
    fallback_reasons: list[str],
) -> None:
    logger.info(
        "metric_search_request_total count=1 data_source=%s ranking_mode=%s",
        data_source,
        ranking_mode,
    )
    for reason in fallback_reasons:
        logger.info("metric_search_fallback_reason_total count=1 reason=%s", reason)
