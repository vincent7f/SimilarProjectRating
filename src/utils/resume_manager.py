#!/usr/bin/env python3
"""
Resume Manager - Task recovery and session resumption for analysis pipeline.

Provides functionality to save task checkpoints, track execution state,
and resume from the last successful step after interruption or failure.

恢复管理器 - 分析流水线的任务恢复和会话恢复功能.
提供保存任务检查点,跟踪执行状态以及在中断或失败后从最后一个成功步骤恢复的功能.
"""

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.utils.logger import get_logger
from src.models.session import AnalysisSession, SessionStatus
from src.models.repository import Repository
from src.models.analysis import AnalysisResult

logger = get_logger(__name__)


class TaskType(str, Enum):
    """Type of task for parallel execution configuration."""
    AI_DEPENDENT = "ai_dependent"      # Tasks that depend on AI/LLM calls
    NON_AI = "non_ai"                 # Tasks that don't require AI
    MIXED = "mixed"                    # Tasks with both AI and non-AI parts


class TaskStatus(str, Enum):
    """Execution status of a task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class TaskCheckpoint:
    """Checkpoint for a single task in the pipeline."""
    
    task_id: str
    task_name: str
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Input/output data serialized as JSON
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    # Error information
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # Dependencies and relationships
    dependencies: List[str] = field(default_factory=list)
    result_key: Optional[str] = None  # Key to store result in session state
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        
        # Handle datetime fields
        data["start_time"] = self.start_time.isoformat() if self.start_time else None
        data["end_time"] = self.end_time.isoformat() if self.end_time else None
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        data["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        
        # Handle enum fields
        data["task_type"] = self.task_type.value
        data["status"] = self.status.value
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskCheckpoint":
        """Create from dictionary."""
        # Convert string values back to enums
        if "task_type" in data and isinstance(data["task_type"], str):
            data["task_type"] = TaskType(data["task_type"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])
        
        # Convert ISO strings back to datetime
        for time_field in ["start_time", "end_time", "created_at", "updated_at"]:
            if time_field in data and isinstance(data[time_field], str):
                data[time_field] = datetime.fromisoformat(data[time_field])
            elif time_field in data and data[time_field] is None:
                data[time_field] = None
        
        return cls(**data)


@dataclass
class ResumeState:
    """Complete state for session resumption."""
    
    session_id: str
    query: str
    session_data: Dict[str, Any] = field(default_factory=dict)
    tasks: List[TaskCheckpoint] = field(default_factory=list)
    current_task_index: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get_next_pending_task(self) -> Optional[TaskCheckpoint]:
        """Get the next pending task."""
        for task in self.tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.FAILED]:
                return task
        return None
    
    def get_completed_tasks(self) -> List[TaskCheckpoint]:
        """Get all completed tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.COMPLETED]
    
    def get_failed_tasks(self) -> List[TaskCheckpoint]:
        """Get all failed tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.FAILED]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["tasks"] = [t.to_dict() for t in self.tasks]
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeState":
        """Create from dictionary."""
        # Load tasks
        tasks_data = data.get("tasks", [])
        tasks = [TaskCheckpoint.from_dict(t) for t in tasks_data]
        data["tasks"] = tasks
        
        # Convert datetime fields
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        return cls(**data)


class ResumeManager:
    """Manages task checkpoints and session resumption."""
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        checkpoint_dir: str = "./data/checkpoints",
        max_concurrent_non_ai: int = 5,
        max_concurrent_ai: int = 1
    ) -> None:
        """Initialize resume manager.
        
        Args:
            session_id: Unique session ID (generated if None).
            checkpoint_dir: Directory for checkpoint files.
            max_concurrent_non_ai: Maximum concurrent non-AI tasks.
            max_concurrent_ai: Maximum concurrent AI-dependent tasks.
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_file = self.checkpoint_dir / f"{self.session_id}.json"
        self.state: Optional[ResumeState] = None
        
        # Parallel execution settings
        self.max_concurrent_non_ai = max_concurrent_non_ai
        self.max_concurrent_ai = max_concurrent_ai
        
        # Semaphores for concurrency control
        self.ai_semaphore = asyncio.Semaphore(max_concurrent_ai)
        self.non_ai_semaphore = asyncio.Semaphore(max_concurrent_non_ai)
        
        logger.info(f"Initialized resume manager: {self.session_id}")
        logger.info(f"AI tasks concurrency: {max_concurrent_ai}, Non-AI tasks concurrency: {max_concurrent_non_ai}")
    
    def initialize_new_session(
        self,
        query: str,
        pipeline_tasks: Optional[List[Dict[str, Any]]] = None
    ) -> ResumeState:
        """Initialize a new session with task definitions.
        
        Args:
            query: User search query.
            pipeline_tasks: List of task definitions for the pipeline.
            
        Returns:
            Initialized resume state.
        """
        default_tasks = self._create_default_pipeline_tasks(query)
        tasks_data = pipeline_tasks or default_tasks
        
        tasks = []
        for task_def in tasks_data:
            task = TaskCheckpoint(
                task_id=task_def["id"],
                task_name=task_def["name"],
                task_type=TaskType(task_def.get("type", "non_ai")),
                dependencies=task_def.get("dependencies", []),
                result_key=task_def.get("result_key")
            )
            tasks.append(task)
        
        self.state = ResumeState(
            session_id=self.session_id,
            query=query,
            tasks=tasks
        )
        
        self._save_state()
        logger.info(f"Initialized new session: {self.session_id} with {len(tasks)} tasks")
        return self.state
    
    def load_resume_state(self) -> Optional[ResumeState]:
        """Load resume state from checkpoint file.
        
        Returns:
            ResumeState if checkpoint exists, None otherwise.
        """
        if not self.checkpoint_file.exists():
            logger.warning(f"No checkpoint found for session: {self.session_id}")
            return None
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.state = ResumeState.from_dict(data)
            logger.info(f"Loaded resume state for session: {self.session_id}")
            logger.info(f"Progress: {self.get_completion_percentage():.1f}% complete")
            return self.state
        except Exception as e:
            logger.error(f"Failed to load resume state: {e}")
            return None
    
    def can_resume(self) -> bool:
        """Check if session can be resumed."""
        if not self.state:
            return False
        
        # Check if there are pending or failed tasks
        pending = any(t.status in [TaskStatus.PENDING, TaskStatus.FAILED] 
                     for t in self.state.tasks)
        completed = any(t.status == TaskStatus.COMPLETED for t in self.state.tasks)
        
        return pending and completed
    
    def get_resume_point(self) -> Tuple[int, List[str]]:
        """Get the resume point (next task index and completed tasks).
        
        Returns:
            Tuple of (next_task_index, list_of_completed_task_names)
        """
        if not self.state:
            return 0, []
        
        completed_tasks = [t.task_name for t in self.state.tasks 
                          if t.status == TaskStatus.COMPLETED]
        next_task = self.state.get_next_pending_task()
        next_index = self.state.tasks.index(next_task) if next_task else len(self.state.tasks)
        
        return next_index, completed_tasks
    
    def get_completion_percentage(self) -> float:
        """Get completion percentage of all tasks."""
        if not self.state or not self.state.tasks:
            return 0.0
        
        completed = len([t for t in self.state.tasks 
                        if t.status == TaskStatus.COMPLETED])
        total = len(self.state.tasks)
        
        return (completed / total) * 100 if total > 0 else 0.0
    
    async def execute_task(
        self,
        task_id: str,
        task_func: callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute a task with checkpointing and concurrency control.
        
        Args:
            task_id: ID of the task to execute.
            task_func: Async function to execute.
            *args: Arguments for task_func.
            **kwargs: Keyword arguments for task_func.
            
        Returns:
            Result of task execution.
        """
        if not self.state:
            raise ValueError("Resume state not initialized")
        
        task = next((t for t in self.state.tasks if t.task_id == task_id), None)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # Check dependencies
        for dep_id in task.dependencies:
            dep_task = next((t for t in self.state.tasks if t.task_id == dep_id), None)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                raise ValueError(f"Dependency not satisfied: {dep_id}")
        
        # Update task status
        task.start_time = datetime.now()
        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now()
        self._save_state()
        
        try:
            # Apply concurrency control based on task type
            if task.task_type == TaskType.AI_DEPENDENT:
                async with self.ai_semaphore:
                    logger.info(f"Executing AI-dependent task: {task.task_name} (concurrency limit: {self.max_concurrent_ai})")
                    result = await task_func(*args, **kwargs)
            else:
                async with self.non_ai_semaphore:
                    logger.info(f"Executing non-AI task: {task.task_name} (concurrency limit: {self.max_concurrent_non_ai})")
                    result = await task_func(*args, **kwargs)
            
            # Record successful completion
            task.end_time = datetime.now()
            task.duration_seconds = (task.end_time - task.start_time).total_seconds()
            task.status = TaskStatus.COMPLETED
            
            # Store result if requested
            if task.result_key:
                if not self.state.session_data:
                    self.state.session_data = {}
                self.state.session_data[task.result_key] = result
            
            task.output_data = {
                "result_type": type(result).__name__,
                "success": True
            }
            
            logger.info(f"Completed task: {task.task_name} in {task.duration_seconds:.1f}s")
            
        except Exception as e:
            # Record failure
            task.end_time = datetime.now()
            task.duration_seconds = (task.end_time - task.start_time).total_seconds()
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            
            import traceback
            task.error_traceback = traceback.format_exc()
            task.output_data = {
                "error": str(e),
                "success": False
            }
            
            logger.error(f"Task failed: {task.task_name} - {e}")
            raise
        
        finally:
            task.updated_at = datetime.now()
            self._save_state()
        
        return result
    
    async def execute_pipeline(self, task_func_map: Dict[str, callable]) -> Dict[str, Any]:
        """Execute the entire pipeline with checkpointing.
        
        Args:
            task_func_map: Dictionary mapping task_id -> async function.
            
        Returns:
            Dictionary of all task results.
        """
        results = {}
        
        for task in self.state.tasks:
            if task.status == TaskStatus.COMPLETED:
                logger.info(f"Skipping already completed task: {task.task_name}")
                continue
            
            if task.status == TaskStatus.FAILED:
                logger.info(f"Retrying failed task: {task.task_name}")
            
            if task.task_id not in task_func_map:
                logger.warning(f"No function found for task: {task.task_id}")
                task.status = TaskStatus.SKIPPED
                self._save_state()
                continue
            
            try:
                result = await self.execute_task(
                    task.task_id,
                    task_func_map[task.task_id]
                )
                results[task.task_id] = result
            except Exception as e:
                logger.error(f"Pipeline execution stopped due to task failure: {task.task_name}")
                break
        
        return results
    
    def _create_default_pipeline_tasks(self, query: str) -> List[Dict[str, Any]]:
        """Create default task definitions for the analysis pipeline.
        
        Returns:
            List of task definitions.
        """
        return [
            {
                "id": "keyword_generation",
                "name": "Keyword Generation",
                "type": "ai_dependent",
                "dependencies": [],
                "result_key": "keyword_groups"
            },
            {
                "id": "github_search",
                "name": "GitHub Search",
                "type": "non_ai",
                "dependencies": ["keyword_generation"],
                "result_key": "candidate_projects"
            },
            {
                "id": "project_filtering",
                "name": "Project Filtering",
                "type": "ai_dependent",
                "dependencies": ["github_search"],
                "result_key": "filtered_projects"
            },
            {
                "id": "code_analysis",
                "name": "Code Analysis",
                "type": "non_ai",
                "dependencies": ["project_filtering"],
                "result_key": "analysis_results_partial"
            },
            {
                "id": "community_analysis",
                "name": "Community Analysis",
                "type": "non_ai",  # Mostly API calls, limited AI
                "dependencies": ["project_filtering"],
                "result_key": "community_results"
            },
            {
                "id": "maturity_analysis",
                "name": "Maturity Analysis",
                "type": "non_ai",
                "dependencies": ["project_filtering"],
                "result_key": "maturity_results"
            },
            {
                "id": "score_calculation",
                "name": "Score Calculation",
                "type": "non_ai",
                "dependencies": ["code_analysis", "community_analysis", "maturity_analysis"],
                "result_key": "scored_projects"
            },
            {
                "id": "ranking",
                "name": "Ranking",
                "type": "non_ai",
                "dependencies": ["score_calculation"],
                "result_key": "ranked_projects"
            },
            {
                "id": "ai_recommendation",
                "name": "AI Recommendation",
                "type": "ai_dependent",
                "dependencies": ["ranking"],
                "result_key": "recommendations"
            },
            {
                "id": "ai_explanation",
                "name": "AI Explanation",
                "type": "ai_dependent",
                "dependencies": ["ai_recommendation"],
                "result_key": "explanation"
            },
            {
                "id": "report_generation",
                "name": "Report Generation",
                "type": "non_ai",
                "dependencies": ["ai_explanation"],
                "result_key": "report_path"
            }
        ]
    
    def _save_state(self) -> None:
        """Save resume state to checkpoint file."""
        if not self.state:
            return
        
        try:
            state_dict = self.state.to_dict()
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved checkpoint for session: {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def cleanup(self) -> None:
        """Clean up checkpoint files."""
        if self.checkpoint_file.exists():
            try:
                self.checkpoint_file.unlink()
                logger.info(f"Cleaned up checkpoint: {self.session_id}")
            except Exception as e:
                logger.error(f"Failed to clean up checkpoint: {e}")
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get all session data."""
        return self.state.session_data if self.state else {}


def create_resume_manager_from_session(
    session_id: str,
    checkpoint_dir: str = "./data/checkpoints"
) -> Optional[ResumeManager]:
    """Create resume manager from existing session ID.
    
    Args:
        session_id: Existing session ID.
        checkpoint_dir: Checkpoint directory.
        
    Returns:
        ResumeManager if session exists, None otherwise.
    """
    manager = ResumeManager(session_id, checkpoint_dir)
    state = manager.load_resume_state()
    
    if state:
        return manager
    return None