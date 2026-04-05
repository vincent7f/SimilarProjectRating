#!/usr/bin/env python3
"""
Pipeline Orchestrator with Resume Support - Enhanced version with checkpointing.

Extends the standard orchestrator with task checkpointing, parallel execution
control, and session resumption capabilities.

支持恢复的流水线协调器 - 带有检查点功能的增强版本.
扩展标准协调器,提供任务检查点,并行执行控制和会话恢复能力.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.pipeline.orchestrator import PipelineOrchestrator
from src.utils.resume_manager import ResumeManager, TaskType, TaskStatus, create_resume_manager_from_session
from src.models.session import AnalysisSession, SessionStatus, LogEntry, SessionSummary
from src.models.repository import Repository
from src.models.search import KeywordGroup
from src.models.analysis import AnalysisResult, ProjectScore, RankedProject
from src.utils.logger import get_logger
from src.utils.config import ParallelConfig
from src.analysis.pipeline_parallel import EnhancedAnalysisPipeline, create_enhanced_pipeline

logger = get_logger(__name__)


class PipelineOrchestratorWithResume(PipelineOrchestrator):
    """Enhanced orchestrator with resume support and parallel execution control."""
    
    def __init__(
        self,
        config: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        max_concurrent_non_ai: int = 5,
        max_concurrent_ai: int = 1,
        enable_resume: bool = True,
        use_enhanced_pipeline: bool = True
    ) -> None:
        """Initialize enhanced orchestrator.
        
        Args:
            config: Configuration object.
            llm_client: LLM client instance.
            max_concurrent_non_ai: Maximum concurrent non-AI tasks.
            max_concurrent_ai: Maximum concurrent AI-dependent tasks.
            enable_resume: Enable resume checkpointing.
            use_enhanced_pipeline: Use enhanced pipeline with AI/non-AI concurrency.
        """
        super().__init__(config, llm_client)
        
        self.enable_resume = enable_resume
        self.use_enhanced_pipeline = use_enhanced_pipeline
        
        # Override parallel config based on CLI arguments
        if config and hasattr(config, 'parallel'):
            config.parallel.ai_concurrent_limit = max_concurrent_ai
            config.parallel.non_ai_concurrent_limit = max_concurrent_non_ai
            config.parallel.enable_parallel_ai = max_concurrent_ai > 1
        else:
            # Create parallel config if not present
            parallel_config = ParallelConfig(
                ai_concurrent_limit=max_concurrent_ai,
                non_ai_concurrent_limit=max_concurrent_non_ai,
                enable_parallel_ai=max_concurrent_ai > 1
            )
            if not hasattr(config, 'parallel'):
                config.parallel = parallel_config
        
        self.max_concurrent_non_ai = max_concurrent_non_ai
        self.max_concurrent_ai = max_concurrent_ai
        
        # Replace analysis pipeline with enhanced version if requested
        if use_enhanced_pipeline and config:
            # Check if GitReverse is enabled and we should use adaptive pipeline
            # 检查是否启用了GitReverse且应该使用自适应流水线
            use_gitreverse = hasattr(config, 'gitreverse') and config.gitreverse.enabled
            
            if use_gitreverse:
                logger.info(f"Using ADAPTIVE analysis pipeline (GitReverse enabled) with AI={max_concurrent_ai}, Non-AI={max_concurrent_non_ai}")
                self.analysis_pipeline = self._create_adaptive_pipeline(config)
            else:
                logger.info(f"Using enhanced analysis pipeline (no GitReverse) with AI={max_concurrent_ai}, Non-AI={max_concurrent_non_ai}")
                self.analysis_pipeline = create_enhanced_pipeline(
                    config=self.config,
                    github_client=self.github,
                    code_analyzer=None,
                    community_analyzer=None,
                    maturity_analyzer=None
                )
        else:
            logger.info("Using standard analysis pipeline")
        
        # Resume manager will be initialized in run_with_resume
        self.resume_manager: Optional[ResumeManager] = None
    
    async def run_with_resume(
        self,
        query: str,
        session_id: Optional[str] = None,
        max_projects: Optional[int] = None,
        dry_run: bool = False,
        resume: bool = True
    ) -> Tuple[AnalysisSession, Optional[ResumeManager]]:
        """Execute pipeline with resume support.
        
        Args:
            query: User search query.
            session_id: Existing session ID for resumption.
            max_projects: Maximum projects to analyze.
            dry_run: Dry run mode.
            resume: Enable resume from checkpoint.
            
        Returns:
            Tuple of (AnalysisSession, ResumeManager)
        """
        # Initialize resume manager
        if session_id and resume:
            self.resume_manager = create_resume_manager_from_session(session_id)
            if self.resume_manager and self.resume_manager.can_resume():
                logger.info(f"Resuming session: {session_id}")
                return await self._resume_session(self.resume_manager, dry_run)
            else:
                logger.info(f"No valid checkpoint found for session: {session_id}")
                # Fall through to new session
        
        # Start new session
        self.resume_manager = ResumeManager(
            session_id=session_id,
            max_concurrent_non_ai=self.max_concurrent_non_ai,
            max_concurrent_ai=self.max_concurrent_ai
        )
        
        # Initialize resume state
        resume_state = self.resume_manager.initialize_new_session(query)
        logger.info(f"Started new session with resume support: {resume_state.session_id}")
        
        # Execute pipeline with checkpointing
        session = await self._execute_with_checkpoints(resume_state, query, max_projects, dry_run)
        
        return session, self.resume_manager
    
    async def _execute_with_checkpoints(
        self,
        resume_state,
        query: str,
        max_projects: Optional[int] = None,
        dry_run: bool = False
    ) -> AnalysisSession:
        """Execute pipeline with task checkpointing."""
        session_id = resume_state.session_id
        start_time = datetime.now(timezone.utc)
        logs: List[LogEntry] = []
        
        session = AnalysisSession(
            session_id=session_id,
            query=query,
            status=SessionStatus.RUNNING,
            start_time=start_time,
            config_snapshot={
                "max_projects": max_projects or self.config.analysis.max_projects,
                "threshold": self.config.analysis.min_similarity_score,
                "weights": dict(self.config.scoring.weights),
                "ai_provider": self.config.ai.provider,
                "ai_model": self.config.ai.model,
                "max_concurrent_non_ai": self.max_concurrent_non_ai,
                "max_concurrent_ai": self.max_concurrent_ai
            },
            logs=logs,
        )
        
        try:
            # Map task IDs to async functions
            task_funcs = {
                "keyword_generation": lambda: self.keyword_gen.generate(query),
                "github_search": lambda: self._execute_github_search(resume_state),
                "project_filtering": lambda: self._execute_project_filtering(resume_state, query, max_projects),
                "code_analysis": lambda: self._execute_code_analysis(resume_state),
                "community_analysis": lambda: self._execute_community_analysis(resume_state),
                "maturity_analysis": lambda: self._execute_maturity_analysis(resume_state),
                "score_calculation": lambda: self._execute_score_calculation(resume_state),
                "ranking": lambda: self._execute_ranking(resume_state),
                "ai_recommendation": lambda: self._execute_ai_recommendation(resume_state, query),
                "ai_explanation": lambda: self._execute_ai_explanation(resume_state, query),
                "report_generation": lambda: self._execute_report_generation(resume_state, query, start_time)
            }
            
            # Execute tasks with resume manager
            results = await self.resume_manager.execute_pipeline(task_funcs)
            
            # Collect results into session
            session = await self._collect_results_into_session(
                session, resume_state, results, query, start_time
            )
            
            # Finalize session
            session.status = SessionStatus.COMPLETED
            session.end_time = datetime.now(timezone.utc)
            
            # Save to database
            self.db.initialize_schema()
            self.db.create_session(session_id, query)
            
            # Clean up checkpoints if successful
            if self.enable_resume:
                self.resume_manager.cleanup()
            
            logger.info(f"Pipeline completed with resume support: {session_id}")
            
            return session
            
        except Exception as e:
            session.status = SessionStatus.FAILED
            session.end_time = datetime.now(timezone.utc)
            session.logs = logs
            
            logger.error(f"Pipeline failed with resume support: {session_id} - {e}")
            
            # Keep checkpoint for potential resumption
            if self.resume_manager and self.enable_resume:
                logger.info(f"Checkpoint saved for failed session: {session_id}")
            
            return session
    
    async def _resume_session(
        self,
        resume_manager: ResumeManager,
        dry_run: bool = False
    ) -> Tuple[AnalysisSession, ResumeManager]:
        """Resume execution from checkpoint."""
        resume_state = resume_manager.state
        if not resume_state:
            raise ValueError("No resume state available")
        
        session_id = resume_state.session_id
        query = resume_state.query
        
        logger.info(f"Resuming session {session_id} from checkpoint")
        
        # Check completion percentage
        completion_pct = resume_manager.get_completion_percentage()
        next_task_index, completed_tasks = resume_manager.get_resume_point()
        
        logger.info(f"Session progress: {completion_pct:.1f}% complete")
        logger.info(f"Completed tasks: {completed_tasks}")
        logger.info(f"Next task index: {next_task_index}")
        
        # Continue execution
        session = await self._execute_with_checkpoints(resume_state, query, None, dry_run)
        
        return session, resume_manager
    
    async def _execute_github_search(self, resume_state) -> List[Repository]:
        """Execute GitHub search task."""
        query = resume_state.query
        
        # Check if we have keyword groups from previous task
        session_data = resume_state.session_data
        if "keyword_groups" in session_data:
            keyword_groups = session_data["keyword_groups"]
        else:
            # Should not happen if dependencies are correct
            raise ValueError("Keyword groups not found in session data")
        
        all_candidates: List[Repository] = []
        for kg in keyword_groups:
            query_str = kg.build_search_query() if hasattr(kg, 'build_search_query') else str(kg)
            candidates = await self.github.search_repositories(
                query=query_str,
                max_results=30,
            )
            all_candidates.extend(candidates)
        
        # Deduplicate
        seen = set()
        unique_candidates: List[Repository] = []
        for c in all_candidates:
            if c.full_name not in seen:
                seen.add(c.full_name)
                unique_candidates.append(c)
        
        return unique_candidates
    
    async def _execute_project_filtering(
        self, 
        resume_state, 
        query: str, 
        max_projects: Optional[int]
    ) -> Any:
        """Execute project filtering task."""
        # Get candidates from session data
        session_data = resume_state.session_data
        candidates = session_data.get("candidate_projects", [])
        
        if not candidates:
            raise ValueError("No candidate projects found for filtering")
        
        filter_result = await self.project_filter.filter(
            candidates=candidates,
            query=query,
            max_projects=max_projects or self.config.analysis.max_projects,
        )
        
        return filter_result
    
    async def _execute_code_analysis(self, resume_state) -> List[AnalysisResult]:
        """Execute code analysis task."""
        session_data = resume_state.session_data
        filtered_projects = session_data.get("filtered_projects", [])
        
        if not filtered_projects.kept:
            raise ValueError("No filtered projects for analysis")
        
        # Analyze in parallel with pipeline's concurrency settings
        analysis_results = await self.analysis_pipeline.analyze_batch(filtered_projects.kept)
        
        return analysis_results
    
    async def _execute_community_analysis(self, resume_state) -> Any:
        """Execute community analysis task.
        
        Note: This is handled by the analysis pipeline, so we return a placeholder.
        """
        return {"status": "completed_by_analysis_pipeline"}
    
    async def _execute_maturity_analysis(self, resume_state) -> Any:
        """Execute maturity analysis task.
        
        Note: This is handled by the analysis pipeline, so we return a placeholder.
        """
        return {"status": "completed_by_analysis_pipeline"}
    
    async def _execute_score_calculation(self, resume_state) -> List[ProjectScore]:
        """Execute score calculation task."""
        session_data = resume_state.session_data
        analysis_results = session_data.get("analysis_results_partial", [])
        
        if not analysis_results:
            raise ValueError("No analysis results for scoring")
        
        scored = self.scorer.calculate_batch_scores(analysis_results)
        return scored
    
    async def _execute_ranking(self, resume_state) -> List[RankedProject]:
        """Execute ranking task."""
        session_data = resume_state.session_data
        scored = session_data.get("scored_projects", [])
        analysis_results = session_data.get("analysis_results_partial", [])
        
        if not scored:
            raise ValueError("No scored projects for ranking")
        
        ranked = self.ranker.rank_by_comprehensive(
            scored,
            [r.project for r in analysis_results],
        )
        
        return ranked
    
    async def _execute_ai_recommendation(
        self, 
        resume_state, 
        query: str
    ) -> List[RankedProject]:
        """Execute AI recommendation task."""
        session_data = resume_state.session_data
        scored = session_data.get("scored_projects", [])
        analysis_results = session_data.get("analysis_results_partial", [])
        
        if not scored:
            raise ValueError("No scored projects for recommendation")
        
        recommendations = await self.recommender.recommend(
            scored, [r.project for r in analysis_results], query
        )
        
        return recommendations
    
    async def _execute_ai_explanation(
        self, 
        resume_state, 
        query: str
    ) -> str:
        """Execute AI explanation task."""
        session_data = resume_state.session_data
        recommendations = session_data.get("recommendations", [])
        
        if not recommendations:
            raise ValueError("No recommendations for explanation")
        
        explanation = await self.explainer.explain_comparison(recommendations[:10], query)
        return explanation
    
    async def _execute_report_generation(
        self,
        resume_state,
        query: str,
        start_time: datetime
    ) -> str:
        """Execute report generation task."""
        session_data = resume_state.session_data
        ranked = session_data.get("ranked_projects", [])
        explanation = session_data.get("explanation", "")
        
        if not ranked:
            raise ValueError("No ranked projects for report generation")
        
        total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Export to Markdown
        markdown_filepath = self.markdown_exporter.export_ranked_projects(
            query=query,
            ranked=ranked,
            session_id=resume_state.session_id,
            duration_seconds=total_duration,
            explanation=explanation,
            format_type="detailed"
        )
        
        return str(markdown_filepath)
    
    async def _collect_results_into_session(
        self,
        session: AnalysisSession,
        resume_state,
        results: Dict[str, Any],
        query: str,
        start_time: datetime
    ) -> AnalysisSession:
        """Collect task results into session object."""
        session_data = resume_state.session_data
        
        # Collect results from session data
        keyword_groups = session_data.get("keyword_groups", [])
        candidate_projects = session_data.get("candidate_projects", [])
        filtered_projects = session_data.get("filtered_projects", None)
        analysis_results = session_data.get("analysis_results_partial", [])
        scored_projects = session_data.get("scored_projects", [])
        ranked_projects = session_data.get("ranked_projects", [])
        explanation = session_data.get("explanation", "")
        report_path = session_data.get("report_path", "")
        
        # Update session
        session.keyword_groups = [kg.__dict__ if hasattr(kg, '__dict__') else kg 
                                 for kg in keyword_groups]
        session.candidate_projects = candidate_projects
        
        if filtered_projects:
            session.filtered_projects = filtered_projects.kept
        
        session.analysis_results = analysis_results
        session.ranked_results = ranked_projects
        session.report_path = report_path
        
        # Create summary
        total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        summary = SessionSummary(
            session_id=session.session_id,
            query=query,
            start_time=start_time,
            end_time=datetime.now(timezone.utc),
            status=SessionStatus.COMPLETED,
            total_projects_found=len(candidate_projects),
            projects_analyzed=len(analysis_results),
            projects_filtered_out=len(candidate_projects) - len(analysis_results),
            total_duration_seconds=total_duration,
            average_analysis_time=(
                sum(ar.analysis_duration_ms for ar in analysis_results)
                / max(1, len(analysis_results)) / 1000.0
            ),
            successes=[f"Successfully analyzed {len(analysis_results)} projects"],
            optimization_suggestions=[
                f"Query '{query}' yielded {len(candidate_projects)} initial candidates",
                f"Resume checkpointing enabled with {self.max_concurrent_ai} AI / {self.max_concurrent_non_ai} non-AI concurrency"
            ],
            next_run_recommendations=[
                "Resume capability allows continuation from interruptions",
                f"Consider adjusting concurrency (AI: {self.max_concurrent_ai}, Non-AI: {self.max_concurrent_non_ai}) for performance tuning"
            ],
        )
        
        session.summary = summary
        return session

    def _create_adaptive_pipeline(self, config: Any) -> Any:
        """Create adaptive analysis pipeline based on GitReverse configuration.
        
        基于GitReverse配置创建自适应分析流水线.
        
        Args:
            config: Configuration object.
                    配置对象.
            
        Returns:
            AdaptiveAnalysisPipeline instance.
            AdaptiveAnalysisPipeline实例.
        """
        try:
            from src.analysis.adaptive_pipeline import AdaptiveAnalysisPipeline
            
            # Create adaptive pipeline
            # 创建自适应流水线
            return AdaptiveAnalysisPipeline(
                config=config,
                github_client=self.github,
                parallel_analysis=True,
                max_concurrent=self.max_concurrent_non_ai  # Use non-AI concurrency for overall limit
            )
        except ImportError as e:
            logger.error(
                "module=orchestrator", operation="adaptive_pipeline_import_error",
                params={"error": str(e)},
            )
            # Fall back to enhanced pipeline
            # 回退到增强流水线
            from src.analysis.pipeline_parallel import create_enhanced_pipeline
            return create_enhanced_pipeline(
                config=config,
                github_client=self.github,
                code_analyzer=None,
                community_analyzer=None,
                maturity_analyzer=None
            )


# Convenience functions for command line usage
async def run_with_resume(
    query: str,
    session_id: Optional[str] = None,
    max_projects: Optional[int] = None,
    max_concurrent_non_ai: int = 5,
    max_concurrent_ai: int = 1,
    dry_run: bool = False,
    resume: bool = True,
    use_enhanced_pipeline: bool = True,
    config: Optional[Any] = None
) -> Tuple[AnalysisSession, Optional[ResumeManager]]:
    """Convenience function to run pipeline with resume support.
    
    Args:
        query: User search query.
        session_id: Existing session ID for resumption.
        max_projects: Maximum projects to analyze.
        max_concurrent_non_ai: Maximum concurrent non-AI tasks.
        max_concurrent_ai: Maximum concurrent AI tasks.
        dry_run: Dry run mode.
        resume: Enable resume from checkpoint.
        use_enhanced_pipeline: Use enhanced pipeline with AI/non-AI concurrency.
        config: Configuration object (optional).
        
    Returns:
        Tuple of (AnalysisSession, ResumeManager)
    """
    orchestrator = PipelineOrchestratorWithResume(
        config=config,
        max_concurrent_non_ai=max_concurrent_non_ai,
        max_concurrent_ai=max_concurrent_ai,
        enable_resume=resume,
        use_enhanced_pipeline=use_enhanced_pipeline
    )
    
    return await orchestrator.run_with_resume(
        query=query,
        session_id=session_id,
        max_projects=max_projects,
        dry_run=dry_run,
        resume=resume
    )


__all__ = [
    "PipelineOrchestratorWithResume",
    "run_with_resume"
]