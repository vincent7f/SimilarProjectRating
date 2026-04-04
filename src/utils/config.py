"""
Configuration Management Module.

Provides a centralized configuration system that loads settings from YAML files
with environment variable override support. Uses dataclass-based typed access
with validation defaults for all application settings.

配置管理模块。
提供集中的配置系统，从YAML文件加载设置并支持环境变量覆盖。
使用基于dataclass的类型化访问，并为所有应用程序设置提供验证默认值。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def _resolve_env_vars(value: Any) -> Any:
    """Recursively resolve environment variable references in config values.

    Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax within YAML values.
    Strings containing ${...} patterns are replaced with the corresponding
    environment variable value or default.

    递归解析配置值中的环境变量引用。
支持YAML值中的${VAR_NAME}和${VAR_NAME:-default}语法。
包含${...}模式的字符串将被替换为对应的环境变量值或默认值。

    Args:
        value: The config value to resolve (str, dict, list, or other).
               要解析的配置值（字符串、字典、列表或其他）。

    Returns:
        Value with all environment variable references resolved.
        所有环境变量引用已解析的值。
    """
    if isinstance(value, str):
        pattern = re.compile(r'\$\{(\w+)(?::-([^}]*))?\}')

        def _replacer(match: re.Match) -> str:
            var_name = match.group(1)
            default = match.group(2) or ""
            return os.environ.get(var_name, default)

        resolved = pattern.sub(_replacer, value)
        # Re-check for nested env vars (one level only) / 检查嵌套环境变量（仅一层）
        if "${" in resolved:
            resolved = pattern.sub(_replacer, resolved)
        return resolved
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


@dataclass
class GitHubConfig:
    """GitHub API configuration parameters.

    Encapsulates all settings needed for interacting with the GitHub REST/GraphQL APIs,
    including authentication tokens, rate limit handling, and timeout configurations.

    GitHub API配置参数。
封装与GitHub REST/GraphQL API交互所需的所有设置，
包括认证令牌、速率限制处理和超时配置。

    Attributes:
        api_token: GitHub personal access token for authenticated requests.
                   用于认证请求的GitHub个人访问令牌。
        rate_limit: Maximum number of API calls per hour (unauthenticated: 60, auth: 5000).
                    每小时最大API调用次数（未认证：60，认证：5000）。
        timeout_seconds: Request timeout in seconds for HTTP calls.
                         HTTP请求的超时时间（秒）。
        base_url: Custom GitHub API base URL (for GitHub Enterprise).
                  自定义GitHub API基础URL（用于GitHub Enterprise）。
        per_page: Number of results per page for paginated API responses.
                 分页API响应的每页结果数。
    """
    api_token: str = ""
    rate_limit: int = 5000
    timeout_seconds: int = 30
    base_url: str = "https://api.github.com"
    per_page: int = 30

    @property
    def is_authenticated(self) -> bool:
        """Check if an API token has been configured.

        检查是否已配置API令牌。

        Returns:
            True if token is non-empty, False otherwise.
            如果令牌非空则返回True，否则返回False。
        """
        return bool(self.api_token)


@dataclass
class AIConfig:
    """AI/LLM provider configuration parameters.

    Manages settings for connecting to various LLM backends including local
    Ollama instances, OpenAI-compatible APIs, and LiteLLM unified router.
    Supports automatic provider failover when enabled.

    AI/LLM提供商配置参数。
管理连接各种LLM后端的设置，包括本地Ollama实例、OpenAI兼容API
和LiteLLM统一路由器。启用时支持自动提供商故障转移。

    Attributes:
        provider: Primary LLM provider identifier ('ollama', 'openai', 'litellm').
                  主要LLM提供商标识符（'ollama'、'openai'、'litellm'）。
        model: Model name to use (e.g., 'llama3.2:latest', 'gpt-4').
               要使用的模型名称（例如'llama3.2:latest'、'gpt-4'）。
        api_base: Base URL for the LLM API endpoint.
                  LLM API端点的基础URL。
        api_key: API key for cloud-based LLM services.
                 基于云的LLM服务的API密钥。
        fallback_enabled: Whether to automatically switch providers on failure.
                         是否在失败时自动切换提供商。
        temperature: Sampling temperature for text generation (0.0-2.0).
                     文本生成的采样温度（0.0-2.0）。
        max_tokens: Maximum tokens per LLM response.
                    每次LLM响应的最大token数。
        request_timeout: Timeout in seconds for LLM API calls.
                        LLM API调用的超时时间（秒）。
        max_retries: Maximum retry attempts on transient failures.
                    瞬态故障的最大重试次数。
    """
    provider: str = "ollama"
    model: str = "llama3.2:latest"
    api_base: str = "http://localhost:11434"
    api_key: str = ""
    fallback_enabled: bool = True
    temperature: float = 0.7
    max_tokens: int = 2048
    request_timeout: int = 120
    max_retries: int = 3


@dataclass
class AnalysisConfig:
    """Analysis engine configuration parameters.

    Controls behavior of the multi-dimensional project analysis system including
    project count limits, relevance filtering thresholds, and code download settings.

    分析引擎配置参数。
控制多维项目分析系统的行为，包括项目数量限制、相关性过滤阈值和代码下载设置。

    Attributes:
        max_projects: Maximum number of projects to retain after filtering (top-N by stars).
                      过滤后保留的最大项目数量（按stars取前N个）。
        min_similarity_score: Minimum relevance threshold for keeping projects (0.0-1.0).
                              保留项目的最小相关性阈值（0.0-1.0）。
        download_timeout: Timeout in seconds for downloading release archives.
                         下载release压缩包的超时时间（秒）。
        max_code_size_mb: Skip detailed analysis if repo archive exceeds this size (MB).
                          如果repo压缩包超过此大小则跳过详细分析（MB）。
        parallel_analysis: Enable concurrent analysis of multiple projects.
                           启用多项目并行分析。
        max_concurrent_analyses: Max number of simultaneous project analyses.
                                同时进行的项目分析最大数量。
        skip_large_repos: If True, analyze only core directories for repos > max_code_size_mb.
                          如果为True，对于>max_code_size_mb的repo仅分析核心目录。
    """
    max_projects: int = 20
    min_similarity_score: float = 0.6
    download_timeout: int = 300
    max_code_size_mb: int = 50
    parallel_analysis: bool = True
    max_concurrent_analyses: int = 4
    skip_large_repos: bool = True


@dataclass
class ScoringConfig:
    """Scoring system configuration parameters.

    Defines dimension weights for the multi-dimensional weighted scoring algorithm
    and normalization parameters for fair comparison across different scales.

    评分系统配置参数。
定义多维加权评分算法的维度权重以及用于跨不同尺度公平比较的标准化参数。

    Attributes:
        weights: Dictionary mapping dimension names to their weight coefficients.
                 Each weight should be positive and sum to approximately 1.0.
                 将维度名称映射到其权重系数的字典。
                 每个权重应为正数且总和约为1.0。
        normalization_method: Strategy for normalizing raw scores ('minmax' or 'zscore').
                             标准化原始分数的策略（'minmax'或'zscore'）。
    """
    weights: Dict[str, float] = field(default_factory=lambda: {
        "code_quality": 0.25,
        "community": 0.20,
        "functionality": 0.18,
        "maturity": 0.15,
        "reputation": 0.12,
        "sustainability": 0.10,
    })
    normalization_method: str = "minmax"

    def validate_weights(self) -> None:
        """Validate that weights sum to approximately 1.0 and are non-negative.

        Raises ValueError if validation fails.
        验证权重总和约为1.0且非负。
        验证失败则抛出ValueError。
        """
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Scoring weights must sum to ~1.0, got {total:.4f}. "
                f"Scoring权重总和必须约为1.0，当前值为{total:.4f}。"
            )
        for name, w in self.weights.items():
            if w < 0:
                raise ValueError(
                    f"Scoring weight '{name}' must be non-negative, got {w}. "
                    f"评分权重'{name}'必须为非负数，当前值为{w}。"
                )


@dataclass
class LoggingConfig:
    """Logging system configuration parameters.

    Configures output format, destination, rotation policy, and verbosity levels
    for the structured JSON logging system.

    日志系统配置参数。
配置结构化JSON日志系统的输出格式、目标、轮转策略和详细程度级别。

    Attributes:
        level: Minimum log level to capture ('DEBUG', 'INFO', 'WARNING', 'ERROR').
               要捕获的最小日志级别（'DEBUG'、'INFO'、'WARNING'、'ERROR'）。
        file_path: Directory path where log files are stored.
                  日志文件存储的目录路径。
        max_size_mb: Maximum log file size before rotation (MB).
                    轮转前的日志文件最大大小（MB）。
        backup_count: Number of rotated backup log files to retain.
                     保留的轮转备份日志文件数量。
        console_output: Whether to also log to stdout/stderr.
                        是否也输出到标准输出/标准错误。
        json_format: Use structured JSON format instead of text.
                    使用结构化JSON格式而非文本格式。
        session_log_prefix: Filename prefix for per-session log files.
                          每次会话日志文件的文件名前缀。
    """
    level: str = "INFO"
    file_path: str = "./logs"
    max_size_mb: int = 100
    backup_count: int = 5
    console_output: bool = True
    json_format: bool = True
    session_log_prefix: str = "session_"


@dataclass
class CacheConfig:
    """File-based caching configuration parameters.

    Controls behavior of the local filesystem cache used to avoid redundant
    API calls and speed up repeated analyses.

    基于文件的缓存配置参数。
控制用于避免冗余API调用和加速重复分析的本地文件系统缓存的行为。

    Attributes:
        enabled: Whether caching is active.
                 是否启用缓存。
        ttl_seconds: Time-to-live for cached entries before expiration.
                    缓存条目的过期生存时间（秒）。
        directory: Filesystem path for storing cache files.
                  存储缓存文件的文件系统路径。
        max_entries: Maximum number of cached items to retain.
                    保留的最大缓存项数量。
    """
    enabled: bool = True
    ttl_seconds: int = 3600
    directory: str = "./data/cache"
    max_entries: int = 500


@dataclass
class Config:
    """Root configuration container holding all sub-configurations.

    This is the main entry point for accessing any application setting.
    Loaded from a YAML file with environment variable overrides supported.

    根配置容器，包含所有子配置。
这是访问任何应用程序设置的主入口点。
从YAML文件加载，支持环境变量覆盖。

    Attributes:
        github: GitHub API interaction settings.
                GitHub API交互设置。
        ai: LLM provider and model settings.
           LLM提供商和模型设置。
        analysis: Project analysis engine settings.
                  项目分析引擎设置。
        scoring: Multi-dimensional scoring system settings.
                多维评分系统设置。
        logging: Structured logging system settings.
                结构化日志系统设置。
        cache: Local filesystem cache settings.
              本地文件系统缓存设置。
        _source_path: Original YAML file path (internal use).
                     原始YAML文件路径（内部使用）。
    """
    github: GitHubConfig = field(default_factory=GitHubConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    _source_path: Optional[Path] = field(default=None, repr=False)

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        """Load configuration from a YAML file.

        Reads the specified YAML file, resolves environment variable references
        (${VAR_NAME} syntax), and constructs a fully populated Config instance
        with all nested sub-configurations initialized.

        从YAML文件加载配置。
读取指定的YAML文件，解析环境变量引用（${VAR_NAME}语法），
并构造一个完全填充的Config实例，其中所有嵌套子配置都已初始化。

        Args:
            path: Path to the YAML configuration file.
                  YAML配置文件的路径。

        Returns:
            Fully populated Config instance with all settings loaded.
            已加载所有设置的完全填充Config实例。

        Raises:
            FileNotFoundError: If the config file does not exist.
                              如果配置文件不存在。
            yaml.YAMLError: If the YAML syntax is invalid.
                           如果YAML语法无效。
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {file_path}. "
                f"配置文件未找到：{file_path}。"
            )

        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

        resolved_data = _resolve_env_vars(raw_data)

        config = cls()
        config._source_path = file_path
        config._apply(resolved_data)

        # Validate critical settings / 验证关键设置
        try:
            config.scoring.validate_weights()
        except ValueError as e:
            print(f"[WARN] Scoring weight validation warning: {e}")

        return config

    def _apply(self, data: Dict[str, Any]) -> None:
        """Apply parsed YAML data to config fields recursively.

        将解析的YAML数据递归应用到配置字段。

        Args:
            data: Dictionary mapping section names to their config values.
                  将段名称映射到其配置值的字典。
        """
        if "github" in data and isinstance(data["github"], dict):
            for k, v in data["github"].items():
                if hasattr(self.github, k):
                    setattr(self.github, k, v)

        if "ai" in data and isinstance(data["ai"], dict):
            for k, v in data["ai"].items():
                if hasattr(self.ai, k):
                    setattr(self.ai, k, v)

        if "analysis" in data and isinstance(data["analysis"], dict):
            for k, v in data["analysis"].items():
                if hasattr(self.analysis, k):
                    setattr(self.analysis, k, v)

        if "scoring" in data and isinstance(data["scoring"], dict):
            if "weights" in data["scoring"]:
                self.scoring.weights.update(data["scoring"]["weights"])
            if "normalization_method" in data["scoring"]:
                self.scoring.normalization_method = data["scoring"]["normalization_method"]

        if "logging" in data and isinstance(data["logging"], dict):
            for k, v in data["logging"].items():
                if hasattr(self.logging, k):
                    setattr(self.logging, k, v)

        if "cache" in data and isinstance(data["cache"], dict):
            for k, v in data["cache"].items():
                if hasattr(self.cache, k):
                    setattr(self.cache, k, v)


# Default config path / 默认配置路径
DEFAULT_CONFIG_PATHS: List[str] = [
    "configs/config.yaml",
    "./configs/config.yaml",
]


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file with fallback to defaults.

    Attempts to load from the specified path or searches common locations.
    Falls back to default values if no config file is found.

    从文件加载配置，默认值作为后备。
尝试从指定路径或搜索常见位置加载。
如果未找到配置文件则使用默认值。

    Args:
        config_path: Explicit path to config file. If None, auto-detects.
                    配置文件的显式路径。如果为None则自动检测。

    Returns:
        Loaded or default Config instance.
        已加载或默认的Config实例。
    """
    paths_to_try: List[str] = []
    if config_path:
        paths_to_try.append(config_path)
    paths_to_try.extend(DEFAULT_CONFIG_PATHS)

    for path in paths_to_try:
        if Path(path).exists():
            return Config.from_yaml(path)

    # Return default config if no file found / 未找到文件则返回默认配置
    return Config()


# Module-level convenience function / 模块级便捷函数
__all__ = [
    "Config", "GitHubConfig", "AIConfig", "AnalysisConfig",
    "ScoringConfig", "LoggingConfig", "CacheConfig", "load_config",
]
