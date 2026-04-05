"""
OpenAI Provider - OpenAI-Compatible API Backend Adapter.

Implements the BaseProvider interface for any API compatible with OpenAI's
chat completions format. Supports OpenAI itself, Azure OpenAI, and many
other providers that expose an OpenAI-compatible endpoint.

OpenAI提供商 - OpenAI兼容API后端适配器.
为与OpenAI聊天补全格式兼容的任何API实现BaseProvider接口.
支持OpenAI本身,Azure OpenAI以及许多其他暴露OpenAI兼容端点的提供商.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from src.ai.providers.base import (
    BaseProvider,
    LLMResponse,
    ProviderHealth,
    ProviderStatus,
)


class OpenAIProvider(BaseProvider):
    """OpenAI-compatible API provider implementation.

    Connects to any service exposing the /v1/chat/completions endpoint
    following OpenAI's request/response format. Works with OpenAI,
    DeepSeek, Together AI, Groq, local vLLM/OLLAMA with compat mode, etc.

    OpenAI兼容API提供商实现.
连接到遵循OpenAI请求/响应格式暴露/v1/chat/completions端点的任何服务.
适用于OpenAI,DeepSeek,Together AI,Groq,带兼容模式的本地vLLM/Ollama等.
    """

    def __init__(
        self,
        model: str = "gpt-4",
        api_base: str = "https://api.openai.com/v1",
        api_key: str = "",
        timeout: int = 120,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize OpenAI-compatible provider.

        初始化OpenAI兼容提供商.

        Args:
            model: Model identifier string (e.g., 'gpt-4', 'deepseek-chat').
                   模型标识符字符串(例如'gpt-4','deepseek-chat').
            api_base: Base URL for the chat completions API.
                     聊天补全API的基础URL.
            api_key: Authentication API key.
                   认证API密钥.
            **kwargs: Additional BaseProvider parameters.
                     其他BaseProvider参数.
        """
        super().__init__(
            name="OpenAI",
            model=model,
            api_base=api_base.rstrip("/"),
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Ensure URL ends with /v1 or similar / 确保URL以/v1或类似结尾
        if not self.api_base.endswith("/v1") and not self.api_base.endswith("/chat"):
            self.api_base = f"{self.api_base}/v1"
        self._status.supports_streaming = True
        self._status.supports_structured_output = True

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text via OpenAI-compatible /chat/completions endpoint.

        通过OpenAI兼容的/chat/completions端点生成文本.

        Args:
            prompt: The user message text.
                  用户消息文本.
            system_prompt: Optional system message.
                         可选系统消息.
            **kwargs: Override generation parameters.
                     覆盖生成参数.

        Returns:
            Normalized LLMResponse.
             标准化的LLMResponse.
        """
        url = f"{self.api_base}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        return LLMResponse(
            content=message.get("content", ""),
            raw_response=data,
            finish_reason=choice.get("finish_reason", "stop"),
            usage={
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0),
            },
            provider_name="openai",
        )

    async def check_health(self) -> ProviderStatus:
        """Verify OpenAI API accessibility and key validity.

        验证OpenAI API可访问性和密钥有效性.

        Returns:
            Updated ProviderStatus.
             更新后的ProviderStatus.
        """
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.api_base}/models", headers=headers)

            if resp.status_code == 200:
                self._update_status(
                    health=ProviderHealth.HEALTHY,
                    latency_ms=int(resp.elapsed.total_seconds() * 1000),
                )
            elif resp.status_code == 401:
                self._update_status(
                    health=ProviderHealth.UNAVAILABLE,
                    error="Invalid API key (401 Unauthorized)",
                )
            else:
                self._update_status(
                    health=ProviderHealth.DEGRADED,
                    error=f"API returned status {resp.status_code}",
                )

        except Exception as e:
            self._update_status(
                health=ProviderHealth.UNAVAILABLE,
                error=str(e),
            )

        return self._status


__all__ = ["OpenAIProvider"]
