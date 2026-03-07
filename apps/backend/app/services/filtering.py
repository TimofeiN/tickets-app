from __future__ import annotations

from app.providers.travelpayouts import FlightCandidate
from app.schemas import DatesMode, SearchRequest


def filter_candidates(
    candidates: list[FlightCandidate],
    payload: SearchRequest,
) -> list[FlightCandidate]:
    filtered_by_budget = _filter_by_budget(candidates, payload)
    return _filter_by_dates(filtered_by_budget, payload)


def score_candidate(candidate: FlightCandidate, payload: SearchRequest) -> float:
    requested_themes = {theme.value for theme in payload.themes}
    matched_themes = len(candidate.themes.intersection(requested_themes))
    theme_ratio = matched_themes / max(len(requested_themes), 1)

    group_budget = payload.budget_usd
    budget_ratio = 1.0
    if group_budget > 0:
        budget_ratio = max(0.0, min(1.0, 1.0 - (candidate.price_usd / group_budget) * 0.5))

    score = 0.7 * theme_ratio + 0.3 * budget_ratio
    return round(max(0.0, min(1.0, score)), 2)


def build_reason(candidate: FlightCandidate, payload: SearchRequest) -> str:
    requested_themes = {theme.value for theme in payload.themes}
    matched = candidate.themes.intersection(requested_themes)
    if matched:
        matching_themes = ", ".join(sorted(matched))
        return f"Theme match: {matching_themes}; flight price stays within current budget target."
    return "Budget-friendly flight in selected date constraints."


def select_top_candidates(
    candidates: list[FlightCandidate],
    payload: SearchRequest,
) -> list[FlightCandidate]:
    scored = sorted(
        candidates,
        key=lambda candidate: (score_candidate(candidate, payload), -candidate.price_usd),
        reverse=True,
    )
    return scored[:3]


def _filter_by_budget(
    candidates: list[FlightCandidate],
    payload: SearchRequest,
) -> list[FlightCandidate]:
    per_traveler_budget = payload.budget_usd / payload.travelers_count
    return [candidate for candidate in candidates if candidate.price_usd <= per_traveler_budget]


def _filter_by_dates(
    candidates: list[FlightCandidate],
    payload: SearchRequest,
) -> list[FlightCandidate]:
    if payload.dates_mode == DatesMode.strict:
        assert payload.strict_dates is not None
        start = payload.strict_dates.start_date
        end = payload.strict_dates.end_date
        return [
            candidate
            for candidate in candidates
            if candidate.departure_date >= start and candidate.return_date <= end
        ]

    assert payload.flexible_dates is not None
    year = payload.flexible_dates.year
    month = payload.flexible_dates.month
    trip_length_days = payload.flexible_dates.trip_length_days

    return [
        candidate
        for candidate in candidates
        if _matches_flexible_window(candidate, year, month, trip_length_days)
    ]


def _matches_flexible_window(
    candidate: FlightCandidate,
    year: int,
    month: int,
    trip_length_days: int,
) -> bool:
    if candidate.departure_date.year != year or candidate.departure_date.month != month:
        return False

    actual_length_days = (candidate.return_date - candidate.departure_date).days
    return actual_length_days == trip_length_days


def pick_with_fallback(
    filtered_candidates: list[FlightCandidate],
    all_candidates: list[FlightCandidate],
    payload: SearchRequest,
) -> list[FlightCandidate]:
    top_filtered = select_top_candidates(filtered_candidates, payload)
    if len(top_filtered) == 3:
        return top_filtered

    selected_ids = {candidate.option_id for candidate in top_filtered}
    sorted_all = sorted(all_candidates, key=lambda candidate: candidate.price_usd)

    for candidate in sorted_all:
        if candidate.option_id in selected_ids:
            continue
        top_filtered.append(candidate)
        selected_ids.add(candidate.option_id)
        if len(top_filtered) == 3:
            break

    return top_filtered
