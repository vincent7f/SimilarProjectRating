"""
Adaptive Analysis Pipeline - Automatically selects between PromptAnalyzer and CodeAnalyzer.

This pipeline intelligently chooses between GitReverse-based prompt analysis and
traditional code analysis based on configuration and availability. Provides a
unified interface while optimizing for speed when GitReverse is available.

自适应分析流水线 - 自动在PromptAnalyzer和CodeAnalyzer之间选择.

该流水线根据配置和可用性,智能地在基于GitReverse的prompt分析和
传统代码分析之间选择.提供统一的接口,同时在GitReverse可用时优化速度.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from src.analysis.code_analyzer import CodeAnalyzer
from src.analysis.community_analyzer import CommunityAnalyzer
from src.analysis.maturity_analyzer import MaturityAnalyzer
from src.analysis.prompt_analyzer import PromptAnalyzer
from src.models.analysis import AnalysisResult
from src.models.metrics import (
    CodeQualityMetrics,
    CommunityMetrics,
    MaturityMetrics,
)
from src.models.repository import Repository
from src.utils.config import Config, GitReverseConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AdaptiveAnalysisPipeline:
    """Intelligent pipeline that selects optimal analysis method per project.

    Evaluates each project and chooses between:
    1. GitReverse prompt analysis (fast, no code download)
    2. Traditional code analysis (detailed, requires code download)
    
    Allows mixed-mode analysis across a batch of projects.

    为每个项目选择最优分析方法的智能流水线.

    为每个项目评估并选择:
    1. GitReverse prompt分析(快速,无需下载代码)
    2. 传统代码分析(详细,需要下载代码)
    
    允许跨项目批次进行混合模式分析.
    """

    def __init__(
        self,
        config: Config,
        code_analyzer: Optional[CodeAnalyzer] = None,
        prompt_analyzer: Optional[PromptAnalyzer] = None,
        community_analyzer: Optional[CommunityAnalyzer] = None,
        maturity_analyzer: Optional[MaturityAnalyzer] = None,
        github_client: Any = None,
        parallel_analysis: bool = True,
        max_concurrent: int = 4,
    ) -> None:
        self.config = config
        self.gitreverse_config = config.gitreverse
        self.use_gitreverse_by_default = config.gitreverse.enabled
        
        # Initialize analyzers
        self.prompt_analyzer = prompt_analyzer or PromptAnalyzer(config=config.gitreverse)
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.community_analyzer = community_analyzer or CommunityAnalyzer(github_client)
        self.maturity_analyzer = maturity_analyzer or MaturityAnalyzer(github_client)
        
        self.parallel_analysis = parallel_analysis
        self.max_concurrent = max_concurrent
        
        # Statistics for monitoring
        self.stats = {
            "prompt_analyses": 0,
            "code_analyses": 0,
            "fallbacks": 0,
            "total_duration_ms": 0,
        }

    async def analyze_project(self, repository: Repository) -> AnalysisResult:
        """Analyze a single project with optimal method selection.

        为单个项目分析,选择最优方法.

        Args:
            repository: Repository metadata.
                        仓库元数据.

        Returns:
            AnalysisResult with quality metrics.
            包含质量指标的AnalysisResult.
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []

        logger.info(
            "module=analysis", operation="adaptive_pipeline_start",
            params={
                "repo": repository.full_name,
                "use_gitreverse": self.use_gitreverse_by_default,
                "stars": repository.stars,
                "has_description": bool(repository.description),
            },
        )

        try:
            # Determine analysis method for this project / 确定此项目的分析方法
            analysis_method = self._select_analysis_method(repository)
            logger.info(
                "module=analysis", operation="method_selected",
                params={
                    "repo": repository.full_name,
                    "method": analysis_method,
                },
            )

            # Run analysis based on selected method / 基于选择的方法运行分析
            if analysis_method == "prompt":
                code_metrics = await self.prompt_analyzer.analyze(repository)
                self.stats["prompt_analyses"] += 1
                
                # Add metadata indicating prompt analysis was used
                # 添加元数据表明使用了prompt分析
                errors.append("Code analysis performed via GitReverse prompt (no code download)")
                
            elif analysis_method == "code":
                code_metrics = await self.code_analyzer.analyze(repository)
                self.stats["code_analyses"] += 1
                
                # Add metadata indicating traditional analysis was used
                # 添加元数据表明使用了传统分析
                errors.append("Traditional code analysis (code downloaded and parsed)")
                
            else:  # adaptive
                # Try prompt first, fall back to code if needed / 先尝试prompt,需要时回退到代码分析
                try:
                    code_metrics = await self.prompt_analyzer.analyze(repository)
                    self.stats["prompt_analyses"] += 1
                    warnings.append("Used GitReverse prompt analysis")
                    
                    # If the result seems poor (low score with no errors), fall back
                    # 如果结果看起来不理想(低分且没有错误),则回退
                    if (code_metrics.overall_score < 30 and 
                        not code_metrics.errors and 
                        self.gitreverse_config.fallback_to_code):
                        logger.info(
                            "module=analysis", operation="prompt_low_score_fallback",
                            params={
                                "repo": repository.full_name,
                                "score": code_metrics.overall_score,
                            },
                        )
                        code_metrics = await self.code_analyzer.analyze(repository)
                        self.stats["code_analyses"] += 1
                        self.stats["fallbacks"] += 1
                        warnings.append(f"Fell back to code analysis from prompt (score: {code_metrics.overall_score})")
                        
                except Exception as e:
                    logger.warning(
                        "module=analysis", operation="prompt_fallback_triggered",
                        params={
                            "repo": repository.full_name,
                            "error": str(e),
                            "fallback_enabled": self.gitreverse_config.fallback_to_code,
                        },
                    )
                    if self.gitreverse_config.fallback_to_code:
                        code_metrics = await self.code_analyzer.analyze(repository)
                        self.stats["code_analyses"] += 1
                        self.stats["fallbacks"] += 1
                        warnings.append(f"Fell back to code analysis due to error: {str(e)[:100]}")
                    else:
                        raise

            # Run community and maturity analysis (always traditional) / 运行社区和成熟度分析(始终传统)
            if self.parallel_analysis:
                comm_metrics, mat_metrics = await asyncio.gather(
                    self._safe_community_analysis(repository),
                    self._safe_maturity_analysis(repository),
                    return_exceptions=True,
                )

                # Handle exceptions / 处理异常
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
                comm_metrics = await self._safe_community_analysis(repository)
                mat_metrics = await self._safe_maturity_analysis(repository)

            duration_ms = int((time.time() - start_time) * 1000)
            self.stats["total_duration_ms"] += duration_ms

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
                metadata={
                    "analysis_method": analysis_method,
                    "used_prompt_analyzer": analysis_method in ["prompt", "adaptive"],
                    "used_code_analyzer": analysis_method in ["code", "adaptive"],
                    "gitreverse_enabled": self.use_gitreverse_by_default,
                    "fallback_used": "fallback" in analysis_method,
                },
            )

            logger.info(
                "module=analysis", operation="adaptive_pipeline_complete",
                params={
                    "repo": repository.full_name,
                    "method": analysis_method,
                    "duration_ms": duration_ms,
                    "overall_score": result.overall_score,
                    "used_prompt": analysis_method in ["prompt", "adaptive"],
                },
            )
            return result

        except Exception as e:
            logger.error(
                "module=analysis", operation="adaptive_pipeline_error",
                params={"repo": repository.full_name, "error": str(e)},
            )
            return AnalysisResult(
                project=repository,
                errors=[str(e)],
                analysis_duration_ms=int((time.time() - start_time) * 1000),
            )

    def _select_analysis_method(self, repository: Repository) -> str:
        """Determine optimal analysis method for a given repository.

        为给定仓库确定最优分析方法.

        Args:
            repository: Repository metadata.
                        仓库元数据.

        Returns:
            "prompt", "code", or "adaptive"
        """
        # If GitReverse is disabled globally, use code analysis / 如果全局禁用GitReverse,使用代码分析
        if not self.use_gitreverse_by_default:
            return "code"

        # Heuristics for when to prefer prompt analysis / 启发式规则决定何时首选prompt分析
        # 1. Popular repositories likely have good GitReverse coverage
        #    流行的仓库可能有良好的GitReverse覆盖
        if repository.stars > 500:
            return "prompt"
        
        # 2. Repositories with good descriptions might have good prompts
        #    有良好描述的仓库可能有良好的prompt
        if repository.description and len(repository.description) > 100:
            return "prompt"
        
        # 3. Active repositories (recent pushes) are more likely to be up-to-date
        #    活跃的仓库(最近推送)更可能保持最新
        if repository.days_since_last_push <= 90:
            return "prompt"
        
        # 4. Repositories with topics/tags might be better documented
        #    有主题/标签的仓库可能文档更好
        if repository.topics and len(repository.topics) >= 3:
            return "prompt"
        
        # Otherwise start with prompt but be ready to fall back (adaptive)
        # 否则从prompt开始但准备回退(自适应)
        return "adaptive"

    async def analyze_batch(
        self,
        repositories: List[Repository],
    ) -> List[AnalysisResult]:
        """Analyze multiple projects with concurrency control.

        使用并发控制分析多个项目.

        Args:
            repositories: List of repository objects.
                          仓库对象列表.

        Returns:
            List of AnalysisResult objects.
            AnalysisResult对象列表.
        """
        results: List[AnalysisResult] = []

        if not repositories:
            return results

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _bounded_analysis(repo: Repository) -> AnalysisResult:
            async with semaphore:
                return await self.analyze_project(repo)

        tasks = [_bounded_analysis(r) for r in repositories]
        results = await asyncio.gather(*tasks)

        # Log batch statistics / 记录批次统计
        prompt_rate = (self.stats["prompt_analyses"] / len(results)) * 100 if results else 0
        logger.info(
            "module=analysis", operation="adaptive_batch_complete",
            params={
                "total_projects": len(results),
                "prompt_analyses": self.stats["prompt_analyses"],
                "code_analyses": self.stats["code_analyses"],
                "fallbacks": self.stats["fallbacks"],
                "prompt_usage_percentage": round(prompt_rate, 1),
                "avg_duration_ms": self.stats["total_duration_ms"] // max(1, len(results)),
            },
        )
        
        return results

    # ------------------------------------------------------------------
    # Safe wrappers with error isolation / 带错误隔离的安全包装器
    # ------------------------------------------------------------------

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

    async def close(self) -> None:
        """Close all analyzer resources.

        关闭所有分析器资源."""
        try:
            await self.prompt_analyzer.close()
        except Exception as e:
            logger.warning(
                "module=analysis", operation="prompt_analyzer_close_error",
                params={"error": str(e)},
            )
        # CodeAnalyzer has no close method typically / CodeAnalyzer通常没有close方法

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


__all__ = ["AdaptiveAnalysisPipeline"]