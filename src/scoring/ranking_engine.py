"""
Ranking Engine - Multi-strategy project ranking and tier classification.

Implements comprehensive ranking, preference-based re-ranking,
S/A/B/C/D tier classification, and category grouping
of analyzed projects.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.models.analysis import ProjectScore, RankedProject, ComparisonTable
from src.models.common import RankTier, score_to_tier
from src.utils.logger import get_logger

logger = get_logger(__name__)


TIER_THRESHOLDS = {
    RankTier.S: 90,
    RankTier.A: 75,
    RankTier.B: 60,
    RankTier.C: 40,
    RankTier.D: 0,
}


class RankingEngine:
    """Multi-strategy ranking engine for scored projects.

    Provides ranked ordering of analyzed projects using configurable
    strategies (comprehensive score, user preferences, scenario-based)
    with tier classification (S/A/B/C/D) and diversity guarantees.

    为评分项目提供多策略排名引擎。
    使用可配置策略（综合分数、用户偏好、场景）提供已分析项目的排序，
    具有分级分类（S/A/B/C/D）和多样性保证。
    """

    def __init__(self) -> None:
        pass

    def rank_by_comprehensive(
        self, scores: List[ProjectScore], repositories: List[Any],
    ) -> List[RankedProject]:
        """Rank by descending comprehensive weighted score."""
        repo_map = {r.full_name: r for r in repositories}
        ranked: List[RankedProject] = []

        sorted_scores = sorted(scores, key=lambda x: x.comprehensive, reverse=True)

        for rank_idx, ps in enumerate(sorted_scores, start=1):
            tier = score_to_tier(ps.comprehensive)
            repo = repo_map.get(ps.project_full_name)
            if not repo:
                continue

            rp = RankedProject(
                project=repo,
                score=ps,
                rank=rank_idx,
                tier=tier,
                highlights=self._extract_highlights(ps),
                concerns=self._extract_concerns(ps),
            )
            ranked.append(rp)

        return ranked

    def rank_by_dimension(
        self, scores: List[ProjectScore], repositories: List[Any],
        dimension: str,
    ) -> List[RankedProject]:
        """Rank by a single dimension's normalized score."""
        repo_map = {r.full_name: r for r in repositories}
        sorted_scores = sorted(
            scores, key=lambda x: x.normalized.get(dimension, 0), reverse=True
        )

        ranked: List[RankedProject] = []
        for idx, ps in enumerate(sorted_scores, start=1):
            tier = score_to_tier(ps.normalized.get(dimension, 0) * 100)
            repo = repo_map.get(ps.project_full_name)
            if repo:
                ranked.append(RankedProject(project=repo, score=ps, rank=idx, tier=tier))

        return ranked

    def rank_with_preferences(
        self,
        scores: List[ProjectScore],
        repositories: List[Any],
        preferences: Dict[str, float],
    ) -> List[RankedProject]:
        """Re-rank with custom dimension weight overrides."""
        adjusted: List[ProjectScore] = []
        for ps in scores:
            new_comp = sum(
                ps.normalized.get(dim, 0) * weight
                for dim, weight in preferences.items()
            ) * 100
            new_ps = ProjectScore(
                project_full_name=ps.project_full_name,
                dimensions=ps.dimensions,
                normalized=ps.normalized.copy(),
                comprehensive=new_comp,
                rank=0,
                confidence=ps.confidence,
            )
            adjusted.append(new_ps)

        return self.rank_by_comprehensive(adjusted, repositories)

    def group_by_category(self, ranked: List[RankedProject]) -> Dict[str, Any]:
        """Group ranked projects into meaningful categories."""
        groups: Dict[str, Any] = {}
        for rp in ranked:
            # Simple category: use language or primary strength / 简单分类：使用语言或主要优势
            lang = rp.project.primary_language or "unknown"
            key = f"{lang}"
            groups.setdefault(key, []).append(rp)
        return groups

    @staticmethod
    def _extract_highlights(score: ProjectScore) -> List[str]:
        """Generate highlight tags from top dimensions."""
        highlights: list[str] = []
        sorted_dims = sorted(
            score.normalized.items(), key=lambda x: x[1], reverse=True
        )
        labels = {
            "code_quality": "Code Quality",
            "community": "Community Active",
            "functionality": "Feature Rich",
            "maturity": "Production Ready",
            "reputation": "Well Recognized",
            "sustainability": "Sustainable",
        }
        for name, val in sorted_dims[:3]:
            if val >= 0.7:
                highlights.append(f"Excellent {labels.get(name, name)} ({val:.0%})")
        if score.comprehensive >= 90:
            highlights.append("Top-tier overall quality")
        elif score.comprehensive >= 75:
            highlights.append("High-quality project")

        return highlights

    @staticmethod
    def _extract_concerns(score: ProjectScore) -> List[str]:
        """Generate concern tags from weak dimensions."""
        concerns: list[str] = []
        labels = {
            "code_quality": "Code Quality",
            "community": "Community Activity",
            "functionality": "Feature Completeness",
            "maturity": "Maturity Level",
            "reputation": "External Reputation",
            "sustainability": "Long-term Viability",
        }
        for name, val in score.normalized.items():
            if val < 0.3:
                concerns.append(f"Low {labels.get(name, name)} ({val:.0%})")
        if score.comprehensive < 40:
            concerns.append("Below recommended threshold")
        return concerns


__all__ = ["RankingEngine"]
