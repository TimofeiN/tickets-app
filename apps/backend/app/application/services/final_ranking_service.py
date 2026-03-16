from __future__ import annotations

from app.application.dto.search_pipeline import (
    FactualShortlistedOption,
    FinalRankedOption,
    SemanticScoreResult,
    SemanticScoringStepResult,
)


class FinalRankingService:
    SEMANTIC_WEIGHT = 0.6
    FACTUAL_WEIGHT = 0.4

    @classmethod
    def rank(
        cls,
        shortlist: list[FactualShortlistedOption],
        semantic_scoring_result: SemanticScoringStepResult,
    ) -> list[FinalRankedOption]:
        semantic_scores: dict[str, SemanticScoreResult] = {
            item.option_id: item for item in semantic_scoring_result.scores
        }
        ranked: list[FinalRankedOption] = []
        for item in shortlist:
            semantic_score = semantic_scores.get(item.candidate.option_id)
            if semantic_score is None:
                final_score = item.factual_score
                reason_short = ""
                confidence = None
            else:
                final_score = (
                    cls.SEMANTIC_WEIGHT * semantic_score.theme_fit_score
                    + cls.FACTUAL_WEIGHT * item.factual_score
                )
                reason_short = semantic_score.reason_short
                confidence = semantic_score.confidence

            ranked.append(
                FinalRankedOption(
                    candidate=item.candidate,
                    final_score=round(final_score, 2),
                    semantic_confidence=confidence,
                    reason_short=reason_short,
                )
            )

        return sorted(
            ranked,
            key=lambda item: (
                item.final_score,
                item.semantic_confidence if item.semantic_confidence is not None else -1.0,
                -item.candidate.price_usd,
            ),
            reverse=True,
        )
