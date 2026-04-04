"""
Project Relevance Filter.

Filters candidate GitHub projects by relevance to the user's query using
AI-powered judgment, then applies star-count ranking and max-project caps.
Ensures only genuinely relevant projects proceed to the analysis phase.

项目相关性过滤器。
通过AI驱动的判断按与用户查询的相关性过滤候选GitHub项目，
然后应用star数排名和最大项目上限。确保只有真正相关的项目进入分析阶段。
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from src.ai.llm_client import LLMClient
from src.ai.prompts import build_relevance_prompt
from src.models.repository import Repository
from src.models.search import FilterResult, SearchQuery
from src.utils.logger import get_logger
from src.utils.config import AnalysisConfig

logger = get_logger(__name__)


class ProjectFilter:
    """AI-enhanced project relevance filter with ranking and capping.

    Processes a list of candidate repositories from GitHub search results,
    uses LLM to assess each one's relevance to the original query, filters
    out irrelevant entries, and enforces maximum project count limits.

    具有排名和封顶功能的AI增强项目相关性过滤器。
处理来自GitHub搜索结果的候选仓库列表，
使用LLM评估每个仓库与原始查询的相关性，
过滤掉不相关条目，并强制执行最大项目数量限制。
    """

    DEFAULT_THRESHOLD: float = 0.6
    DEFAULT_MAX_PROJECTS: int = 20
    MIN_PROJECTS: int = 5

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        threshold: float = DEFAULT_THRESHOLD,
        max_projects: int = DEFAULT_MAX_PROJECTS,
    ) -> None:
        self.llm_client = llm_client
        self.threshold = threshold
        self.max_projects = max_projects

    async def filter(
        self,
        candidates: List[Repository],
        query: str,
        threshold: Optional[float] = None,
        max_projects: Optional[int] = None,
    ) -> FilterResult:
        """Filter candidates by AI relevance assessment.

        通过AI相关性评估过滤候选项目。

        Args:
            candidates: All candidate repositories from search.
                        来自搜索的所有候选仓库。
            query: Original user search query.
                  原始用户搜索查询。
            threshold: Minimum relevance score to keep (0.0-1.0).
                      要保留的最低相关性分数（0.0-1.0）。
            max_projects: Maximum projects to retain after filtering.
                          过滤后保留的最大项目数。

        Returns:
            FilterResult with kept/removed lists, scores, and statistics.
             包含保留/移除列表、分数和统计信息的FilterResult。
        """
        effective_threshold = threshold or self.threshold
        effective_max = max_projects or self.max_projects

        logger.info(
            "module=search", operation="filter_start",
            params={
                "input_count": len(candidates),
                "threshold": effective_threshold,
                "max_projects": effective_max,
            },
        )

        # Deduplicate by full_name / 按full_name去重
        seen: set = set()
        unique_candidates: List[Repository] = []
        for repo in candidates:
            if repo.full_name not in seen:
                seen.add(repo.full_name)
                unique_candidates.append(repo)

        logger.info(
            "module=search", operation="after_dedup",
            params={"unique_count": len(unique_candidates)},
        )

        if not unique_candidates:
            return FilterResult(
                input_count=len(candidates),
                threshold=effective_threshold,
            )

        # Phase 1: AI Relevance Scoring / 阶段1：AI相关性评分
        scores: Dict[str, float] = {}
        reasons: Dict[str, str] = {}

        if self.llm_client:
            scores, reasons = await self._batch_relevance_score(
                unique_candidates, query
            )
        else:
            # No AI: pass all through with neutral score / 无AI：全部通过中性分数
            for repo in unique_candidates:
                scores[repo.full_name] = 1.0

        # Phase 2: Apply Threshold / 阶段2：应用阈值
        kept: List[Repository] = []
        removed: List[Repository] = []

        for repo in unique_candidates:
            score = scores.get(repo.full_name, 0.0)
            if score >= effective_threshold:
                kept.append(repo)
            else:
                removed.append(repo)
                removal_reasons = {
                    f"{repo.full_name}": (
                        reasons.get(repo.full_name, "")
                        or f"Relevance score {score:.2f} below threshold {effective_threshold}"
                    )
                }

        # Phase 3: Enforce Max Projects Cap (by stars) / 阶段3：执行最大项目上限（按stars）
        truncated_count = 0
        if len(kept) > effective_max:
            kept.sort(key=lambda r: r.stars, reverse=True)
            truncated_count = len(kept) - effective_max
            removed.extend(kept[effective_max:])
            kept = kept[:effective_max]

        # Check minimum count / 检查最小数量
        if len(kept) < self.MIN_PROJECTS:
            logger.warning(
                "module=search", operation="below_min_projects",
                params={
                    "kept": len(kept),
                    "min_required": self.MIN_PROJECTS,
                },
            )

        result = FilterResult(
            input_count=len(candidates),
            kept=kept,
            removed=list(set(removed)),  # Deduplicate removed / 去重removed
            removal_reasons={r.full_name: r for r, _ in removal_reasons.items()},
            relevance_scores=scores,
            threshold=effective_threshold,
            applied_limit=(len(kept) == effective_max
                             and len(candidates) > effective_max),
            truncated_count=truncated_count,
        )

        logger.info(
            "module=search", operation="filter_complete",
            params={
                "input": result.input_count,
                "kept": len(result.kept),
                "removed": len(result.removed),
                "pass_rate": f"{result.pass_rate:.1%}",
            },
        )
        return result

    async def _batch_relevance_score(
        self,
        candidates: List[Repository],
        query: str,
    ) -> tuple[Dict[str, float], Dict[str, str]]:
        """Score all candidates' relevance using LLM (with concurrency control).

        使用LLM对所有候选项目的相关性进行评分（带并发控制）。"""

        scores: Dict[str, float] = {}
        reasons: Dict[str, str] = {}

        semaphore = asyncio.Semaphore(4)  # Limit concurrency / 限制并发

        async def score_one(repo: Repository) -> tuple[str, float, str]:
            async with semaphore:
                prompt = build_relevance_prompt(
                    user_query=query,
                    project_name=repo.full_name,
                    project_description=repo.description or "",
                    project_language=repo.primary_language,
                    project_topics=repo.topics,
                    stars=repo.stars,
                    url=repo.html_url or repo.url,
                )

                try:
                    raw = await self.llm_client.generate_structured(prompt)

                    is_relevant = raw.get("is_relevant", False)
                    score = float(raw.get("relevance_score", 0.5))
                    reason = raw.get("reasoning", "")

                    if not is_relevant and score > self.threshold:
                        score *= 0.5  # Downgrade conflicting signals / 降级冲突信号

                    return (repo.full_name, score, reason)

                except Exception as e:
                    logger.debug(
                        "module=search",
                        operation="single_relevance_failed",
                        params={"repo": repo.full_name, "error": str(e)},
                    )
                    return (repo.full_name, 0.5, f"Error during scoring: {str(e)}")

        tasks = [score_one(repo) for repo in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in results:
            if isinstance(item, BaseException):
                continue
            name, score, reason = item  # type: ignore
            scores[name] = score
            if reason:
                reasons[name] = reason

        return scores, reasons


__all__ = ["ProjectFilter"]
