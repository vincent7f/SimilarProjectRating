"""
Ollama Provider - Local LLM Backend Adapter.

Implements the BaseProvider interface for Ollama, a local LLM runtime that
runs models on the user's machine. This is the primary (preferred) backend
for privacy-preserving and cost-free AI operations.

Ollama提供商 - 本地LLM后端适配器。
为Ollama实现BaseProvider接口，Ollama是在用户机器上运行模型的本地LLM运行时。
这是用于保护隐私和免费AI操作的主要（首选）后端。
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from src.ai.providers.base import BaseProvider, LLMResponse, ProviderHealth, ProviderStatus


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider implementation.

    Connects to a locally running Ollama instance (default: localhost:11434)
    to generate text completions using models like llama3, mistral, codellama.

    Ollama本地LLM提供商实现。
连接到本地运行的Ollama实例（默认：localhost:11434），
使用llama3、mistral、codellama等模型生成文本补全。

    Attributes:
        Inherits all attributes from BaseProvider.
         继承BaseProvider的所有属性。
    """

    def __init__(
        self,
        model: str = "gemma4:26b-a4b-it-q4_K_M",
        api_base: str = "http://localhost:11434",
        api_key: str = "",
        timeout: int = 120,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize Ollama provider with connection settings.

        使用连接设置初始化Ollama提供商。

        Args:
            model: Ollama model name (e.g., 'llama3.2:latest', 'mistral:7b').
                  Ollama模型名称（例如'llama3.2:latest'、'mistral:7b'）。
            api_base: Ollama server base URL.
                      Ollama服务器基础URL。
            api_key: Not used by Ollama but kept for interface consistency.
                    Ollama不使用但为接口一致性保留。
            timeout: HTTP request timeout seconds.
                    HTTP请求超时秒数。
            **kwargs: Additional BaseProvider parameters.
                     其他BaseProvider参数。
        """
        super().__init__(
            name="Ollama",
            model=model,
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._status.supports_streaming = True
        self._status.supports_structured_output = False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text using the Ollama /api/generate endpoint.

        使用Ollama /api/generate端点生成文本。

        Args:
            prompt: User prompt text.
                  用户提示文本。
            system_prompt: Optional system instruction.
                          可选系统指令。
            **kwargs: Override parameters (temperature, etc.).
                     覆盖参数（temperature等）。

        Returns:
            Normalized LLMResponse.
             标准化的LLMResponse。
        """
        url = f"{self.api_base}/api/generate"

        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data.get("response", "")
        return LLMResponse(
            content=content,
            raw_response=data,
            finish_reason=data.get("done_reason", "stop"),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": (
                    data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                ),
            },
            provider_name="ollama",
        )

    async def check_health(self) -> ProviderStatus:
        """Check if Ollama server is reachable and responsive.

        检查Ollama服务器是否可达且响应。

        Returns:
            Updated ProviderStatus with health assessment.
             包含健康评估的更新后ProviderStatus。
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.api_base}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    available_model_names = [m["name"] for m in models]
                    is_available = any(
                        self.model in m for m in available_model_names
                    )
                    self._update_status(
                        health=ProviderHealth.HEALTHY if is_available else ProviderHealth.DEGRADED,
                        latency_ms=int(resp.elapsed.total_seconds() * 1000),
                    )
                else:
                    self._update_status(health=ProviderHealth.UNAVAILABLE)

        except Exception as e:
            self._update_status(
                health=ProviderHealth.UNAVAILABLE,
                error=str(e),
            )

        return self._status


__all__ = ["OllamaProvider"]
