"""
Analysis Result Domain Models.

Data classes representing analysis results, scoring outputs,
and ranked project comparisons produced by the analysis pipeline.

分析结果领域模型。
表示分析流水线产生的分析结果、评分输出
和排名项目比较的dataclass。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.models.common import RankTier
from src.models.repository import Repository
from src.models.metrics import (
    CodeQualityMetrics,
    CommunityMetrics,
    MaturityMetrics,
)


@dataclass
class AnalysisResult:
    """Complete analysis result for a single project.

    Aggregates all analysis dimensions (code quality, community, maturity)
    along with raw scores and intermediate data into one unified record.

    单个项目的完整分析结果。
聚合所有分析维度（代码质量、社区、成熟度）
以及原始分数和中间数据到一个统一记录中。

    Attributes:
        project: The analyzed repository's metadata.
                 被分析仓库的元数据。
        code_metrics: Code quality assessment results.
                      代码质量评估结果。
        community_metrics: Community activity and health assessment results.
                          社区活动和健康度评估结果。
        maturity_metrics: Production-readiness and governance assessment results.
                         生产就绪度和治理评估结果。
        functionality_score: Feature completeness and capability score (0.0-100.0).
                            功能完整性能力评分（0.0-100.0）。
        reputation_score: External recognition and trust score (0.0-100.0).
                         外部认可和信任评分（0.0-100.0）。
        sustainability_score: Long-term maintenance viability score (0.0-100.0).
                            长期维护可行性评分（0.0-100.0）。
        errors: List of error messages encountered during analysis.
                分析过程中遇到的错误消息列表。
        warnings: List of warning messages from the analysis process.
                  分析过程中的警告消息列表。
        analysis_duration_ms: Time taken to complete analysis (milliseconds).
                             完成分析所用的时间（毫秒）。
    """
    project: Repository = field(default_factory=Repository)
    code_metrics: CodeQualityMetrics = field(default_factory=CodeQualityMetrics)
    community_metrics: CommunityMetrics = field(default_factory=CommunityMetrics)
    maturity_metrics: MaturityMetrics = field(default_factory=MaturityMetrics)
    functionality_score: float = 0.0
    reputation_score: float = 0.0
    sustainability_score: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    analysis_duration_ms: int = 0


@dataclass
class ProjectScore:
    """Multi-dimensional scoring output for a single analyzed project.

    Contains both raw per-dimension scores and normalized (comparable) scores
    ready for ranking across different projects. Includes the final comprehensive
    weighted sum score.

    单个分析项目的多维评分输出。
包含原始每维度分数和标准化（可比较）分数，
用于跨不同项目的排名。包含最终的综合加权总分。

    Attributes:
        project_full_name: Repository identifier ('owner/repo').
                           仓库标识符（'owner/repo'）。
        dimensions: Raw scores for each dimension before normalization.
                   标准化前每个维度的原始分数。
        normalized: Min-max normalized scores (0.0-1.0) for fair comparison.
                   用于公平比较的Min-max标准化分数（0.0-1.0）。
        comprehensive: Final weighted comprehensive score (0.0-100.0).
                      最终加权综合分数（0.0-100.0）。
        rank: Position in the sorted ranking (1 = best).
              排序列表中的位置（1=最佳）。
        confidence: Scoring confidence indicator based on data availability (0.0-1.0).
                   基于数据可用性的评分置信度指示器（0.0-1.0）。
    """
    project_full_name: str = ""
    dimensions: Dict[str, float] = field(default_factory=dict)
    normalized: Dict[str, float] = field(default_factory=dict)
    comprehensive: float = 0.0
    rank: int = 0
    confidence: float = 1.0

    def get_dimension(self, name: str) -> float:
        """Get normalized score for a specific dimension.

        获取特定维度的标准化分数。

        Args:
            name: Dimension identifier (e.g., 'code_quality').
                  维度标识符（例如'code_quality'）。

        Returns:
            Normalized score (0.0-1.0), or 0.0 if dimension not found.
            标准化分数（0.0-1.0），如维度不存在则返回0.0。
        """
        return self.normalized.get(name, 0.0)


@dataclass
class RankedProject:
    """A project positioned within a ranked comparison list.

    Extends basic scored project with tier classification, highlight tags,
    concern flags, and AI-generated recommendation context.

    排名比较列表中的一个定位项目。
扩展基本评分项目，增加分级分类、高亮标签、关注标志
和AI生成的推荐上下文。

    Attributes:
        project: The repository being ranked.
                 被排名的仓库。
        score: Complete scoring data for this project.
               此项目的完整评分数据。
        rank: Position in overall ranking (1 = best).
              总体排名中的位置（1=最佳）。
        tier: S/A/B/C/D tier classification.
              S/A/B/C/D等级分类。
        highlights: Positive highlight tags (e.g., 'Excellent test coverage', 'Active community').
                   正面高亮标签（例如'Excellent test coverage'、'Active community'）。
        concerns: Concern or warning tags (e.g., 'No license', 'Stale development').
                 关注或警告标签（例如'No license'、'Stale development'）。
        recommendation_reason: AI-generated explanation for why this project is recommended.
                             AI生成的推荐此项目的原因解释。
        use_cases: Recommended use cases for this project.
                  此项目的推荐使用场景。
    """
    project: Repository = field(default_factory=Repository)
    score: ProjectScore = field(default_factory=ProjectScore)
    rank: int = 0
    tier: RankTier = RankTier.D
    highlights: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    recommendation_reason: str = ""
    use_cases: List[str] = field(default_factory=list)

    @property
    def tier_label(self) -> str:
        """Return human-readable tier label with emoji.

        返回带emoji的可读等级标签。

        Returns:
            Tier label string like 'S - Exceptional' or 'C - Acceptable'.
            等级标签字符串，如'S - Exceptional'或'C - Acceptable'。
        """
        labels = {
            RankTier.S: "S - Exceptional",
            RankTier.A: "A - Excellent",
            RankTier.B: "B - Good",
            RankTier.C: "C - Acceptable",
            RankTier.D: "D - Low",
        }
        return labels.get(self.tier, f"{self.tier.value} - Unknown")


@dataclass
class ComparisonTable:
    """Cross-project comparison table data for report generation.

    Prepares structured data for generating side-by-side comparison
    tables in output reports showing key metrics across all projects.

    用于报告生成的跨项目比较表格数据。
准备结构化数据以在输出报告中生成并排的比较表格，
显示所有项目的关键指标。

    Attributes:
        headers: Column header names (first column is usually metric name).
                 列标题名称（第一列通常是指标名称）。
        rows: List of rows where each row is a dictionary mapping header->value.
              行列表，其中每行是映射header->value的字典。
        project_names: Ordered list of project names matching column order.
                      匹配列顺序的项目名称有序列表。
    """
    headers: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    project_names: List[str] = field(default_factory=list)
