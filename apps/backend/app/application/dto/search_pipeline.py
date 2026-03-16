from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.flight_candidate import FlightCandidate


@dataclass(frozen=True)
class FactualShortlistedOption:
    candidate: FlightCandidate
    factual_score: float


@dataclass(frozen=True)
class ShortlistStepResult:
    shortlist: list[FactualShortlistedOption]


@dataclass(frozen=True)
class SemanticScoreResult:
    option_id: str
    theme_fit_score: float
    confidence: float
    matched_themes: tuple[str, ...]
    reason_short: str


@dataclass(frozen=True)
class SemanticScoringStepResult:
    scores: list[SemanticScoreResult]


@dataclass(frozen=True)
class FinalRankedOption:
    candidate: FlightCandidate
    final_score: float
    semantic_confidence: float | None
    reason_short: str
