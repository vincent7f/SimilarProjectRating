"""
Session Management Domain Models.

Data classes for tracking analysis sessions, execution logs,
run summaries, and accumulated experience/knowledge.

会话管理领域模型。
用于跟踪分析会话、执行日志、运行总结
和累积经验/知识的dataclass。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionStatus(str, Enum):
    """Execution status of an analysis session.

    分析会话的执行状态。

    Attributes:
        INITIALIZED: Session created but not yet started.
                     会话已创建但尚未开始。
        RUNNING: Analysis pipeline is actively executing.
                 分析流水线正在积极执行。
        COMPLETED: All stages finished successfully.
                   所有阶段成功完成。
        FAILED: Execution terminated due to an error.
                执行因错误而终止。
        PARTIALLY_COMPLETED: Some stages succeeded but others failed.
                           某些阶段成功但其他阶段失败。
    """
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


@dataclass
class LogEntry:
    """Structured log entry for detailed operation tracking.

    Each significant operation during analysis produces a LogEntry
    capturing input parameters, output results, timing, and status.

    详细操作跟踪的结构化日志条目。
分析期间的每个重要操作都会生成一个LogEntry，
捕获输入参数、输出结果、时间和状态。

    Attributes:
        timestamp: When the operation occurred (ISO 8601 format).
                  操作发生的时间（ISO 8601格式）。
        level: Severity level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
              严重级别（'DEBUG'、'INFO'、'WARNING'、'ERROR'）。
        module: Source module that generated this entry ('search', 'analysis', etc.).
               生成此条目的源模块（'search'、'analysis'等）。
        operation: Specific operation name (e.g., 'github_search', 'code_analysis').
                  具体操作名称（例如'github_search'、'code_analysis'）。
        params: Input parameters passed to the operation.
                传递给操作的输入参数。
        results: Output results from the operation.
                 操作的输出结果。
        duration_ms: Operation execution time in milliseconds.
                    操作执行时间（毫秒）。
        success: Whether the operation completed without errors.
                操作是否无错误完成。
        error: Error message if success is False, else None.
               如果success为False的错误消息，否则为None。
        metadata: Additional contextual key-value pairs.
                  额外的上下文键值对。
    """
    timestamp: str = ""
    level: str = "INFO"
    module: str = ""
    operation: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dictionary for serialization.

        转换为普通字典以便序列化。

        Returns:
            Dictionary representation of this log entry.
             此日志条目的字典表示。
        }
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "module": self.module,
            "operation": self.operation,
            "params": self.params,
            "results": self.results,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class ExperienceEntry:
    """Accumulated experience item from past runs.

    Captures lessons learned (both successes and failures) from previous
    analysis sessions to inform future execution improvements.

    过往运行累积的经验条目。
捕获先前分析会话中学到的经验教训（成功和失败），
以指导未来的执行改进。

    Attributes:
        category: Type of experience ('success', 'failure', 'optimization', 'warning').
                  经验类型（'success'、'failure'、'optimization'、'warning'）。
        summary: Brief description of the lesson learned.
                 所学经验的简要描述。
        context: The situation or condition under which this was learned.
                学习此经验的情境或条件。
        suggestion: Actionable recommendation derived from this experience.
                   从此经验得出的可行建议。
        session_id: ID of the session where this originated.
                  来源会话的ID。
        recorded_at: When this experience was recorded.
                    此经验被记录的时间。
    """
    category: str = ""
    summary: str = ""
    context: str = ""
    suggestion: str = ""
    session_id: str = ""
    recorded_at: Optional[datetime] = None


@dataclass
class SessionSummary:
    """End-of-run summary report for an analysis session.

    Generated after each complete (or partial) analysis run, summarizing
    what happened, what worked, what failed, and recommendations for improvement.

    分析会话的运行结束总结报告。
在每次完整（或部分）分析运行后生成，总结发生了什么、
什么有效、什么失败了以及改进建议。

    Attributes:
        session_id: Unique identifier for this session.
                   此会话的唯一标识符。
        query: Original user search query.
               原始用户搜索查询。
        start_time: When the session began.
                  会话开始时间。
        end_time: When the session concluded (or failed).
                 会话结束（或失败）时间。
        status: Final status of the session.
               会话的最终状态。
        total_projects_found: Number of candidate projects discovered.
                            发现的候选项目总数。
        projects_analyzed: Number of projects fully analyzed.
                          完全分析的项目数量。
        projects_filtered_out: Number of projects filtered as irrelevant.
                             被过滤为不相关的项目数量。
        total_duration_seconds: Wall-clock duration of the entire session.
                              整个会话的挂钟持续时间。
        average_analysis_time: Average time spent analyzing each project.
                             分析每个项目所用的平均时间。
        successes: List of successful outcomes worth noting.
                  值得注意的成功结果列表。
        failures: List of failures encountered with causes and workarounds.
                 遇到的故障列表及原因和解决方案。
        optimization_suggestions: Recommendations for improving future runs.
                                改进未来运行的建议。
        experiences: New experience entries to persist for future reference.
                    要保留供未来参考的新经验条目。
        next_run_recommendations: Specific suggestions for the next execution.
                                下次执行的具体建议。
    """
    session_id: str = ""
    query: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: SessionStatus = SessionStatus.INITIALIZED
    total_projects_found: int = 0
    projects_analyzed: int = 0
    projects_filtered_out: int = 0
    total_duration_seconds: float = 0.0
    average_analysis_time: float = 0.0
    successes: List[str] = field(default_factory=list)
    failures: List[Dict[str, str]] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    experiences: List[ExperienceEntry] = field(default_factory=list)
    next_run_recommendations: List[str] = field(default_factory=list)


@dataclass
class AnalysisSession:
    """Top-level container for a complete analysis execution session.

    Manages the lifecycle of a single end-to-end analysis run from query
    input through report output, including all intermediate state and logs.

    完整分析执行会话的顶级容器。
管理单次端到端分析运行的整个生命周期，
从查询输入到报告输出，包括所有中间状态和日志。

    Attributes:
        session_id: Unique UUID-style identifier for this session.
                   此会话的唯一UUID样式标识符。
        query: User's original natural language search query.
               用户原始的自然语言搜索查询。
        start_time: Session start timestamp.
                  会话开始时间戳。
        end_time: Session completion/failure timestamp.
                 会话完成/失败时间戳。
        status: Current execution status.
               当前执行状态。
        config_snapshot: Configuration settings used for this run (for reproducibility).
                       此运行使用的配置设置（用于可重现性）。
        keyword_groups: Search keyword groups generated by AI.
                       由AI生成的搜索关键词组。
        candidate_projects: All candidate repositories found before filtering.
                          过滤前找到的所有候选仓库。
        filtered_projects: Repositories after relevance filtering.
                         相关性过滤后的仓库。
        analysis_results: Completed analysis results for each project.
                        每个项目的已完成分析结果。
        ranked_results: Final ranked and scored project list.
                       最终排名和评分的项目列表。
        logs: Chronological log entries for all operations.
              所有操作按时间顺序排列的日志条目。
        summary: End-of-run summary (generated after completion).
               运行结束后总结（完成后生成）。
        report_path: Path to the generated Markdown report file.
                    生成的Markdown报告文件路径。
    """
    session_id: str = ""
    query: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: SessionStatus = SessionStatus.INITIALIZED
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    keyword_groups: List[Any] = field(default_factory=list)
    candidate_projects: List[Any] = field(default_factory=list)
    filtered_projects: List[Any] = field(default_factory=list)
    analysis_results: List[Any] = field(default_factory=list)
    ranked_results: List[Any] = field(default_factory=list)
    logs: List[LogEntry] = field(default_factory=list)
    summary: Optional[SessionSummary] = None
    report_path: Optional[str] = None
