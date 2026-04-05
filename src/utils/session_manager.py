#!/usr/bin/env python3
"""
Session Management Module - Session tracking, summarization, and auto-commit support.

Manages analysis sessions, logs execution steps, generates summaries,
and tracks success/failure experiences for future improvements.

会话管理模块 - 会话跟踪,总结和自动提交支持.
管理分析会话,记录执行步骤,生成总结,并跟踪成功/失败经验以供未来改进.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    """Status of an analysis session."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepName(str, Enum):
    """Names of steps in the analysis pipeline."""
    INITIALIZATION = "initialization"
    AI_KEYWORD_GENERATION = "ai_keyword_generation"
    GITHUB_SEARCH = "github_search"
    PROJECT_FILTERING = "project_filtering"
    CODE_ANALYSIS = "code_analysis"
    COMMUNITY_ANALYSIS = "community_analysis"
    MATURITY_ANALYSIS = "maturity_analysis"
    SCORE_CALCULATION = "score_calculation"
    RANKING = "ranking"
    AI_RECOMMENDATION = "ai_recommendation"
    AI_EXPLANATION = "ai_explanation"
    REPORT_GENERATION = "report_generation"
    SESSION_SUMMARY = "session_summary"
    AUTO_COMMIT = "auto_commit"


@dataclass
class StepRecord:
    """Record of a single execution step."""
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "pending"
    duration_seconds: Optional[float] = None
    error_msg: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data


@dataclass
class SessionSummary:
    """Summary of an analysis session with insights and learnings."""
    session_id: str
    query: str
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float
    status: SessionStatus
    steps_completed: int
    steps_total: int
    success_rate: float
    projects_analyzed: int
    projects_filtered: int
    
    # Key metrics
    average_code_score: Optional[float] = None
    average_community_score: Optional[float] = None
    average_maturity_score: Optional[float] = None
    average_total_score: Optional[float] = None
    
    # Success/failure experiences
    successful_patterns: List[str] = field(default_factory=list)
    failure_causes: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # Recommendations for next runs
    next_run_recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        data["end_time"] = self.end_time.isoformat()
        data["status"] = self.status.value
        return data
    
    def to_markdown(self) -> str:
        """Generate markdown report of session summary."""
        success_rate_pct = self.success_rate * 100
        return f"""# Analysis Session Summary

## Basic Information
- **Session ID**: `{self.session_id}`
- **Query**: {self.query}
- **Duration**: {self.total_duration_seconds:.1f} seconds
- **Status**: {self.status.value}
- **Steps Completed**: {self.steps_completed}/{self.steps_total} ({success_rate_pct:.1f}%)

## Analysis Results
- **Projects Found**: {self.projects_filtered}
- **Projects Analyzed**: {self.projects_analyzed}
- **Average Scores**:
  - Code Quality: {self.average_code_score or 'N/A':.2f}
  - Community Activity: {self.average_community_score or 'N/A':.2f}
  - Project Maturity: {self.average_maturity_score or 'N/A':.2f}
  - Total Score: {self.average_total_score or 'N/A':.2f}

## Learnings and Insights

### Successful Patterns
{self._format_list(self.successful_patterns)}

### Failure Causes
{self._format_list(self.failure_causes)}

### Improvement Suggestions
{self._format_list(self.improvement_suggestions)}

## Recommendations for Next Run
{self._format_list(self.next_run_recommendations)}
"""
    
    def _format_list(self, items: List[str]) -> str:
        """Format list items for markdown."""
        if not items:
            return "None"
        return "\n".join(f"- {item}" for item in items)


class SessionManager:
    """Manages analysis sessions with auto-commit and experience tracking."""
    
    def __init__(self, session_id: Optional[str] = None, base_dir: str = "./data/sessions"):
        """Initialize session manager.
        
        Args:
            session_id: Unique session ID (generated if None).
            base_dir: Base directory for session files.
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.base_dir = Path(base_dir)
        self.session_dir = self.base_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Session tracking
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.query: Optional[str] = None
        
        # Step tracking
        self.steps: List[StepRecord] = []
        self.current_step: Optional[StepRecord] = None
        
        # Session data
        self.summary: Optional[SessionSummary] = None
        
        # Initialize paths
        self.steps_file = self.session_dir / "steps.json"
        self.summary_file = self.session_dir / "summary.json"
        self.summary_md_file = self.session_dir / "summary.md"
        self.log_file = self.session_dir / "session.log"
        
        logger.info(f"Initialized session manager: {self.session_id}")
    
    def initialize_session(self, query: str) -> None:
        """Initialize new analysis session.
        
        Args:
            query: User search query.
        """
        self.start_time = datetime.now()
        self.query = query
        logger.info(f"Started session for query: {query}")
    
    def start_step(self, step_name: StepName, input_data: Optional[Dict[str, Any]] = None) -> None:
        """Start tracking a new execution step.
        
        Args:
            step_name: Name of the step.
            input_data: Input data for the step.
        """
        if self.current_step is not None:
            self.end_step(status="completed")
        
        self.current_step = StepRecord(
            name=step_name.value,
            start_time=datetime.now(),
            input_data=input_data
        )
        self.steps.append(self.current_step)
        logger.info(f"Started step: {step_name.value}")
    
    def end_step(self, 
                 status: str = "completed", 
                 error_msg: Optional[str] = None,
                 output_data: Optional[Dict[str, Any]] = None) -> None:
        """End the currently active step.
        
        Args:
            status: Step status (completed, failed, etc.)
            error_msg: Error message if step failed.
            output_data: Output data from the step.
        """
        if self.current_step is None:
            logger.warning("Attempted to end step but no step is active")
            return
        
        end_time = datetime.now()
        duration = (end_time - self.current_step.start_time).total_seconds()
        
        self.current_step.end_time = end_time
        self.current_step.status = status
        self.current_step.duration_seconds = duration
        self.current_step.error_msg = error_msg
        self.current_step.output_data = output_data
        
        # Persist step data
        self._persist_steps()
        
        log_msg = f"Ended step: {self.current_step.name} [{status}, {duration:.1f}s]"
        if error_msg:
            log_msg += f" - Error: {error_msg}"
        logger.info(log_msg)
        
        self.current_step = None
    
    def finalize_session(self, 
                        status: SessionStatus,
                        projects_analyzed: int,
                        projects_filtered: int,
                        average_scores: Optional[Dict[str, float]] = None,
                        experiences: Optional[Dict[str, List[str]]] = None) -> SessionSummary:
        """Finalize the session and generate summary.
        
        Args:
            status: Final session status.
            projects_analyzed: Number of projects analyzed.
            projects_filtered: Number of projects filtered.
            average_scores: Average scores for analyzed projects.
            experiences: Success/failure experiences for future improvements.
            
        Returns:
            The generated session summary.
        """
        if self.start_time is None:
            raise ValueError("Session not initialized")
        
        self.end_time = datetime.now()
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        steps_total = len(self.steps)
        steps_completed = sum(1 for s in self.steps if s.status == "completed")
        success_rate = steps_completed / steps_total if steps_total > 0 else 0.0
        
        # Generate summary
        self.summary = SessionSummary(
            session_id=self.session_id,
            query=self.query or "Unknown",
            start_time=self.start_time,
            end_time=self.end_time,
            total_duration_seconds=total_duration,
            status=status,
            steps_completed=steps_completed,
            steps_total=steps_total,
            success_rate=success_rate,
            projects_analyzed=projects_analyzed,
            projects_filtered=projects_filtered,
            average_code_score=average_scores.get("code") if average_scores else None,
            average_community_score=average_scores.get("community") if average_scores else None,
            average_maturity_score=average_scores.get("maturity") if average_scores else None,
            average_total_score=average_scores.get("total") if average_scores else None,
            successful_patterns=experiences.get("successful_patterns", []) if experiences else [],
            failure_causes=experiences.get("failure_causes", []) if experiences else [],
            improvement_suggestions=experiences.get("improvement_suggestions", []) if experiences else [],
            next_run_recommendations=self._generate_recommendations()
        )
        
        # Persist summary
        self._persist_summary()
        
        logger.info(f"Finalized session: {self.session_id}, status: {status.value}")
        return self.summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for next run based on session data."""
        recommendations = []
        
        # Analyze step durations
        slow_steps = [s for s in self.steps if s.duration_seconds and s.duration_seconds > 30]
        failed_steps = [s for s in self.steps if s.status == "failed"]
        
        if slow_steps:
            recommendations.append(
                f"Optimize slow steps: {', '.join(s.name for s in slow_steps)}"
            )
        
        if failed_steps:
            recommendations.append(
                f"Review and fix failed steps: {', '.join(s.name for s in failed_steps)}"
            )
        
        # General recommendations
        recommendations.extend([
            "Review AI provider configuration if response quality is low",
            "Consider increasing project limit for broad queries",
            "Check network connectivity for GitHub API and AI calls",
            "Verify downloaded code archives are being cleaned up properly"
        ])
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _persist_steps(self) -> None:
        """Persist step records to file."""
        steps_data = [step.to_dict() for step in self.steps]
        with open(self.steps_file, 'w', encoding='utf-8') as f:
            json.dump(steps_data, f, indent=2, ensure_ascii=False)
    
    def _persist_summary(self) -> None:
        """Persist session summary to JSON and Markdown files."""
        if self.summary is None:
            return
        
        # Save as JSON
        summary_dict = self.summary.to_dict()
        with open(self.summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_dict, f, indent=2, ensure_ascii=False)
        
        # Save as Markdown
        md_content = self.summary.to_markdown()
        with open(self.summary_md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Persisted session summary: {self.session_id}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get basic session information."""
        return {
            "session_id": self.session_id,
            "query": self.query,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "steps_completed": len(self.steps),
            "current_step": self.current_step.name if self.current_step else None,
            "summary_available": self.summary is not None
        }
    
    async def cleanup(self) -> None:
        """Clean up temporary session resources."""
        if self.current_step:
            self.end_step(status="cancelled")
        
        logger.info(f"Cleaned up session: {self.session_id}")


# Utilities for experience tracking
def extract_experiences_from_session(session_summary: SessionSummary) -> Dict[str, List[str]]:
    """Extract learning experiences from session summary.
    
    This function analyzes the session results to extract patterns and learnings
    that can be used to improve future runs.
    """
    experiences = {
        "successful_patterns": [],
        "failure_causes": [],
        "improvement_suggestions": []
    }
    
    # Extract from summary
    if session_summary.average_total_score and session_summary.average_total_score > 7.0:
        experiences["successful_patterns"].append(
            f"High average score ({session_summary.average_total_score:.1f}) achieved for query: {session_summary.query[:50]}..."
        )
    
    # Add generic improvement suggestions
    if session_summary.success_rate < 0.9:
        experiences["improvement_suggestions"].append(
            f"Improve step success rate (current: {session_summary.success_rate:.1%})"
        )
    
    return experiences