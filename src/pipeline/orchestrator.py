"""
Pipeline Orchestrator - End-to-End Analysis Flow Coordinator.

Coordinates the complete analysis pipeline from user query input
through search, filter, analyze, score, rank, recommend, and report output.
This is the main orchestration layer that ties all modules together.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.analysis.pipeline import AnalysisPipeline
from src.models.analysis import AnalysisResult, ComparisonTable, ProjectScore, RankedProject
from src.models.session import (
    AnalysisSession,
    LogEntry,
    SessionStatus,
    SessionSummary,
    ExperienceEntry,
)
from src.models.repository import Repository
from src.models.search import FilterResult, KeywordGroup, SearchQuery
from src.scoring.score_calculator import ScoreCalculator
from src.scoring.ranking_engine import RankingEngine
from src.search.github_client import GitHubClient
from src.search.keyword_generator import KeywordGenerator
from src.search.project_filter import ProjectFilter
from src.ai.llm_client import LLMClient
from src.ai.recommender import Recommender
from src.ai.explainer import Explainer
from src.storage.database import Database
from src.utils.config import Config, load_config
from src.utils.logger import setup_logger, get_logger

logger = get_logger(__name__)


class PipelineOrchestrator:
    """Full analysis pipeline orchestrator.

    Manages the end-to-end workflow:
    1. Initialize configuration and logging
    2. Generate search keywords via AI
    3. Search GitHub for candidate projects
    4. Filter irrelevant projects via AI relevance check
    5. Analyze filtered projects in parallel (code/community/maturity)
    6. Calculate multi-dimensional scores
    7. Rank and generate recommendations
    8. Output reports and session summary
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self.config = config or load_config()
        self.db = Database()

        # Initialize clients / 初始化客户端
        self.github = GitHubClient(self.config.github)
        self.llm_client = llm_client or LLMClient(self.config)

        # Initialize modules / 初始化模块
        self.keyword_gen = KeywordGenerator(llm_client=self.llm_client)
        self.project_filter = ProjectFilter(
            llm_client=self.llm_client,
            threshold=self.config.analysis.min_similarity_score,
            max_projects=self.config.analysis.max_projects,
        )
        self.analysis_pipeline = AnalysisPipeline(
            github_client=self.github,
            parallel_analysis=self.config.analysis.parallel_analysis,
            max_concurrent=self.config.analysis.max_concurrent_analyses,
        )
        self.scorer = ScoreCalculator(
            weights=dict(self.config.scoring.weights),
        )
        self.ranker = RankingEngine()
        self.recommender = Recommender(llm_client=self.llm_client)
        self.explainer = Explainer(llm_client=self.llm_client)

        # Logging / 日志
        self.app_logger = setup_logger(
            name="orchestrator",
            log_dir=self.config.logging.file_path,
            level=self.config.logging.level,
            console_output=self.config.logging.console_output,
            json_format=self.config.logging.json_format,
        )

    async def run(
        self,
        query: str,
        max_projects: Optional[int] = None,
        dry_run: bool = False,
    ) -> AnalysisSession:
        """Execute the complete analysis pipeline."""
        session_id = str(uuid.uuid4())[:12]
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
            },
            logs=logs,
        )

        try:
            # Step 1: Keywords / 步骤1：关键词
            self._log_step(logs, "keyword_generation", "start")
            keyword_groups: List[KeywordGroup] = await self.keyword_gen.generate(query)

            # Step 2: Search / 步骤2：搜索
            self._log_step(logs, "github_search", "start")
            all_candidates: List[Repository] = []
            for kg in keyword_groups:
                query_str = kg.build_search_query()
                candidates = await self.github.search_repositories(
                    query=query_str,
                    max_results=50 if dry_run else 30,
                )
                all_candidates.extend(candidates)

            # Deduplicate / 去重
            seen: set = set()
            unique_candidates: List[Repository] = []
            for c in all_candidates:
                if c.full_name not in seen:
                    seen.add(c.full_name)
                    unique_candidates.append(c)

            self._log_step(logs, "github_search", "complete",
                        results={"total_found": len(unique_candidates)})

            session.candidate_projects = unique_candidates
            session.keyword_groups = [kg.__dict__ for kg in keyword_groups]

            # Step 3: Filter / 步骤3：过滤
            self._log_step(logs, "filter", "start")
            filter_result: FilterResult = await self.project_filter.filter(
                candidates=unique_candidates,
                query=query,
                max_projects=max_projects or self.config.analysis.max_projects,
            )

            session.filtered_projects = filter_result.kept
            self._log_step(logs, "filter", "complete",
                        results={"kept": len(filter_result.kept),
                                "removed": len(filter_result.removed)})

            if not filter_result.kept:
                raise ValueError("No relevant projects found after filtering.")

            # Step 4: Analyze / 步骤4：分析
            self._log_step(logs, "analysis", "start")
            analysis_results: List[AnalysisResult] = await \
                self.analysis_pipeline.analyze_batch(filter_result.kept)

            session.analysis_results = analysis_results
            self._log_step(logs, "analysis", "complete",
                        results={"analyzed": len(analysis_results)})

            # Step 5: Score / 步骤5：评分
            self._log_step(logs, "scoring", "start")
            scored: List[ProjectScore] = self.scorer.calculate_batch_scores(analysis_results)

            # Step 6: Rank / 步骤6：排名
            ranked: List[RankedProject] = self.ranker.rank_by_comprehensive(
                scored,
                [r.project for r in analysis_results],
            )

            session.ranked_results = ranked

            # Step 7: Recommend & Explain / 步骤7：推荐与解释
            self._log_step(logs, "recommendation", "start")
            recommendations: List[RankedProject] = await self.recommender.recommend(
                scored, [r.project for r in analysis_results], query,
            )

            # Step 8: Report / 步骤8：报告
            explanation = await self.explainer.explain_comparison(recommendations[:10], query)

            # Save to database / 保存到数据库
            self.db.initialize_schema()
            self.db.create_session(session_id, query)
            for ar in analysis_results:
                self.db.save_analysis_result({
                    "session_id": session_id,
                    "project_full_name": ar.project.full_name,
                    "code_quality_score": ar.code_metrics.overall_score,
                    "community_score": ar.community_metrics.overall_score,
                    "maturity_score": ar.maturity_metrics.overall_score,
                    "functionality_score": ar.functionality_score,
                    "reputation_score": ar.reputation_score,
                    "sustainability_score": ar.sustainability_score,
                    "comprehensive_score": 0,  # Will be updated below / 将在下方更新
                    "rank": 0,
                    "tier": "",
                    "analysis_duration_ms": ar.analysis_duration_ms,
                })

            # Summary / 总结
            total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            summary = SessionSummary(
                session_id=session_id,
                query=query,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                status=SessionStatus.COMPLETED,
                total_projects_found=len(unique_candidates),
                projects_analyzed=len(analysis_results),
                projects_filtered_out=len(unique_candidates) - len(analysis_results),
                total_duration_seconds=total_duration,
                average_analysis_time=(
                    sum(ar.analysis_duration_ms for ar in analysis_results)
                    / max(1, len(analysis_results)) / 1000.0
                ),
                successes=[f"Successfully analyzed {len(analysis_results)} projects"],
                optimization_suggestions=[
                    f"Query '{query}' yielded {len(unique_candidates)} initial candidates",
                ],
                next_run_recommendations=[
                    "Try more specific or different keywords for better targeting",
                ],
            )

            session.status = SessionStatus.COMPLETED
            session.end_time = datetime.now(timezone.utc)
            session.summary = summary
            session.logs = logs

            self.db.update_session_status(session_id, SessionStatus.COMPLETED.value,
                                        {"query": query, "status": "completed"})

            logger.info("module=pipeline", operation="pipeline_complete",
                       params={"session_id": session_id, "duration_s": total_duration})

            return session

        except Exception as e:
            session.status = SessionStatus.FAILED
            session.end_time = datetime.now(timezone.utc)
            session.logs = logs
            session.summary = SessionSummary(
                session_id=session_id, query=query,
                status=SessionStatus.FAILED,
                failures=[{"issue": "Pipeline execution error",
                            "cause": str(e), "fix": "Check configuration and API access"}],
            )
            self.db.update_session_status(session_id, SessionStatus.FAILED.value)
            return session

    @staticmethod
    def _log_step(
        logs: List[LogEntry],
        operation: str,
        status: str,
        params: Optional[Dict[str, Any]] = None,
        results: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_ms: int = 0,
    ) -> None:
        """Helper to append structured log entries."""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level="INFO" if status == "complete" else ("ERROR" if error else "DEBUG"),
            module="pipeline",
            operation=operation,
            params=params or {},
            results=results or {},
            success=(error is None),
            duration_ms=duration_ms,
            error=error,
        )
        logs.append(entry)


__all__ = ["PipelineOrchestrator"]
