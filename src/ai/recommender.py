"""
Recommender - AI-Powered Project Recommendation Engine.

Generates personalized project recommendations based on scored analysis results.
Supports different ranking strategies (comprehensive, preference-based, scenario-based)
and ensures recommendation diversity to avoid homogeneous suggestions.

推荐引擎 - AI驱动的项目推荐生成器。
基于评分分析结果生成个性化项目推荐。支持不同的排名策略
（综合、偏好、场景）并确保推荐多样性以避免同质化建议。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.ai.llm_client import LLMClient
from src.models.analysis import ProjectScore, RankedProject
from src.models.common import RankTier
from src.models.repository import Repository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Recommender:
    """AI-enhanced project recommender with multiple ranking strategies.

    Combines algorithmic scoring with AI-generated insights to produce
    ranked recommendations that consider user preferences and use-case context.

    具有多种排名策略的AI增强型项目推荐器。
将算法评分与AI生成的洞察相结合，生成考虑用户偏好和
用例上下文的排名推荐。

    Attributes:
        llm_client: LLM client for generating recommendation insights.
                   用于生成推荐洞察的LLM客户端。
    """

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        """Initialize recommender with optional LLM client.

        使用可选LLM客户端初始化推荐器。

        Args:
            llm_client: Client for AI-powered explanation generation.
                      用于AI驱动解释生成的客户端。
        """
        self.llm_client = llm_client

    async def recommend(
        self,
        scored_projects: List[ProjectScore],
        repositories: List[Repository],
        query: str,
        strategy: str = "comprehensive",
        max_recommendations: int = 10,
    ) -> List[RankedProject]:
        """Generate ranked recommendations from scored projects.

        从评分项目生成排名推荐。

        Args:
            scored_projects: List of ProjectScore objects sorted by comprehensive score.
                           按综合分数排序的ProjectScore对象列表。
            repositories: Corresponding repository metadata for each score.
                        每个分数对应的仓库元数据。
            query: Original user search query.
                  原始用户搜索查询。
            strategy: Ranking strategy ('comprehensive', 'preference', 'scenario').
                     排名策略（'comprehensive'、'preference'、'scenario'）。
            max_recommendations: Maximum number of projects to recommend.
                                推荐的最大项目数。

        Returns:
            List of RankedProject objects with tier classification and highlights.
             带分级分类和高亮的RankedProject对象列表。
        """
        if not scored_projects:
            return []

        # Build repo lookup / 构建仓库查找表
        repo_map: Dict[str, Repository] = {r.full_name: r for r in repositories}

        # Apply strategy-specific adjustments / 应用特定于策略的调整
        adjusted_scores = self._apply_strategy(
            scored_projects, strategy, query
        )

        # Create ranked projects / 创建排名项目
        ranked: List[RankedProject] = []
        for rank_idx, (score, original_score) in enumerate(
            zip(adjusted_scores[:max_recommendations],
                scored_projects[:max_recommendations]), start=1
        ):
            repo = repo_map.get(score.project_full_name)
            if not repo:
                continue

            tier = _score_to_tier(score.comprehensive)
            highlights = self._generate_highlights(score)
            concerns = self._generate_concerns(score)

            ranked.append(RankedProject(
                project=repo,
                score=score,
                rank=rank_idx,
                tier=tier,
                highlights=highlights,
                concerns=concerns,
                use_cases=self._infer_use_cases(score),
            ))

        # Enrich with AI insights if client available / 如有客户端则使用AI洞察丰富
        if self.llm_client and ranked:
            await self._enrich_with_ai_insights(
                ranked, query
            )

        logger.info(
            "module=ai", operation="recommend_complete",
            params={
                "strategy": strategy,
                "total_recommended": len(ranked),
                "query": query,
            },
        )
        return ranked

    def recommend_by_preference(
        self,
        scored_projects: List[ProjectScore],
        repositories: List[Repository],
        query: str,
        preferences: Dict[str, float],
    ) -> List[RankedProject]:
        """Generate recommendations with custom dimension weight overrides.

        使用自定义维度权重覆盖生成推荐。

        Args:
            scored_projects: Pre-scored project list.
                           预评分项目列表。
            repositories: Repository metadata list.
                         仓库元数据列表。
            query: User query string.
                  用户查询字符串。
            preferences: Dimension name -> custom weight mapping.
                         维度名称->自定义权重映射。

        Returns:
            Preference-adjusted ranked recommendations.
             偏好调整后的排名推荐。
        """
        # Re-calculate scores with custom weights / 使用自定义权重重新计算分数
        adjusted = []
        for ps in scored_projects:
            new_comprehensive = sum(
                ps.normalized.get(dim, 0.0) * weight
                for dim, weight in preferences.items()
            )
            new_ps = ProjectScore(
                project_full_name=ps.project_full_name,
                dimensions=ps.dimensions.copy(),
                normalized=ps.normalized.copy(),
                comprehensive=new_comprehensive * 100.0,  # Scale back / 缩放回
                rank=0,
                confidence=ps.confidence,
            )
            adjusted.append(new_ps)

        adjusted.sort(key=lambda x: x.comprehensive, reverse=True)

        return self.recommend(
            adjusted, repositories, query,
            strategy="preference", max_recommendations=len(adjusted),
        )

    def group_by_tier(self, ranked: List[RankedProject]) -> Dict[str, List[RankedProject]]:
        """Group ranked projects by their S/A/B/C/D tier.

        将排名项目按S/A/B/C/D等级分组。

        Args:
            ranked: List of RankedProject objects.
                 RankedProject对象列表。

        Returns:
            Dictionary mapping tier value -> list of projects in that tier.
             映射等级值->该等级中项目列表的字典。
        """
        groups: Dict[str, List[RankedProject]] = {}
        for rp in ranked:
            key = rp.tier.value
            groups.setdefault(key, []).append(rp)
        return groups

    # ------------------------------------------------------------------
    # Internal Methods / 内部方法
    # ------------------------------------------------------------------

    def _apply_strategy(
        self,
        scores: List[ProjectScore],
        strategy: str,
        query: str,
    ) -> List[ProjectScore]:
        """Apply ranking strategy adjustments to scores.

        对分数应用排名策略调整。

        Args:
            scores: Input scores sorted by comprehensive descending.
                  按综合降序排序的输入分数。
            strategy: Strategy name.
                     策略名称。
            query: User query (used for scenario matching).
                  用户查询（用于场景匹配）。

        Returns:
            Adjusted scores list.
             调整后的分数列表。
        """
        if strategy == "comprehensive":
            return scores  # No adjustment / 无调整
        elif strategy == "production_ready":
            # Boost maturity dimension / 提升成熟度维度
            result = []
            for s in scores:
                ns = ProjectScore(
                    project_full_name=s.project_full_name,
                    dimensions=s.dimensions,
                    normalized=s.normalized,
                    comprehensive=(
                        s.comprehensive
                        + s.get_dimension("maturity") * 15  # Maturity bonus
                    ),
                    confidence=s.confidence,
                )
                result.append(ns)
            result.sort(key=lambda x: x.comprehensive, reverse=True)
            return result
        else:
            return scores

    def _generate_highlights(self, score: ProjectScore) -> List[str]:
        """Generate positive highlight tags based on top-performing dimensions.

        根据表现最佳的维度生成正面高亮标签。

        Args:
            score: Project score data.
                 项目评分数据。

        Returns:
            List of highlight description strings.
             高亮描述字符串列表。
        """
        highlights: List[str] = []
        dim_names = {
            "code_quality": "Code Quality",
            "community": "Community Active",
            "functionality": "Feature Rich",
            "maturity": "Production Ready",
            "reputation": "Well Recognized",
            "sustainability": "Sustainable",
        }

        # Top 2 dimensions / 前2个维度
        sorted_dims = sorted(
            score.normalized.items(), key=lambda x: x[1], reverse=True
        )
        for dim_name, value in sorted_dims[:2]:
            if value >= 0.7:
                label = dim_names.get(dim_name, dim_name.replace("_", " ").title())
                highlights.append(f"Excellent {label} ({value:.0%})")

        if score.comprehensive >= 90:
            highlights.append("Top-tier overall quality")
        elif score.comprehensive >= 75:
            highlights.append("High-quality project")

        return highlights

    def _generate_concerns(self, score: ProjectScore) -> List[str]:
        """Generate concern/warning tags for weak dimensions.

        为弱维度生成关注/警告标签。

        Args:
            score: Project score data.
                 项目评分数据。

        Returns:
            List of concern description strings.
             关注描述字符串列表。
        """
        concerns: List[str] = []
        dim_labels = {
            "code_quality": "Code Quality",
            "community": "Community Activity",
            "functionality": "Feature Completeness",
            "maturity": "Maturity",
            "reputation": "Reputation",
            "sustainability": "Sustainability",
        }

        for dim_name, value in score.normalized.items():
            if value < 0.3:
                label = dim_labels.get(dim_name, dim_name.title())
                concerns.append(f"Low {label} ({value:.0%})")

        if score.comprehensive < 40:
            concerns.append("Below minimum recommended threshold")

        return concerns

    def _infer_use_cases(self, score: ProjectScore) -> List[str]:
        """Infer suitable use cases from score profile.

        从评分概况推断适用场景。

        Args:
            score: Project score data.
                 项目评分数据。

        Returns:
            List of use case strings.
             用例字符串列表。
        """
        use_cases: List[str] = []

        if score.get_dimension("maturity") > 0.7:
            use_cases.append("Production deployment")

        if score.get_dimension("community") > 0.6:
            use_cases.append("Learning and contribution")

        if score.get_dimension("functionality") > 0.65:
            use_cases.append("Full-featured usage")

        if score.get_dimension("code_quality") > 0.7:
            use_cases.append("Reference implementation")

        return use_cases or ["General purpose"]

    async def _enrich_with_ai_insights(
        self,
        ranked: List[RankedProject],
        query: str,
    ) -> None:
        """Use LLM to generate detailed recommendation reasons for top projects.

        使用LLM为顶级项目生成详细的推荐原因。

        Args:
            ranked: Ranked project list (modified in-place).
                 排名项目列表（就地修改）。
            query: Original user query.
                  原始用户查询。
        """
        if not self.llm_client:
            return

        try:
            from src.ai.prompts import build_recommendation_prompt

            # Prepare data summary / 准备数据摘要
            scoring_rows = [
                f"- {rp.project.full_name}: {rp.score.comprehensive:.1f} "
                f"(Tier {rp.tier.value})"
                for rp in ranked[:10]
            ]

            prompt = build_recommendation_prompt(
                user_query=query,
                projects_data=json.dumps(
                    [
                        {
                            "name": rp.project.full_name,
                            "score": rp.score.comprehensive,
                            "tier": rp.tier.value,
                            "stars": rp.project.stars,
                        }
                        for rp in ranked
                    ],
                    ensure_ascii=False,
                ),
                scoring_table="\n".join(scoring_rows),
            )

            result = await self.llm_client.generate_structured(prompt)

            if isinstance(result, list):
                for idx, rec in enumerate(result):
                    if idx < len(ranked):
                        rec.recommendation_reason = rec.get(
                            "verdict", ""
                        ) if isinstance(rec, dict) else ""

        except Exception as e:
            logger.warning(
                "module=ai", operation="ai_enrichment_failed",
                params={"error": str(e)},
            )


def _score_to_tier(score: float) -> RankTier:
    """Map numeric score to tier classification."""
    if score >= 90:
        return RankTier.S
    elif score >= 75:
        return RankTier.A
    elif score >= 60:
        return RankTier.B
    elif score >= 40:
        return RankTier.C
    else:
        return RankTier.D


__all__ = ["Recommender"]
