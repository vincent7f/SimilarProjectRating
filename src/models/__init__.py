"""
Models Package - Domain data model definitions.

Contains all dataclasses and type definitions representing the core domain
entities: repositories, metrics, analysis results, sessions, and search data.

模型包 - 领域数据模型定义。
包含表示所有核心领域实体的dataclass和类型定义：
仓库、指标、分析结果、会话和搜索数据。
"""

from src.models.repository import Repository, Release, Asset, LicenseInfo
from src.models.metrics import (
    CodeQualityMetrics,
    CommunityMetrics,
    MaturityMetrics,
)
from src.models.analysis import (
    AnalysisResult,
    ProjectScore,
    RankedProject,
)
from src.models.session import AnalysisSession, SessionSummary, LogEntry
from src.models.search import KeywordGroup, SearchQuery, FilterResult

__all__ = [
    # Repository models / 仓库模型
    "Repository", "Release", "Asset", "LicenseInfo",
    # Metrics / 指标
    "CodeQualityMetrics", "CommunityMetrics", "MaturityMetrics",
    # Analysis / 分析
    "AnalysisResult", "ProjectScore", "RankedProject",
    # Session / 会话
    "AnalysisSession", "SessionSummary", "LogEntry",
    # Search / 搜索
    "KeywordGroup", "SearchQuery", "FilterResult",
]
