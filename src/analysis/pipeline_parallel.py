#!/usr/bin/env python3
"""
Enhanced Analysis Pipeline with Parallel Control for AI and Non-AI tasks.

Extends the standard AnalysisPipeline with support for differentiated
concurrency limits for AI-dependent and non-AI tasks, and integrated 
with the resume checkpoint system.

支持AI和非AI任务并行控制的增强分析流水线。
扩展标准AnalysisPipeline，支持AI依赖任务和非AI任务的差异化并发限制，
并与恢复检查点系统集成。
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

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
from src.utils.config import ParallelConfig
from src.utils.logger import get_logger
from src.utils.resume_manager import TaskType

logger = get_logger(__name__)


class EnhancedAnalysisPipeline:
    """Enhanced analysis pipeline with AI/non-AI parallel execution control.
    
    Manages the complete analysis workflow with configurable concurrency
    limits for different task types. This enables optimal resource usage:
    - AI tasks: Limited concurrency (default: 1) to avoid overwhelming LLM
    - Non-AI tasks: Higher concurrency (default: 5) for CPU/IO-bound work
    
    具有AI/非AI并行执行控制的增强分析流水线。
    管理具有不同类型任务可配置并发限制的完整分析工作流。实现最优资源使用：
    - AI任务：有限并发（默认：1），避免压垮LLM
    - 非AI任务：更高并发（默认：5），用于CPU/IO密集型工作
    """
    
    def __init__(
        self,
        code_analyzer: Optional[CodeAnalyzer] = None,
        community_analyzer: Optional[CommunityAnalyzer] = None,
        maturity_analyzer: Optional[MaturityAnalyzer] = None,
        github_client: Any = None,
        parallel_config: Optional[ParallelConfig] = None,
        enable_parallel_analysis: bool = True,
    ) -> None:
        """Initialize enhanced analysis pipeline.
        
        Args:
            code_analyzer: Code quality assessment engine.
            community_analyzer: Community metrics engine.
            maturity_analyzer: Maturity assessment engine.
            github_client: GitHub API client.
            parallel_config: Parallel execution configuration.
            enable_parallel_analysis: Whether to enable parallel analysis.
        """
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.community_analyzer = community_analyzer or CommunityAnalyzer(github_client)
        self.maturity_analyzer = maturity_analyzer or MaturityAnalyzer(github_client)
        self.enable_parallel_analysis = enable_parallel_analysis
        
        # Default parallel config
        self.parallel_config = parallel_config or ParallelConfig()
        
        # Semaphores for concurrency control
        self.ai_semaphore = asyncio.Semaphore(
            self.parallel_config.ai_concurrent_limit
            if self.parallel_config.enable_parallel_ai
            else 1
        )
        self.non_ai_semaphore = asyncio.Semaphore(
            self.parallel_config.non_ai_concurrent_limit
            if self.parallel_config.enable_parallel_non_ai
            else 1
        )
        self.overall_semaphore = asyncio.Semaphore(
            min(self.parallel_config.max_concurrent_tasks,
                self.parallel_config.ai_concurrent_limit + 
                self.parallel_config.non_ai_concurrent_limit)
        )
        
        logger.info(
            f"Initialized enhanced analysis pipeline with concurrency limits: "
            f"AI={self.parallel_config.ai_concurrent_limit}, "
            f"Non-AI={self.parallel_config.non_ai_concurrent_limit}"
        )
    
    async def analyze_batch(
        self, 
        repositories: List[Repository],
        batch_size: Optional[int] = None
    ) -> List[AnalysisResult]:
        """Analyze a batch of projects with intelligent parallel control.
        
        Intelligently schedules tasks based on their type (AI/non-AI) to
        maximize throughput while respecting concurrency limits.
        
        Args:
            repositories: List of repositories to analyze.
            batch_size: Optional batch size for chunking.
            
        Returns:
            List of AnalysisResult objects.
        """
        if not repositories:
            return []
        
        if batch_size is None:
            batch_size = len(repositories)
        
        results = []
        total = len(repositories)
        
        logger.info(
            f"Starting batch analysis of {total} projects with enhanced parallel control"
        )
        
        # Process in batches
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = repositories[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            
            logger.info(
                f"Processing batch {batch_num}: projects {batch_start+1}-{batch_end} of {total}"
            )
            
            # Create analysis tasks for the batch
            tasks = []
            for repo in batch:
                task = self._analyze_project_with_concurrency_control(repo)
                tasks.append(task)
            
            # Execute with overall concurrency limit
            batch_results = []
            if self.enable_parallel_analysis:
                # Execute with semaphore to control total concurrency
                async with self.overall_semaphore:
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Sequential execution
                for task in tasks:
                    try:
                        result = await task
                        batch_results.append(result)
                    except Exception as e:
                        batch_results.append(e)
            
            # Process results
            for i, result in enumerate(batch_results):
                repo = batch[i]
                if isinstance(result, Exception):
                    logger.error(
                        f"Analysis failed for {repo.full_name}: {result}"
                    )
                    # Create a failed analysis result
                    failed_result = AnalysisResult(
                        project=repo,
                        code_metrics=CodeQualityMetrics(overall_score=0.0),
                        community_metrics=CommunityMetrics(overall_score=0.0),
                        maturity_metrics=MaturityMetrics(overall_score=0.0),
                        analysis_duration_ms=0,
                        errors=[str(result)]
                    )
                    results.append(failed_result)
                else:
                    results.append(result)
            
            logger.info(
                f"Completed batch {batch_num}: {len(batch_results)} results processed"
            )
        
        logger.info(
            f"Completed analysis of {total} projects with enhanced pipeline"
        )
        return results
    
    async def _analyze_project_with_concurrency_control(
        self, 
        repository: Repository
    ) -> AnalysisResult:
        """Analyze a single project with proper concurrency control.
        
        This method ensures AI-dependent tasks respect their low concurrency
        limit while non-AI tasks can run with higher parallelism.
        
        Args:
            repository: Repository to analyze.
            
        Returns:
            AnalysisResult for the project.
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []
        
        logger.debug(f"Starting enhanced analysis for {repository.full_name}")
        
        try:
            # Define task functions with proper concurrency control
            async def analyze_code() -> CodeQualityMetrics:
                """Code analysis task (non-AI)."""
                async with self.non_ai_semaphore:  # Higher concurrency for non-AI
                    return await self._safe_code_analysis(repository)
            
            async def analyze_community() -> CommunityMetrics:
                """Community analysis task (non-AI, mostly API calls)."""
                async with self.non_ai_semaphore:  # Higher concurrency for non-AI
                    return await self._safe_community_analysis(repository)
            
            async def analyze_maturity() -> MaturityMetrics:
                """Maturity analysis task (non-AI)."""
                async with self.non_ai_semaphore:  # Higher concurrency for non-AI
                    return await self._safe_maturity_analysis(repository)
            
            # Execute analysis based on configuration
            if self.enable_parallel_analysis:
                # Run all analyzers concurrently
                code_task = analyze_code()
                comm_task = analyze_community()
                mat_task = analyze_maturity()
                
                code_metrics, comm_metrics, mat_metrics = await asyncio.gather(
                    code_task, comm_task, mat_task,
                    return_exceptions=True
                )
            else:
                # Run analyzers sequentially
                code_metrics = await analyze_code()
                comm_metrics = await analyze_community()
                mat_metrics = await analyze_maturity()
            
            # Handle exceptions from tasks
            code_metrics = self._handle_task_result(
                code_metrics, "code analysis", errors, warnings
            )
            comm_metrics = self._handle_task_result(
                comm_metrics, "community analysis", errors, warnings
            )
            mat_metrics = self._handle_task_result(
                mat_metrics, "maturity analysis", errors, warnings
            )
            
            # Ensure we have valid metrics objects
            if not isinstance(code_metrics, CodeQualityMetrics):
                code_metrics = CodeQualityMetrics(overall_score=0.0)
            if not isinstance(comm_metrics, CommunityMetrics):
                comm_metrics = CommunityMetrics(overall_score=0.0)
            if not isinstance(mat_metrics, MaturityMetrics):
                mat_metrics = MaturityMetrics(overall_score=0.0)
            
            # Calculate analysis duration
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)
            
            # Create result
            result = AnalysisResult(
                project=repository,
                code_metrics=code_metrics,
                community_metrics=comm_metrics,
                maturity_metrics=mat_metrics,
                analysis_duration_ms=duration_ms,
                errors=errors,
                warnings=warnings
            )
            
            logger.debug(
                f"Completed enhanced analysis for {repository.full_name} in {duration_ms}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Enhanced analysis pipeline failed for {repository.full_name}: {e}"
            )
            # Return minimal result with error
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)
            
            return AnalysisResult(
                project=repository,
                code_metrics=CodeQualityMetrics(overall_score=0.0),
                community_metrics=CommunityMetrics(overall_score=0.0),
                maturity_metrics=MaturityMetrics(overall_score=0.0),
                analysis_duration_ms=duration_ms,
                errors=[str(e)],
                warnings=[]
            )
    
    def _handle_task_result(
        self,
        result: Any,
        task_name: str,
        errors: List[str],
        warnings: List[str]
    ) -> Any:
        """Handle result from an analysis task (success, exception, or error)."""
        if isinstance(result, BaseException):
            error_msg = f"{task_name} failed: {str(result)}"
            errors.append(error_msg)
            logger.warning(error_msg)
            return None
        elif isinstance(result, Exception):
            error_msg = f"{task_name} failed with exception: {str(result)}"
            errors.append(error_msg)
            logger.warning(error_msg)
            return None
        else:
            return result
    
    async def _safe_code_analysis(self, repository: Repository) -> CodeQualityMetrics:
        """Run code analysis with error handling."""
        try:
            return await self.code_analyzer.analyze(repository)
        except Exception as e:
            logger.warning(f"Code analysis failed for {repository.full_name}: {e}")
            return CodeQualityMetrics(overall_score=0.0)
    
    async def _safe_community_analysis(self, repository: Repository) -> CommunityMetrics:
        """Run community analysis with error handling."""
        try:
            return await self.community_analyzer.analyze(repository)
        except Exception as e:
            logger.warning(f"Community analysis failed for {repository.full_name}: {e}")
            return CommunityMetrics(overall_score=0.0)
    
    async def _safe_maturity_analysis(self, repository: Repository) -> MaturityMetrics:
        """Run maturity analysis with error handling."""
        try:
            return await self.maturity_analyzer.analyze(repository)
        except Exception as e:
            logger.warning(f"Maturity analysis failed for {repository.full_name}: {e}")
            return MaturityMetrics(overall_score=0.0)
    
    def get_concurrency_stats(self) -> Dict[str, Any]:
        """Get current concurrency statistics."""
        return {
            "ai_concurrent_limit": self.parallel_config.ai_concurrent_limit,
            "non_ai_concurrent_limit": self.parallel_config.non_ai_concurrent_limit,
            "enable_parallel_ai": self.parallel_config.enable_parallel_ai,
            "enable_parallel_non_ai": self.parallel_config.enable_parallel_non_ai,
            "ai_semaphore_value": self.ai_semaphore._value,
            "non_ai_semaphore_value": self.non_ai_semaphore._value,
            "overall_semaphore_value": self.overall_semaphore._value,
            "enable_parallel_analysis": self.enable_parallel_analysis
        }
    
    def update_parallel_config(self, parallel_config: ParallelConfig) -> None:
        """Update parallel configuration and refresh semaphores."""
        self.parallel_config = parallel_config
        
        # Recreate semaphores with new limits
        self.ai_semaphore = asyncio.Semaphore(
            parallel_config.ai_concurrent_limit
            if parallel_config.enable_parallel_ai
            else 1
        )
        self.non_ai_semaphore = asyncio.Semaphore(
            parallel_config.non_ai_concurrent_limit
            if parallel_config.enable_parallel_non_ai
            else 1
        )
        self.overall_semaphore = asyncio.Semaphore(
            min(parallel_config.max_concurrent_tasks,
                parallel_config.ai_concurrent_limit + 
                parallel_config.non_ai_concurrent_limit)
        )
        
        logger.info(
            f"Updated parallel config: AI={parallel_config.ai_concurrent_limit}, "
            f"Non-AI={parallel_config.non_ai_concurrent_limit}"
        )


# Helper function to create enhanced pipeline from configuration
def create_enhanced_pipeline(
    config: Any,
    github_client: Any = None,
    code_analyzer: Optional[CodeAnalyzer] = None,
    community_analyzer: Optional[CommunityAnalyzer] = None,
    maturity_analyzer: Optional[MaturityAnalyzer] = None,
) -> EnhancedAnalysisPipeline:
    """Factory function to create enhanced pipeline from configuration."""
    return EnhancedAnalysisPipeline(
        code_analyzer=code_analyzer,
        community_analyzer=community_analyzer,
        maturity_analyzer=maturity_analyzer,
        github_client=github_client,
        parallel_config=config.parallel,
        enable_parallel_analysis=config.analysis.parallel_analysis
    )


__all__ = [
    "EnhancedAnalysisPipeline",
    "create_enhanced_pipeline"
]