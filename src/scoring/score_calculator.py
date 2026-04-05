"""
Multi-Dimensional Score Calculator.

Implements the 6-dimension weighted scoring algorithm:
code_quality (25%), community (20%), functionality (18%),
maturity (15%), reputation (12%), sustainability (10%).
Uses min-max normalization for fair cross-project comparison.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.models.analysis import AnalysisResult, ProjectScore
from src.models.common import DEFAULT_SCORING_WEIGHTS
from src.utils.config import ScoringConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ScoreCalculator:
    """6-dimension weighted scoring engine with min-max normalization.

    6维加权评分引擎,带min-max标准化.
    """

    DIMENSION_KEYS = [
        "code_quality", "community", "functionality",
        "maturity", "reputation", "sustainability",
    ]

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        normalization_method: str = "minmax",
    ) -> None:
        self.weights: Dict[str, float] = (
            dict(DEFAULT_SCORING_WEIGHTS) if weights is None else dict(weights)
        )
        self.normalization_method = normalization_method
        self._validate_weights()

    def _validate_weights(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.05:
            logger.warning(
                "module=scoring", operation="weight_validation_warning",
                params={
                    "total": f"{total:.4f}",
                    "weights": self.weights,
                },
            )

    def calculate_project_score(self, result: AnalysisResult) -> ProjectScore:
        """Calculate normalized scores for a single analyzed project."""
        dimensions: Dict[str, float] = {
            "code_quality": result.code_metrics.overall_score,
            "community": result.community_metrics.overall_score,
            "functionality": result.functionality_score,
            "maturity": result.maturity_metrics.overall_score,
            "reputation": result.reputation_score,
            "sustainability": result.sustainability_score,
        }

        return ProjectScore(
            project_full_name=result.project.full_name,
            dimensions=dimensions,
            normalized={},  # Will be set by normalize_batch / 将由normalize_batch设置
            comprehensive=0.0,
            rank=0,
            confidence=self._calculate_confidence(result),
        )

    def calculate_batch_scores(
        self, results: List[AnalysisResult]
    ) -> List[ProjectScore]:
        """Calculate and normalize scores across all projects."""
        if not results:
            return []

        # Step 1: Raw per-dimension scores / 步骤1:每维度原始分数
        raw_scores: List[ProjectScore] = [
            self.calculate_project_score(r) for r in results
        ]

        # Step 2: Min-max normalization per dimension / 步骤2:每维度min-max标准化
        normalized = self._normalize_dimensions(raw_scores)

        # Step 3: Weighted comprehensive score / 步骤3:加权综合分数
        for i, ps in enumerate(raw_scores):
            ps.normalized = normalized[i]
            ps.comprehensive = round(sum(
                self.weights.get(dim, 0) * ps.normalized.get(dim, 0)
                for dim in self.DIMENSION_KEYS
                if dim in self.weights and dim in ps.normalized
            ) * 100, 1)

        # Step 4: Rank by comprehensive score / 步骤4:按综合分数排名
        sorted_scores = sorted(raw_scores, key=lambda x: x.comprehensive, reverse=True)
        for rank_idx, ps in enumerate(sorted_scores, start=1):
            ps.rank = rank_idx

        logger.info(
            "module=scoring", operation="batch_scoring_complete",
            params={"count": len(sorted_scores)},
        )
        return sorted_scores

    def _normalize_dimensions(
        self, scores: List[ProjectScore]
    ) -> List[Dict[str, float]]:
        """Apply min-max normalization to each dimension independently."""
        if len(scores) <= 1:
            return [s.dimensions.copy() if s.dimensions else {}
                     for s in scores]

        normalized_list: List[Dict[str, float]] = []
        for dim in self.DIMENSION_KEYS:
            values = [s.dimensions.get(dim, 0.0) for s in scores]
            vmin = min(values)
            vmax = max(values)
            vrange = vmax - vmin

            if vrange == 0:
                norm_values = [1.0] * len(values)  # All equal → all perfect / 全部相等→全部完美
            else:
                norm_values = [(v - vmin) / vrange for v in values]

            for idx, nv in enumerate(norm_values):
                if idx >= len(normalized_list):
                    normalized_list.append({})
                normalized_list[idx][dim] = nv

        return normalized_list

    @staticmethod
    def _calculate_confidence(result: AnalysisResult) -> float:
        """Estimate scoring confidence based on data availability."""
        factors: list[float] = []
        total_possible = 6

        if result.code_metrics.overall_score > 0:
            factors.append(1.0)
        else:
            factors.append(0.5)

        if result.community_metrics.overall_score > 0:
            factors.append(1.0)
        else:
            factors.append(0.7)  # Community often estimable / 社区通常可估算

        if result.functionality_score > 0:
            factors.append(1.0)

        if result.maturity_metrics.overall_score > 0:
            factors.append(1.0)

        if result.reputation_score > 0:
            factors.append(0.8)  # Reputation is estimated / 声誉是估算的

        if result.sustainability_score > 0:
            factors.append(0.8)

        return sum(factors) / total_possible if factors else 0.5


__all__ = ["ScoreCalculator"]
