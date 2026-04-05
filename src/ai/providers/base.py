"""
Base LLM Provider Abstract Class.

Defines the interface that all LLM provider implementations must follow.
Provides common infrastructure for status tracking, error handling,
and response parsing shared across Ollama, OpenAI, and LiteLLM backends.

基础LLM提供程序抽象类.
定义所有LLM提供程序实现必须遵循的接口.
提供跨Ollama,OpenAI和LiteLLM后端共享的状态跟踪,错误处理
和响应解析的通用基础设施.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProviderHealth(str, Enum):
    """Health status classification for an LLM provider.

    LLM提供商的健康状态分类.

    Attributes:
        HEALTHY: Provider is responsive and operational.
                 提供商响应正常且可运行.
        DEGRADED: Provider responding but with issues (slow, limited).
                  提供商响应但存在问题(缓慢,受限).
        UNAVAILABLE: Provider cannot be reached or returns errors.
                    无法访问提供商或返回错误.
    """
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ProviderStatus:
    """Runtime status report for a provider instance.

    LLM提供程序实例的运行时状态报告.

    Attributes:
        name: Human-readable provider name ('Ollama', 'OpenAI', 'LiteLLM').
              可读的提供商名称('Ollama','OpenAI','LiteLLM').
        health: Current health assessment.
               当前健康评估.
        model: Model name currently in use (or configured).
              当前使用的模型名称(或已配置的).
        api_base: API endpoint URL being used.
                正在使用的API端点URL.
        latency_ms: Last request round-trip time in milliseconds (-1 if no requests yet).
                   最后请求往返时间(毫秒)(如尚无请求则-1).
        error: Last error message if any recent failures occurred.
               最近发生故障时的最后错误消息.
        supports_streaming: Whether this provider supports streaming responses.
                            此提供商是否支持流式响应.
        supports_structured_output: Whether structured/JSON mode output is supported.
                                    是否支持结构化/JSON模式输出.
    """
    name: str = ""
    health: ProviderHealth = ProviderHealth.HEALTHY
    model: str = ""
    api_base: str = ""
    latency_ms: int = -1
    error: Optional[str] = None
    supports_streaming: bool = False
    supports_structured_output: bool = False


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider.

    Normalizes the output format across different providers so downstream
    code can work with a consistent interface regardless of backend.

    来自任何LLM提供商的标准化响应.
规范化不同提供商的输出格式,使下游代码无论后端如何都能使用一致的接口.

    Attributes:
        content: The generated text response from the model.
                 模型生成的文本响应.
        raw_response: Original provider-specific response object (for debugging).
                     原始特定于提供商的响应对象(用于调试).
        finish_reason: Why generation stopped ('stop', 'length', 'error').
                      生成停止的原因('stop','length','error').
        usage: Token usage statistics if available.
               可用的令牌使用统计信息.
        provider_name: Which provider generated this response.
                      生成此响应的提供商.
        duration_ms: Total wall-clock time for this request.
                    此请求的总挂钟时间.
        is_cached: Whether this result came from a cache.
                  此结果是否来自缓存.
    """
    content: str = ""
    raw_response: Any = None
    finish_reason: str = "stop"
    usage: Optional[Dict[str, int]] = None
    provider_name: str = ""
    duration_ms: int = 0
    is_cached: bool = False


class BaseProvider(ABC):
    """Abstract base class for LLM provider implementations.

    Every provider (Ollama, OpenAI, LiteLLM) must inherit from this class and
    implement all abstract methods. Provides common retry logic, timeout handling,
    and status tracking infrastructure.

    LLM提供程序实现的抽象基类.
每个提供商(Ollama,OpenAI,LiteLLM)必须从此类继承并实现所有抽象方法.
提供通用的重试逻辑,超时处理和状态跟踪基础设施.

    Attributes:
        name: Display name for this provider implementation.
              此提供程序实现的显示名称.
        model: Model identifier to use with this provider.
              与此提供商一起使用的模型标识符.
        api_base: Base URL for the API endpoint.
                 API端点的基础URL.
        api_key: Authentication key (empty string if not required).
                 认证密钥(如不需要则为空字符串).
        timeout: Request timeout in seconds.
                请求超时时间(秒).
        max_retries: Maximum automatic retry attempts on transient errors.
                    瞬态错误时的最大自动重试次数.
        temperature: Sampling temperature (0.0=deterministic, 2.0=random).
                     采样温度(0.0=确定性,2.0=随机).
        max_tokens: Maximum tokens in generated response.
                   生成响应中的最大token数.
        _status: Runtime status tracking.
                运行时状态跟踪.
    """

    def __init__(
        self,
        name: str,
        model: str,
        api_base: str,
        api_key: str = "",
        timeout: int = 120,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize provider with connection parameters.

        使用连接参数初始化提供商.

        Args:
            name: Human-readable provider name.
                  可读的提供商名称.
            model: Model to use.
                  要使用的模型.
            api_base: API endpoint base URL.
                     API端点基础URL.
            api_key: API authentication key.
                    API认证密钥.
            timeout: Per-request timeout seconds.
                    每次请求超时秒数.
            max_retries: Max retries on failure.
                        失败时的最大重试次数.
            temperature: Generation sampling temperature.
                        生成采样温度.
            max_tokens: Max response token count.
                       最大响应token计数.
        """
        self.name = name
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._status = ProviderStatus(
            name=name,
            model=model,
            api_base=api_base,
        )

    @property
    def status(self) -> ProviderStatus:
        """Get current runtime status of this provider.

        获取此提供商的当前运行时状态.

        Returns:
            Current ProviderStatus snapshot.
             当前ProviderStatus快照.
        """
        return self._status

    # ------------------------------------------------------------------
    # Abstract Interface / 抽象接口
    # ------------------------------------------------------------------

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a text completion from the language model.

        从语言模型生成文本补全.

        Args:
            prompt: User or task-specific input text.
                   用户或任务特定的输入文本.
            system_prompt: Optional system-level instruction prefix.
                          可选的系统级指令前缀.
            **kwargs: Additional provider-specific parameters.
                     其他特定于提供商的参数.

        Returns:
            Standardized LLMResponse with content and metadata.
             包含内容和元数据的标准化LLMResponse.
        """
        ...

    @abstractmethod
    async def check_health(self) -> ProviderStatus:
        """Verify provider availability and responsiveness.

        验证提供商可用性和响应能力.

        Returns:
            Updated ProviderStatus reflecting current state.
             反映当前状态的更新后的ProviderStatus.
        """
        ...

    # ------------------------------------------------------------------
    # Common Utilities / 通用工具方法
    # ------------------------------------------------------------------

    def _update_status(
        self,
        health: Optional[ProviderHealth] = None,
        error: Optional[str] = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        """Update internal status tracking fields.

        更新内部状态跟踪字段.

        Args:
            health: New health state if provided.
                   如提供则使用新的健康状态.
            error: Error description if applicable.
                  如适用则使用错误描述.
            latency_ms: Measured latency if available.
                       如有可用则使用测量到的延迟.
        """
        if health is not None:
            self._status.health = health
        if error is not None:
            self._status.error = error
        if latency_ms is not None:
            self._status.latency_ms = latency_ms

    async def _retry_with_backoff(
        self,
        coro_func,
        *args: Any,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute an async function with exponential backoff retry logic.

        使用指数退避重试逻辑执行异步函数.

        Args:
            coro_func: Async callable to execute.
                      要执行的异步可调用对象.
            *args: Positional arguments for the callable.
                  可调用对象的位置参数.
            **kwargs: Keyword arguments for the callable.
                     可调用对象的关键字参数.

        Returns:
            Successful LLMResponse from the underlying call.
             来自底层调用的成功LLMResponse.

        Raises:
            Exception: If all retries exhausted without success.
                       如果所有重试耗尽仍未成功则抛出异常.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                start_time = asyncio.get_event_loop().time()
                response = await coro_func(*args, **kwargs)
                duration = int(
                    (asyncio.get_event_loop().time() - start_time) * 1000
                )
                self._update_status(
                    health=ProviderHealth.HEALTHY,
                    error=None,
                    latency_ms=duration,
                )
                return response

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(2 ** attempt, 10)  # Cap at 10s / 上限10秒
                    await asyncio.sleep(delay)

        self._update_status(
            health=ProviderHealth.UNAVAILABLE,
            error=str(last_exception),
        )
        raise last_exception  # type: ignore

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"model='{self.model}', api_base='{self.api_base}')"
        )


__all__ = ["BaseProvider", "ProviderStatus", "ProviderHealth", "LLMResponse"]
