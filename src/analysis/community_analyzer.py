"""
Community Activity Analyzer.

Evaluates GitHub project community health through metrics including
star growth trends, commit frequency, issue handling efficiency,
contributor diversity, and recency of activity.

社区活跃度分析器.
通过包括Star增长趋势,提交频率,Issue处理效率,
贡献者多样性和最近活动时间在内的指标评估GitHub项目社区健康度.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from src.models.metrics import CommunityMetrics
from src.models.repository import Repository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CommunityAnalyzer:
    """Community health and activity assessment engine.

    Aggregates data from GitHub API endpoints to compute community vitality
    scores across engagement, responsiveness, and sustainability dimensions.

    社区健康度和活动性评估引擎.
聚合来自GitHub API端点的数据以计算参与度,响应能力和可持续性维度上的
    社区活力分数.

    Attributes:
        github_client: Client for fetching community data from GitHub API.
                      用于从GitHub API获取社区数据的客户端.
    """

    def __init__(self, github_client: Any = None) -> None:
        self.github_client = github_client

    async def analyze(self, repository: Repository) -> CommunityMetrics:
        """Analyze community metrics for a repository.

        分析仓库的社区指标.

        Args:
            repository: Repository with basic metadata populated.
                       已填充基本元数据的仓库.

        Returns:
            Complete CommunityMetrics assessment.
             完整的CommunityMetrics评估.
        """
        start_time = time.time()
        owner_repo = repository.full_name.split("/")
        owner = owner_repo[0] if len(owner_repo) > 0 else ""
        repo = owner_repo[1] if len(owner_repo) > 1 else ""

        logger.info(
            "module=analysis", operation="community_analysis_start",
            params={"repo": repository.full_name},
        )

        try:
            # Fetch detailed community data / 获取详细社区数据
            raw_metrics: Dict[str, Any] = {}

            if self.github_client:
                raw_metrics = await self.github_client.get_community_metrics(owner, repo)
            else:
                raw_metrics = self._estimate_from_repository(repository)

            # Compute derived metrics / 计算派生指标
            now = datetime.now(timezone.utc)

            # Star growth calculations / Star增长计算
            total_stars = repository.stars
            star_growth_30d = raw_metrics.get("star_growth_30d", self._estimate_star_growth(total_stars, 30))
            star_growth_90d = raw_metrics.get("star_growth_90d", self._estimate_star_growth(total_stars, 90))
            days_age = max(1, repository.age_days)
            stars_per_day = total_stars / days_age if days_age > 0 else 0

            # Commit activity / 提交活动
            commit_freq = raw_metrics.get("commit_frequency_weekly", self._estimate_commit_frequency(repository))

            # Issue handling / Issue处理
            open_issues = raw_metrics.get("open_issues", repository.open_issues)
            issue_rate = min(1.0, (total_stars * 0.01) / max(1, open_issues)) if open_issues > 0 else 1.0
            avg_resolution = raw_metrics.get("avg_resolution_days")

            # Contributors / 贡献者
            total_contributors = raw_metrics.get("contributor_count",
                                              len(raw_metrics.get("top_contributors", [])))
            active_30d = min(total_contributors, int(total_contributors * 0.4))  # Estimate / 估算

            # Time-based recency / 基于时间的最近度
            days_since_push = repository.days_since_last_push
            days_since_release = raw_metrics.get("days_since_last_release", days_since_push)

            # Calculate composite scores / 计算综合分数
            activity_score = self._calculate_activity_score(
                stars_per_day, commit_freq, total_contributors, days_since_push,
            )
            health_score = self._calculate_health_score(
                issue_rate, avg_resolution, total_contributors, open_issues,
            )
            overall_score = (
                activity_score * 0.55 + health_score * 0.45
            )

            metrics = CommunityMetrics(
                total_stars=total_stars,
                star_growth_30d=star_growth_30d,
                star_growth_90d=star_growth_90d,
                stars_per_day=round(stars_per_day, 2),
                commit_frequency_weekly=round(commit_freq, 1),
                recent_commits_30d=int(commit_freq * 4),  # Rough estimate / 粗略估算
                active_contributors_30d=active_30d,
                total_contributors=total_contributors,
                open_issues=open_issues,
                closed_total=raw_metrics.get("closed_total", int(open_issues * 3)),
                issue_resolution_rate=round(issue_rate, 2),
                avg_resolution_days=avg_resolution,
                open_prs=raw_metrics.get("open_prs", 0),
                merged_prs_total=raw_metrics.get("merged_prs", 0),
                pr_merge_rate=raw_metrics.get("pr_merge_rate", min(0.8, health_score / 100)),
                days_since_last_commit=max(0, days_since_push),
                days_since_last_release=max(-1, days_since_release),
                project_age_days=days_age,
                activity_score=round(activity_score, 1),
                health_score=round(health_score, 1),
                overall_score=min(100.0, max(0.0, round(overall_score, 1))),
                analysis_duration_ms=int((time.time() - start_time) * 1000),
            )

            logger.info(
                "module=analysis", operation="community_analysis_complete",
                params={
                    "repo": repository.full_name,
                    "overall": metrics.overall_score,
                    "activity": metrics.activity_score,
                    "health": metrics.health_score,
                    "duration_ms": metrics.analysis_duration_ms,
                },
            )
            return metrics

        except Exception as e:
            logger.error(
                "module=analysis", operation="community_analysis_error",
                params={"repo": repository.full_name, "error": str(e)},
            )
            return CommunityMetrics(
                total_stars=repository.stars,
                overall_score=0.0,
                errors=[str(e)],
                analysis_duration_ms=int((time.time() - start_time) * 1000),
            )

    def _calculate_activity_score(
        self,
        stars_per_day: float,
        commits_per_week: float,
        contributors: int,
        days_since_push: int,
    ) -> float:
        """Calculate normalized activity score (0-100).

        计算标准化活跃度分数(0-100)."""
        score = 0.0

        # Star velocity (max 35 points) / Star速度(最高35分)
        spd_normalized = min(1.0, stars_per_day / 50.0)  # 50+ stars/day is excellent
        score += spd_normalized * 35.0

        # Commit frequency (max 30 points) / 提交频率(最高30分)
        cf_normalized = min(1.0, commits_per_week / 20.0)  # 20+/week is very active
        score += cf_normalized * 30.0

        # Contributor base (max 20 points) / 贡献者基础(最高20分)
        c_norm = min(1.0, contributors / 50.0)  # 50+ is large community
        score += c_norm * 20.0

        # Recency bonus/penalty (max 15 points) / 最近度奖励/惩罚(最高15分)
        if days_since_push <= 7:
            score += 15.0  # Very recent / 非常最近
        elif days_since_push <= 30:
            score += 10.0
        elif days_since_push <= 90:
            score += 5.0
        elif days_since_push > 365:
            score -= 5.0   # Stale / 过时
        else:
            score += 0.0

        return max(0.0, min(100.0, score))

    def _calculate_health_score(
        self,
        issue_resolution_rate: float,
        avg_resolution_days: Optional[float],
        contributors: int,
        open_issues: int,
    ) -> float:
        """Calculate community health/responsiveness score (0-100).

        计算社区健康/响应能力分数(0-100)."""
        score = 0.0

        # Issue resolution rate (max 40 points) / Issue解决率(最高40分)
        score += issue_resolution_rate * 40.0

        # Response time (max 25 points) / 响应时间(最高25分)
        if avg_resolution_days is not None:
            if avg_resolution_days < 7:
                score += 25.0
            elif avg_resolution_days < 30:
                score += 18.0
            elif avg_resolution_days < 90:
                score += 10.0
            else:
                score += 3.0
        else:
            score += 15.0  # Neutral / 中性

        # Community size factor (max 20 points) / 社区规模因素(最高20分)
        c_factor = min(1.0, contributors / 20.0)
        score += c_factor * 20.0

        # Open issue ratio penalty (max -15) / 开放Issue比例惩罚(最多-15)
        if contributors > 5 and open_issues > 100:
            issue_ratio = open_issues / contributors
            if issue_ratio > 10:
                score -= 10.0
            elif issue_ratio > 5:
                score -= 5.0

        return max(0.0, min(100.0, score))

    @staticmethod
    def _estimate_star_growth(total_stars: int, days_back: int) -> float:
        """Heuristic star growth estimation when API history unavailable.

        当API历史不可用时的启发式Star增长估算."""
        # Assume exponential decay model: most growth early, slowing over time
        # 假设指数衰减模型:早期大部分增长,随后放缓
        age_penalty = max(0.1, 1.0 - (days_back / 1000))  # Decay over ~3 years
        base_daily = total_stars / 500  # Rough baseline / 粗略基准线
        return base_daily * age_penalty * days_back

    @staticmethod
    def _estimate_commit_frequency(repo: Repository) -> float:
        """Estimate weekly commit frequency from available data.

        从可用数据估算每周提交频率."""
        if repo.days_since_last_push < 0 or repo.age_days == 0:
            return 5.0  # Default assumption / 默认假设

        # Rough heuristic based on project maturity / 基于项目成熟度的粗略启发式
        if repo.stars > 50000:
            return 25.0  # Major projects are usually very active / 大型项目通常非常活跃
        elif repo.stars > 5000:
            return 12.0
        elif repo.stars > 500:
            return 6.0
        else:
            return 2.0

    def _estimate_from_repository(self, repo: Repository) -> Dict[str, Any]:
        """Generate rough estimates from base repository data only.

        仅从基本仓库数据生成粗略估算."""
        return {
            "contributor_count": max(1, repo.stars // 200),
            "top_contributors": [],
            "star_growth_30d": self._estimate_star_growth(repo.stars, 30),
            "commit_frequency_weekly": self._estimate_commit_frequency(repo),
        }


__all__ = ["CommunityAnalyzer"]
