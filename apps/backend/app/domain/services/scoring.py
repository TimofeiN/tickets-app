from __future__ import annotations

from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences


def score_candidate(candidate: FlightCandidate, preferences: TripPreferences) -> float:
    requested_themes = set(preferences.themes)
    matched_themes = len(candidate.themes.intersection(requested_themes))
    theme_ratio = matched_themes / max(len(requested_themes), 1)

    group_budget = preferences.budget_usd
    budget_ratio = 1.0
    if group_budget > 0:
        budget_ratio = max(0.0, min(1.0, 1.0 - (candidate.price_usd / group_budget) * 0.5))

    score = 0.7 * theme_ratio + 0.3 * budget_ratio
    return round(max(0.0, min(1.0, score)), 2)


def build_reason(candidate: FlightCandidate, preferences: TripPreferences) -> str:
    requested_themes = set(preferences.themes)
    matched = candidate.themes.intersection(requested_themes)
    if matched:
        matching_themes = ", ".join(sorted(matched))
        return f"Theme match: {matching_themes}; flight price stays within current budget target."
    return "Budget-friendly flight in selected date constraints."


def sort_candidates(
    candidates: list[FlightCandidate],
    preferences: TripPreferences,
) -> list[FlightCandidate]:
    return sorted(
        candidates,
        key=lambda candidate: (score_candidate(candidate, preferences), -candidate.price_usd),
        reverse=True,
    )


def select_top_candidates(
    candidates: list[FlightCandidate],
    preferences: TripPreferences,
) -> list[FlightCandidate]:
    return sort_candidates(candidates, preferences)[:3]


def pick_with_fallback(
    filtered_candidates: list[FlightCandidate],
    all_candidates: list[FlightCandidate],
    preferences: TripPreferences,
) -> list[FlightCandidate]:
    top_filtered = select_top_candidates(filtered_candidates, preferences)
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
