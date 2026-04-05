"""
Analysis Pipeline - Parallel Orchestration of All Analyzers.

Coordinates the three analysis modules (code, community, maturity) to run
concurrently or sequentially, aggregates results into AnalysisResult objects,
and manages the full analysis lifecycle for each project.

分析流水线 - 所有分析器的并行编排.
协调三个分析模块(代码,社区,成熟度)并发或顺序运行,
将结果聚合到AnalysisResult对象中,并管理每个项目的完整分析生命周期.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from src.analysis.code_analyzer import CodeAnalyzer
from src.analysis.community_analyzer import CommunityAnalyzer
from src.analysis.maturity_analyzer import MaturityAnalyzer
from src.models.analysis import AnalysisResult
from src.models.metrics import (
    CodeQualityMetrics,
    CommunityMetrics,
    MaturityMetrics,
)
from src.models.repository import Repository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisPipeline:
    """Orchestrates multi-dimensional project analysis.

    Manages the complete analysis workflow for a batch of projects,
    coordinating code quality, community health, and maturity assessments
    with configurable parallelism and error handling.

    编排多维项目分析.
管理一批项目的完整分析工作流,
协调代码质量,社区健康度和成熟度评估,
具有可配置的并行性和错误处理.

    Attributes:
        code_analyzer: Code quality assessment engine.
                      代码质量评估引擎.
        community_analyzer: Community metrics engine.
                           社区指标引擎.
        maturity_analyzer: Maturity assessment engine.
                         成熟度评估引擎.
        parallel_analysis: Whether to run analyzers concurrently.
                          是否并发运行分析器.
        max_concurrent: Max simultaneous analyses (if parallel).
                       最大同时分析数(如果并行).
    """

    def __init__(
        self,
        code_analyzer: Optional[CodeAnalyzer] = None,
        community_analyzer: Optional[CommunityAnalyzer] = None,
        maturity_analyzer: Optional[MaturityAnalyzer] = None,
        github_client: Any = None,
        parallel_analysis: bool = True,
        max_concurrent: int = 4,
    ) -> None:
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.community_analyzer = community_analyzer or CommunityAnalyzer(github_client)
        self.maturity_analyzer = maturity_analyzer or MaturityAnalyzer(github_client)
        self.parallel_analysis = parallel_analysis
        self.max_concurrent = max_concurrent

    async def analyze_project(self, repository: Repository) -> AnalysisResult:
        """Run all analysis dimensions on a single project.

        对单个项目运行所有分析维度."""
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []

        logger.info(
            "module=analysis", operation="pipeline_analyze_start",
            params={"repo": repository.full_name},
        )

        try:
            if self.parallel_analysis:
                code_metrics, comm_metrics, mat_metrics = await asyncio.gather(
                    self._safe_code_analysis(repository),
                    self._safe_community_analysis(repository),
                    self._safe_maturity_analysis(repository),
                    return_exceptions=True,
                )

                # Handle gather exceptions / 处理gather异常
                if isinstance(code_metrics, BaseException):
                    errors.append(f"Code analysis failed: {str(code_metrics)}")
                    code_metrics = CodeQualityMetrics(overall_score=0.0)
                elif isinstance(code_metrics, Exception):
                    errors.append(f"Code analysis error: {str(code_metrics)}")
                    code_metrics = CodeQualityMetrics(overall_score=0.0)

                if isinstance(comm_metrics, BaseException):
                    warnings.append(f"Community analysis skipped: {str(comm_metrics)}")
                    comm_metrics = CommunityMetrics(overall_score=0.0)
                elif isinstance(comm_metrics, Exception):
                    comm_metrics = CommunityMetrics(overall_score=0.0)

                if isinstance(mat_metrics, BaseException):
                    warnings.append(f"Maturity analysis skipped: {str(mat_metrics)}")
                    mat_metrics = MaturityMetrics(overall_score=0.0)
                elif isinstance(mat_metrics, Exception):
                    mat_metrics = MaturityMetrics(overall_score=0.0)

            else:
                # Sequential execution / 顺序执行
                code_metrics = await self._safe_code_analysis(repository)
                comm_metrics = await self._safe_community_analysis(repository)
                mat_metrics = await self._safe_maturity_analysis(repository)

            duration_ms = int((time.time() - start_time) * 1000)

            result = AnalysisResult(
                project=repository,
                code_metrics=code_metrics,
                community_metrics=comm_metrics,
                maturity_metrics=mat_metrics,
                functionality_score=self._estimate_functionality(repository),
                reputation_score=self._estimate_reputation(repository),
                sustainability_score=self._estimate_sustainability(repository),
                errors=errors,
                warnings=warnings,
                analysis_duration_ms=duration_ms,
            )

            logger.info(
                "module=analysis", operation="pipeline_complete",
                params={
                    "repo": repository.full_name,
                    "duration_ms": duration_ms,
                    "errors_count": len(errors),
                },
            )
            return result

        except Exception as e:
            return AnalysisResult(
                project=repository,
                errors=[str(e)],
                analysis_duration_ms=int((time.time() - start_time) * 1000),
            )

    async def analyze_batch(
        self,
        repositories: List[Repository],
    ) -> List[AnalysisResult]:
        """Analyze multiple projects with concurrency control.

        使用并发控制分析多个项目."""
        results: List[AnalysisResult] = []

        if not repositories:
            return results

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _bounded_analysis(repo: Repository) -> AnalysisResult:
            async with semaphore:
                return await self.analyze_project(repo)

        tasks = [_bounded_analysis(r) for r in repositories]
        results = await asyncio.gather(*tasks)

        return results

    # ------------------------------------------------------------------
    # Safe wrappers with error isolation / 带错误隔离的安全包装器
    # ------------------------------------------------------------------

    async def _safe_code_analysis(self, repo: Repository) -> CodeQualityMetrics:
        """Wrap code analysis with exception handling."""
        try:
            return await self.code_analyzer.analyze(repo)
        except Exception as e:
            logger.error("module=pipeline", operation="code_error",
                          params={"repo": repo.full_name, "error": str(e)})
            return CodeQualityMetrics(overall_score=0.0, errors=[str(e)])

    async def _safe_community_analysis(self, repo: Repository) -> CommunityMetrics:
        """Wrap community analysis with exception handling."""
        try:
            return await self.community_analyzer.analyze(repo)
        except Exception as e:
            logger.error("module=pipeline", operation="community_error",
                          params={"repo": repo.full_name, "error": str(e)})
            return CommunityMetrics(overall_score=0.0, errors=[str(e)])

    async def _safe_maturity_analysis(self, repo: Repository) -> MaturityMetrics:
        """Wrap maturity analysis with exception handling."""
        try:
            return await self.maturity_analyzer.analyze(repo)
        except Exception as e:
            logger.error("module=pipeline", operation="maturity_error",
                          params={"repo": repo.full_name, "error": str(e)})
            return MaturityMetrics(overall_score=0.0, errors=[str(e)])

    # ------------------------------------------------------------------
    # Estimation helpers / 估算辅助工具
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_functionality(repo: Repository) -> float:
        """Estimate feature completeness from available signals."""
        score = 50.0  # Base / 基础分
        if repo.description and len(repo.description) > 50:
            score += 10.0
        if repo.topics and len(repo.topics) >= 3:
            score += 15.0
        if repo.language:
            score += 5.0
        if repo.stars > 100:
            score += 20.0  # Popular enough to have features / 足够受欢迎以拥有功能
        return min(100.0, score)

    @staticmethod
    def _estimate_reputation(repo: Repository) -> float:
        """Estimate external reputation from stars/forks ratio."""
        if repo.stars == 0:
            return 10.0
        fork_ratio = repo.forks / max(1, repo.stars)
        base = min(80.0, repo.stars / 500.0 * 60)  # Stars-based / 基于Stars
        penalty = fork_ratio * 20  # High fork ratio can mean less original / 高fork比可能意味着原创性低
        return max(0.0, min(100.0, base - penalty))

    @staticmethod
    def _estimate_sustainability(repo: Repository) -> float:
        """Estimate long-term maintenance viability."""
        score = 40.0
        days_pushed = repo.days_since_last_push
        if days_pushed >= 0 and days_pushed <= 30:
            score += 30.0  # Recently active / 最近活跃
        elif days_pushed >= 0 and days_pushed <= 90:
            score += 15.0
        elif days_pushed >= 0 and days_pushed > 365:
            score -= 15.0  # Stale / 过时
        if repo.license_info:
            score += 20.0  # Licensed is sustainable / 有许可证是可持续的
        if repo.watchers > 50:
            score += 10.0
        return min(100.0, max(0.0, score))


__all__ = ["AnalysisPipeline"]
