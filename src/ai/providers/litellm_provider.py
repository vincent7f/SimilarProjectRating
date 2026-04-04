"""
LiteLLM Provider - Unified LLM Routing Adapter.

Implements the BaseProvider interface through LiteLLM library which provides
a unified interface to 100+ LLM providers (OpenAI, Anthropic, Cohere, HuggingFace,
local models, etc.) with automatic routing, retry, fallback, and load balancing.

LiteLLM提供商 - 统一LLM路由适配器。
通过LiteLLM库实现BaseProvider接口，LiteLLM提供对100+个LLM提供商的统一接口
（OpenAI、Anthropic、Cohere、HuggingFace、本地模型等），具有自动路由、重试、故障转移和负载均衡。
"""

from __future__ import annotations

import json
from typing import Any, Optional

from src.ai.providers.base import (
    BaseProvider,
    LLMResponse,
    ProviderHealth,
    ProviderStatus,
)


class LiteLLMProvider(BaseProvider):
    """LiteLLM unified routing provider implementation.

    Uses the litellm library as a universal translation layer, allowing seamless
    switching between providers without changing application code. Requires
    the 'litellm' package to be installed.

    LiteLLM统一路由提供商实现。
使用litellm库作为通用翻译层，允许在不更改应用程序代码的情况下
在提供商之间无缝切换。需要安装'litellm'包。
    """

    def __init__(
        self,
        model: str = "openai/gpt-4",
        api_base: str = "",
        api_key: str = "",
        timeout: int = 120,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize LiteLLM provider with routing configuration.

        使用路由配置初始化LiteLLM提供商。

        Args:
            model: LiteLLM model string format (e.g., 'openai/gpt-4',
                  'anthropic/claude-3', 'ollama/llama3').
                  LiteLLM模型字符串格式（例如'openai/gpt-4'、
                  'anthropic/claude-3'、'ollama/llama3'）。
            api_base: Custom base URL (optional, often not needed with LiteLLM).
                     自定义基础URL（可选，通常LiteLLM不需要）。
            api_key: API key (can also use env vars like OPENAI_API_KEY).
                    API密钥（也可以使用OPENAI_API_KEY等环境变量）。
            **kwargs: Additional BaseProvider parameters.
                     其他BaseProvider参数。
        """
        super().__init__(
            name="LiteLLM",
            model=model,
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._status.supports_streaming = True
        self._status.supports_structured_output = True

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text via LiteLLM completion function.

        通过LiteLLM补全函数生成文本。

        Args:
            prompt: User prompt.
                  用户提示。
            system_prompt: System instruction (passed as first message).
                         系统指令（作为第一条消息传递）。
            **kwargs: Override parameters.
                     覆盖参数。

        Returns:
            Normalized LLMResponse.
             标准化的LLMResponse。
        """
        try:
            import litellm
        except ImportError:
            raise ImportError(
                "litellm package is required for LiteLLMProvider. "
                "Install with: pip install litellm. "
                "LiteLLMProvider需要litellm包。使用pip install litellm安装。"
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Configure optional env vars / 配置可选环境变量
        if self.api_key and "OPENAI_API_KEY" not in __import__("os").environ:
            # Set key per-request if needed / 如需要则每次请求设置密钥
            pass

        import time

        start = time.time()

        response = await litellm.acompletion(
            model=kwargs.get("model", self.model),
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            timeout=self.timeout,
        )

        duration_ms = int((time.time() - start) * 1000)
        choice = response.choices[0]

        self._update_status(latency_ms=duration_ms)

        return LLMResponse(
            content=choice.message.content or "",
            raw_response=response.model_dump() if hasattr(response, "model_dump") else str(response),  # type: ignore
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,  # type: ignore
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,  # type: ignore
                "total_tokens": response.usage.total_tokens if response.usage else 0,  # type: ignore
            },
            provider_name="litellm",
            duration_ms=duration_ms,
        )

    async def check_health(self) -> ProviderStatus:
        """Verify LiteLLM installation and basic connectivity.

        验证LiteLLM安装和基本连接性。

        Returns:
            Updated ProviderStatus.
             更新后的ProviderStatus。
        """
        try:
            import litellm

            # Quick test with minimal call / 最小调用快速测试
            test_response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                timeout=10,
            )
            self._update_status(health=ProviderHealth.HEALTHY)

        except ImportError:
            self._update_status(
                health=ProviderHealth.UNAVAILABLE,
                error="litellm package not installed",
            )
        except Exception as e:
            self._update_status(
                health=ProviderHealth.DEGRADED,
                error=str(e),
            )

        return self._status


__all__ = ["LiteLLMProvider"]
