"""
Scoring Module - Multi-dimensional weighted scoring and ranking.

Calculates comprehensive scores across 6 dimensions (code quality,
community, functionality, maturity, reputation, sustainability)
and generates ranked project comparisons.

评分模块 - 多维度加权评分与排名。
在6个维度（代码质量、社区、功能完整性、成熟度、用户评价、维护可持续性）
上计算综合分数，并生成排名的项目比较结果。
"""

from src.scoring.score_calculator import ScoreCalculator
from src.scoring.ranking_engine import RankingEngine

__all__ = ["ScoreCalculator", "RankingEngine"]
