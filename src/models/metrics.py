"""
Analysis Metrics Domain Models.

Data classes representing multi-dimensional analysis metrics:
code quality, community activity, and project maturity assessments.

分析指标领域模型.
表示多维度分析指标的dataclass:
代码质量,社区活动和项目成熟度评估.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ===========================================================================
# Code Quality Metrics / 代码质量指标
# ===========================================================================

@dataclass
class CodeQualityMetrics:
    """Comprehensive code quality assessment metrics.

    Evaluates a project's codebase across multiple quality dimensions
    including style compliance, test coverage, dependency management,
    documentation completeness, and architectural clarity.

    综合代码质量评估指标.
在多个质量维度上评估项目的代码库,包括风格合规性,测试覆盖率,
依赖管理,文档完整性和架构清晰度.

    Attributes:
        code_style_score: Score for coding convention adherence (0.0-1.0).
                          编码约定遵循度评分(0.0-1.0).
        test_coverage: Estimated test coverage ratio (0.0-1.0), or None if unassessable.
                       估计测试覆盖率(0.0-1.0),如无法评估则为None.
        test_framework: Name of detected testing framework (e.g., 'pytest', 'jest').
                        检测到的测试框架名称(例如'pytest','jest').
        has_tests: Whether test directory or test files were found.
                   是否发现测试目录或测试文件.
        dependency_count: Total number of declared dependencies.
                         声明的依赖总数.
        outdated_dependencies: Count of dependencies with known outdated versions.
                             已知过时版本的依赖数量.
        security_issues: List of detected security vulnerability descriptions.
                         检测到的安全漏洞描述列表.
        doc_completeness: Documentation completeness score (0.0-1.0).
                         文档完整性评分(0.0-1.0).
        has_readme: Whether README.md exists.
                    是否存在README.md.
        has_api_docs: Whether API documentation was found (Sphinx/MkDocs/etc).
                     是否发现API文档(Sphinx/MkDocs等).
        has_examples: Whether example code or tutorials exist.
                     是否存在示例代码或教程.
        architecture_score: Code organization and modularity score (0.0-1.0).
                           代码组织和模块化评分(0.0-1.0).
        complexity_indicators: Dictionary mapping metric names to values.
                              映射指标名称到值的字典.
        overall_score: Weighted comprehensive score (0.0-100.0).
                       加权综合分数(0.0-100.0).
    """
    code_style_score: float = 0.0
    test_coverage: Optional[float] = None
    test_framework: Optional[str] = None
    has_tests: bool = False
    dependency_count: int = 0
    outdated_dependencies: int = 0
    security_issues: List[str] = field(default_factory=list)
    doc_completeness: float = 0.0
    has_readme: bool = False
    has_api_docs: bool = False
    has_examples: bool = False
    architecture_score: float = 0.0
    complexity_indicators: Dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0


# ===========================================================================
# Community Metrics / 社区指标
# ===========================================================================

@dataclass
class CommunityMetrics:
    """Community health and activity assessment metrics.

    Tracks community engagement patterns through star growth trends,
    commit frequency, issue handling efficiency, contributor diversity,
    and recency of activity indicators.

    社区健康度和活动评估指标.
通过Star增长趋势,提交频率,Issue处理效率,贡献者多样性
和最近活动指示器来跟踪社区参与模式.

    Attributes:
        total_stars: Current cumulative star count.
                     当前累计Star数.
        star_growth_30d: Star count increase over last 30 days.
                         最近30天的Star增长数.
        star_growth_90d: Star count increase over last 90 days.
                         最近90天的Star增长数.
        stars_per_day: Average daily star growth rate (since creation or measurable period).
                      平均每日Star增长率(自创建以来或可测量期间).
        commit_frequency_weekly: Average commits per week over recent period.
                                 近期平均每周提交数.
        recent_commits_30d: Total commits in the last 30 days.
                            最近30天总提交数.
        active_contributors_30d: Number of contributors active in last 30 days.
                                最近30天内活跃的贡献者数量.
        total_contributors: All-time unique contributor count.
                           历史唯一贡献者总数.
        open_issues: Currently unresolved issue count.
                     当前未解决的Issue数量.
        closed_total: All-time closed issue count.
                     历史已关闭Issue总数.
        issue_resolution_rate: Ratio of closed to total issues (0.0-1.0).
                              已关闭Issue与总Issue的比率(0.0-1.0).
        avg_resolution_days: Average days to close an issue (0.0 = instant, None = no data).
                            关闭一个Issue的平均天数(0.0=即时,None=无数据).
        open_prs: Currently open pull request count.
                 当前开放的Pull Request数量.
        merged_prs_total: All-time merged PR count.
                         历史已合并PR总数.
        pr_merge_rate: Ratio of merged to total PRs (0.0-1.0).
                      已合并PR与总PR的比率(0.0-1.0).
        days_since_last_commit: Days elapsed since most recent commit (-1 if unknown).
                               距最近提交经过的天数(未知则-1).
        days_since_last_release: Days elapsed since latest release (-1 if none).
                                距最新发布经过的天数(无发布则-1).
        project_age_days: Total age of the project in days.
                         项目的总天数年龄.
        activity_score: Normalized activity level score (0.0-100.0).
                       标准化活跃度评分(0.0-100.0).
        health_score: Overall community health indicator (0.0-100.0).
                     整体社区健康度指示器(0.0-100.0).
        overall_score: Comprehensive community dimension score (0.0-100.0).
                      综合社区维度分数(0.0-100.0).
    """
    total_stars: int = 0
    star_growth_30d: float = 0.0
    star_growth_90d: float = 0.0
    stars_per_day: float = 0.0
    commit_frequency_weekly: float = 0.0
    recent_commits_30d: int = 0
    active_contributors_30d: int = 0
    total_contributors: int = 0
    open_issues: int = 0
    closed_total: int = 0
    issue_resolution_rate: float = 0.0
    avg_resolution_days: Optional[float] = None
    open_prs: int = 0
    merged_prs_total: int = 0
    pr_merge_rate: float = 0.0
    days_since_last_commit: int = -1
    days_since_last_release: int = -1
    project_age_days: int = 0
    activity_score: float = 0.0
    health_score: float = 0.0
    overall_score: float = 0.0


# ===========================================================================
# Maturity Metrics / 成熟度指标
# ===========================================================================

@dataclass
class MaturityMetrics:
    """Project maturity and production-readiness assessment metrics.

    Evaluates a project's readiness for production use by examining
    version management discipline, CI/CD infrastructure, governance practices,
    and supporting ecosystem maturity.

    项目成熟度和生产就绪度评估指标.
通过检查版本管理规范,CI/CD基础设施,治理实践和支持生态系统成熟度
来评估项目用于生产的就绪程度.

    Attributes:
        release_count: Total number of published releases.
                       已发布版本的总数.
        uses_semver: Whether versions follow semantic versioning convention.
                    版本是否遵循语义化版本约定.
        latest_version: Most recent version string (e.g., '2.1.0').
                       最新版本字符串(例如'2.1.0').
        days_since_last_release: Days since most recent release (-1 if never released).
                                距最近发布的天数(从未发布则-1).
        release_frequency_days: Average days between consecutive releases (0.0 if only one).
                               连续发布之间的平均天数(仅一次发布则0.0).
        has_ci_config: Whether CI configuration was detected (.github/workflows, etc.).
                      是否检测到CI配置(.github/workflows等).
        ci_platform: Detected CI platform name ('github-actions', 'travis-ci', etc.).
                    检测到的CI平台名称('github-actions','travis-ci'等).
        has_cd_pipeline: Whether continuous deployment is configured.
                        是否配置了持续部署.
        has_automated_tests: Whether automated tests are configured in CI.
                            CI中是否配置了自动化测试.
        has_code_quality_check: Whether code quality tools run in CI (linting, type-checking).
                               CI是否运行代码质量工具(linting,type-checking).
        has_license: Whether a license file is present.
                    是否存在许可证文件.
        license_type: SPDX identifier of the license.
                     许可证的SPDX标识符.
        has_code_of_conduct: Whether a code of conduct document exists.
                             是否存在行为准则文档.
        has_contributing_guide: Whether contribution guidelines are documented.
                               是否记录了贡献指南.
        has_security_policy: Whether a SECURITY.md policy file exists.
                            是否存在SECURITY.md策略文件.
        has_issue_template: Custom issue templates are configured.
                          配置了自定义Issue模板.
        has_pr_template: Custom PR templates are configured.
                       配置了自定义PR模板.
        has_discussion_forum: Discussion forums enabled (GitHub Discussions, Discord, etc.).
                             启用了讨论论坛(GitHub Discussions,Discord等).
        has_website: Project has an external website.
                    项目有外部网站.
        has_roadmap: Public roadmap or future plans are documented.
                   公开路线图或未来计划已记录.
        has_changelog: Change log file (CHANGELOG.md, HISTORY.md, etc.) exists.
                      变更日志文件(CHANGELOG.md,HISTORY.md等)存在.
        maturity_level: Classified maturity stage ('experimental'|'beta'|'stable'|'mature').
                       分类成熟阶段('experimental'|'beta'|'stable'|'mature').
        overall_score: Comprehensive maturity dimension score (0.0-100.0).
                      综合成熟度维度分数(0.0-100.0).
    """
    release_count: int = 0
    uses_semver: bool = False
    latest_version: Optional[str] = None
    days_since_last_release: int = -1
    release_frequency_days: float = 0.0
    has_ci_config: bool = False
    ci_platform: Optional[str] = None
    has_cd_pipeline: bool = False
    has_automated_tests: bool = False
    has_code_quality_check: bool = False
    has_license: bool = False
    license_type: Optional[str] = None
    has_code_of_conduct: bool = False
    has_contributing_guide: bool = False
    has_security_policy: bool = False
    has_issue_template: bool = False
    has_pr_template: bool = False
    has_discussion_forum: bool = False
    has_website: bool = False
    has_roadmap: bool = False
    has_changelog: bool = False
    maturity_level: str = "experimental"
    overall_score: float = 0.0
