"""
Common Type Definitions - Shared types used across the project.

Defines common type aliases, constants, and utility functions
used by multiple modules in the codebase.

通用类型定义 - 项目中使用的共享类型。
定义代码库中多个模块使用的通用类型别名、常量和工具函数。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class MaturityLevel(str, Enum):
    """Project maturity classification levels.

    Defines the stability and production-readiness stages
    that a GitHub project can be classified into.

    项目成熟度分类级别。
定义GitHub项目可以被归类到的稳定性和生产就绪阶段。

    Attributes:
        EXPERIMENTAL: Early stage with unstable APIs (<30 score).
                      实验阶段，API不稳定（<30分）。
        BETA: Beta stage, basic functionality works (30-50 score).
              Beta阶段，基本功能可用（30-50分）。
        STABLE: Stable version suitable for production (50-75 score).
                稳定版本，可用于生产环境（50-75分）。
        MATURE: Mature project with ecosystem support (>75 score).
                成熟项目，有完善的生态支持（>75分）。
    """
    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    MATURE = "mature"


class RankTier(str, Enum):
    """Ranking tier classification (S/A/B/C/D).

    Categorizes projects into tiers based on their comprehensive scores.
    Higher tiers indicate better overall quality and recommendation priority.

    排名分级分类（S/A/B/C/D）。
根据综合分数将项目分类到不同等级。更高的等级表示更好的整体质量和推荐优先级。

    Attributes:
        S: Top tier (score >= 90). Exceptional quality across all dimensions.
           顶级（>=90分）。所有维度都表现卓越。
        A: Excellent tier (score >= 75). Strong performance with minor gaps.
           优秀级（>=75分）。表现强劲但有轻微不足。
        B: Good tier (score >= 60). Solid choice for most use cases.
           良好级（>=60分）。大多数用例的可靠选择。
        C: Acceptable tier (score >= 40). Usable but with notable concerns.
           可接受级（>=40分）。可用但有明显问题。
        D: Low tier (score < 40). Not recommended except for specific cases.
           低等级（<40分）。除非特殊情况否则不推荐。
    """
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class LLMProvider(str, Enum):
    """Supported LLM provider backends.

    Lists all AI model providers that this system can interface with,
    ordered by preference priority.

    支持的LLM提供商后端。
列出此系统可以交互的所有AI模型提供程序，按优先级排序。

    Attributes:
        OLLAMA: Local Ollama instance (primary choice, privacy-preserving).
                本地Ollama实例（首选，保护隐私）。
        OPENAI: OpenAI-compatible API (fallback option).
                OpenAI兼容API（备选方案）。
        LITELLM: LiteLLM unified routing layer (universal fallback).
                 LiteLLM统一路由层（通用回退方案）。
    """
    OLLAMA = "ollama"
    OPENAI = "openai"
    LITELLM = "litellm"


# ---------------------------------------------------------------------------
# Type Aliases / 类型别名
# ---------------------------------------------------------------------------

# JSON-compatible value types / JSON兼容值类型
JsonValue = Optional[Union[str, int, float, bool, List[Any], Dict[str, Any]]]

# Common dictionary types / 常用字典类型
MetadataDict = Dict[str, str]
ScoresDict = Dict[str, float]

# Path types / 路径类型
PathStr = str


# ---------------------------------------------------------------------------
# Constants / 常量
# ---------------------------------------------------------------------------

# Default scoring weights (can be overridden by config) / 默认评分权重（可被配置覆盖）
DEFAULT_SCORING_WEIGHTS: ScoresDict = {
    "code_quality": 0.25,
    "community": 0.20,
    "functionality": 0.18,
    "maturity": 0.15,
    "reputation": 0.12,
    "sustainability": 0.10,
}

# Default thresholds / 默认阈值
DEFAULT_RELEVANCE_THRESHOLD: float = 0.6
DEFAULT_MAX_PROJECTS: int = 20
DEFAULT_MIN_PROJECTS: int = 5

# Score range / 分数范围
MIN_SCORE: float = 0.0
MAX_SCORE: float = 100.0


def score_to_tier(score: float) -> RankTier:
    """Convert a numeric score to a rank tier.

    Maps a comprehensive score (0-100) to its corresponding S/A/B/C/D tier
    based on predefined threshold boundaries.

    将数值分数转换为排名等级。
根据预定义的阈值边界将综合分数（0-100）映射到对应的S/A/B/C/D等级。

    Args:
        score: Comprehensive score between 0 and 100.
               0到100之间的综合分数。

    Returns:
        The corresponding RankTier enum value.
        对应的RankTier枚举值。
    """
    if score >= 90.0:
        return RankTier.S
    elif score >= 75.0:
        return RankTier.A
    elif score >= 60.0:
        return RankTier.B
    elif score >= 40.0:
        return RankTier.C
    else:
        return RankTier.D


def score_to_maturity(score: float) -> MaturityLevel:
    """Convert a maturity score to a maturity level classification.

    Maps a maturity assessment score to its corresponding level:
    experimental/beta/stable/mature.

    将成熟度分数转换为成熟度级别分类。
将成熟度评估分数映射到对应的级别：experimental/beta/stable/mature。

    Args:
        score: Maturity assessment score between 0 and 100.
               0到100之间的成熟度评估分数。

    Returns:
        The corresponding MaturityLevel enum value.
        对应的MaturityLevel枚举值。
    """
    if score >= 75.0:
        return MaturityLevel.MATURE
    elif score >= 50.0:
        return MaturityLevel.STABLE
    elif score >= 30.0:
        return MaturityLevel.BETA
    else:
        return MaturityLevel.EXPERIMENTAL
