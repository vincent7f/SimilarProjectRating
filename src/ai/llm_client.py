"""
Unified LLM Client - Central interface for all AI operations.

Provides a single entry point for interacting with any supported LLM backend
(Ollama, OpenAI, LiteLLM). Handles provider selection, automatic failover,
request routing, retry logic, and response normalization.

统一LLM客户端 - 所有AI操作的中央接口.
提供与任何支持的LLM后端(Ollama,OpenAI,LiteLLM)交互的单个入口点.
处理提供商选择,自动故障转移,请求路由,重试逻辑和响应标准化.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from src.ai.prompts import SYSTEM_PROMPT_BASE
from src.ai.providers.base import BaseProvider, LLMResponse, ProviderHealth
from src.utils.config import AIConfig, Config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Provider priority order (first tried first) / 提供商优先顺序(先尝试第一个)
PROVIDER_PRIORITY: List[str] = ["ollama", "openai", "litellm"]


class LLMClient:
    """Centralized LLM client with multi-provider support and auto-failover.

    Manages provider instances, routes requests to the best available backend,
    handles graceful degradation when primary providers fail, and provides
    a simple synchronous-style API over async internals.

    具有多提供商支持和自动故障转移的集中式LLM客户端.
管理提供商实例,将请求路由到最佳可用后端,
在主提供商失败时优雅降级,
并在异步内部之上提供简单的同步风格API.

    Attributes:
        config: AI configuration settings.
               AI配置设置.
        _providers: Dictionary mapping provider name -> initialized instance.
                   映射provider name->已初始化实例的字典.
        _active_provider: Currently selected provider for requests.
                         当前用于请求的选定提供商.
        _fallback_enabled: Whether to try alternate providers on failure.
                          失败时是否尝试备用提供商.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        ai_config: Optional[AIConfig] = None,
    ) -> None:
        """Initialize LLMClient with configuration.

        使用配置初始化LLMClient.

        Args:
            config: Full application config (used to extract ai section).
                   完整的应用配置(用于提取ai部分).
            ai_config: Direct AI configuration override (takes precedence).
                      直接AI配置覆盖(优先).
        """
        effective_ai_config = (
            ai_config
            or (config.ai if config else AIConfig())
        )
        self.config = effective_ai_config
        self._providers: Dict[str, BaseProvider] = {}
        self._active_provider: Optional[BaseProvider] = None
        self._fallback_enabled = effective_ai_config.fallback_enabled

    # ------------------------------------------------------------------
    # Provider Management / 提供商管理
    # ------------------------------------------------------------------

    def register_provider(self, provider: BaseProvider) -> None:
        """Register a provider instance for potential use.

        注册一个可能使用的提供商实例.

        Args:
            provider: Initialized provider instance to add.
                     要添加的已初始化提供商实例.
        """
        self._providers[provider.name.lower()] = provider
        logger.info(
                "Registered provider %s",
                provider.name,
                extra={
                    "module": "ai", 
                    "operation": "register_provider",
                    "params": {"name": provider.name}
                }
            )

        # Set as active if none set yet / 如果尚未设置则设为活跃
        if self._active_provider is None:
            self._active_provider = provider

    def set_active_provider(self, name: str) -> bool:
        """Manually select which provider to use for subsequent requests.

        手动选择后续请求要使用的提供商.

        Args:
            name: Provider name ('ollama', 'openai', 'litellm').
                 提供商名称('ollama','openai','litellm').

        Returns:
            True if provider found and activated, False otherwise.
             找到并激活提供商则返回True,否则返回False.
        """
        name_lower = name.lower()
        if name_lower in self._providers:
            self._active_provider = self._providers[name_lower]
            logger.info(
                "Set active provider to %s",
                name,
                extra={
                    "module": "ai", 
                    "operation": "set_active_provider",
                    "params": {"name": name}
                }
            )
            return True
        logger.warning(
                "Failed to set active provider to %s. Available: %s",
                name, list(self._providers.keys()),
                extra={
                    "module": "ai", 
                    "operation": "set_active_provider_failed",
                    "params": {"requested": name, "available": list(self._providers.keys())}
                }
            )
        return False

    def get_active_provider_name(self) -> str:
        """Return the currently active provider's name.

        返回当前活跃提供商的名称.

        Returns:
            Provider name string, or 'none' if no provider registered.
             提供商名字符串,如无注册提供商则返回'none'.
        """
        return self._active_provider.name if self._active_provider else "none"

    # ------------------------------------------------------------------
    # Core Generation Methods / 核心生成方法
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text using the active (or fallback) LLM provider.

        Uses the active provider by default. If fallback is enabled and the
        active provider fails, automatically tries alternative providers
        in priority order.

        使用活动(或后备)LLM提供商生成文本.
默认使用活动提供商.如果启用了后备且活动提供商失败,
自动按优先顺序尝试替代提供商.

        Args:
            prompt: The main user/task prompt text.
                   主要用户/任务提示文本.
            system_prompt: Optional system-level instruction prefix.
                          可选的系统级指令前缀.
            **kwargs: Additional parameters passed to provider.generate().
                     传递给provider.generate()的其他参数.

        Returns:
            Generated text string from the LLM.
             来自LLM的生成文本字符串.

        Raises:
            RuntimeError: If no providers available or all providers fail.
                         如无可用提供商或所有提供商失败则抛出.
        """
        if not self._active_provider:
            self._try_auto_discover_providers()
        if not self._active_provider:
            raise RuntimeError(
                "No LLM provider available. Please configure Ollama, "
                "OpenAI, or LiteLLM. No LLM provider available. "
                "请配置Ollama,OpenAI或LiteLLM."
            )

        effective_system = system_prompt or SYSTEM_PROMPT_BASE
        provider = self._active_provider

        try:
            logger.debug(
                "module=ai", operation="generate_start",
                params={
                    "provider": provider.name,
                    "model": provider.model,
                    "prompt_length": len(prompt),
                },
            )

            response: LLMResponse = await provider.generate(
                prompt=prompt,
                system_prompt=effective_system,
                **kwargs,
            )

            logger.info(
                "module=ai", operation="generate_complete",
                params={
                    "provider": response.provider_name,
                    "duration_ms": response.duration_ms,
                    "response_length": len(response.content),
                    "cached": response.is_cached,
                },
            )

            return response.content

        except Exception as e:
            logger.error(
                "module=ai", operation="generate_error",
                params={"provider": provider.name, "error": str(e)},
            )
            if self._fallback_enabled:
                fallback_resp = await self._try_fallback_generate(
                    prompt, effective_system, failed_provider=provider.name, **kwargs
                )
                return fallback_resp
            raise

    async def generate_structured(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate and parse structured JSON output from the LLM.

        Generates text then attempts to parse it as JSON, returning a parsed
        dictionary. Useful when prompts request JSON-formatted responses.

        生成并解析来自LLM的结构化JSON输出.
生成文本然后尝试将其解析为JSON,返回解析后的字典.
当提示请求JSON格式的响应时很有用.

        Args:
            prompt: The prompt requesting structured output.
                  请求结构化输出的提示.
            schema: Optional JSON schema hint for validation (not enforced).
                    用于验证的可选JSON schema提示(不强制执行).
            system_prompt: System instruction override.
                          系统指令覆盖.
            **kwargs: Additional parameters for the provider.
                     提供商的其他参数.

        Returns:
            Parsed dictionary from LLM JSON response.
             来自LLM JSON响应的解析字典.

        Raises:
            json.JSONDecodeError: If response is not valid JSON.
                                  如响应不是有效JSON则抛出.
        """
        raw_text = await self.generate(prompt, system_prompt=system_prompt, **kwargs)

        # Attempt to extract JSON from markdown code blocks / 尝试从Markdown代码块中提取JSON
        cleaned = raw_text.strip()

        if "```" in cleaned:
            import re
            json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(1).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(
                "module=ai", operation="parse_json_failed",
                params={"raw_length": len(raw_text), "truncated_preview": raw_text[:200]},
            )
            raise

    # ------------------------------------------------------------------
    # Fallback Logic / 后备逻辑
    # ------------------------------------------------------------------

    async def _try_fallback_generate(
        self,
        prompt: str,
        system_prompt: str,
        failed_provider: str,
        **kwargs: Any,
    ) -> str:
        """Attempt to fulfill request using fallback providers after primary failure.

        在主提供商失败后尝试使用后备提供商完成请求.

        Args:
            prompt: Original prompt text.
                  原始提示文本.
            system_prompt: System instruction used.
                         使用的系统指令.
            failed_provider: Name of the provider that just failed.
                           刚刚失败的提供商名称.
            **kwargs: Additional parameters.
                     其他参数.

        Returns:
            Text from successful fallback provider.
             来自成功后备提供商的文本.

        Raises:
            RuntimeError: If all providers fail.
                         所有提供商都失败时抛出.
        """
        logger.warning(
            "module=ai", operation="fallback_initiated",
            params={"failed_provider": failed_provider},
        )

        for provider_name in PROVIDER_PRIORITY:
            if provider_name == failed_provider:
                continue
            provider = self._providers.get(provider_name)
            if not provider or provider.status.health == ProviderHealth.UNAVAILABLE:
                continue

            try:
                logger.info(
                    "module=ai", operation="trying_fallback",
                    params={"fallback_provider": provider_name},
                )
                response = await provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    **kwargs,
                )
                self._active_provider = provider
                logger.info(
                    "module=ai", operation="fallback_success",
                    params={"new_active": provider_name},
                )
                return response.content

            except Exception as fb_err:
                logger.warning(
                    "module=ai", operation="fallback_failed",
                    params={"provider": provider_name, "error": str(fb_err)},
                )
                continue

        raise RuntimeError(
            f"All LLM providers failed. Primary: {failed_provider}. "
            f"所有LLM提供商都失败了.主提供商:{failed_provider}."
        )

    # ------------------------------------------------------------------
    # Status & Diagnostics / 状态与诊断
    # ------------------------------------------------------------------

    def get_provider_status(self) -> Dict[str, Any]:
        """Report status of all registered providers.

        报告所有注册提供商的状态.

        Returns:
            Dictionary with active provider info and per-provider status.
             包含活跃提供商信息和各提供商状态的字典.
        """
        statuses = {}
        for name, provider in self._providers.items():
            statuses[name] = {
                "health": provider.status.health.value,
                "model": provider.status.model,
                "latency_ms": provider.status.latency_ms,
                "error": provider.status.error,
            }

        return {
            "active": self.get_active_provider_name(),
            "fallback_enabled": self._fallback_enabled,
            "registered_providers": list(self._providers.keys()),
            "statuses": statuses,
        }

    async def check_all_health(self) -> Dict[str, Any]:
        """Run health checks against all registered providers.

        对所有注册提供商运行健康检查.

        Returns:
            Updated status dictionary after health checks.
             健康检查后的更新状态字典.
        """
        results = {}
        for name, provider in self._providers.items():
            try:
                status = await provider.check_health()
                results[name] = {
                    "health": status.health.value,
                    "latency_ms": status.latency_ms,
                    "error": status.error,
                }
            except Exception as e:
                results[name] = {"health": "unavailable", "error": str(e)}
        return results

    # ------------------------------------------------------------------
    # Auto-discovery / 自动发现
    # ------------------------------------------------------------------

    def _try_auto_discover_providers(self) -> None:
        """Attempt to instantiate default providers if none manually registered.

        如果没有手动注册,尝试实例化默认提供商.
        """
        if self._providers:
            return

        logger.info(
                "Auto-discovering providers",
                extra={
                    "module": "ai", 
                    "operation": "auto_discover_providers"
                }
            )

        # Import lazily to avoid circular deps / 延迟导入以避免循环依赖
        try:
            from src.ai.providers.ollama_provider import OllamaProvider
            ollama = OllamaProvider(
                model=self.config.model,
                api_base=self.config.api_base,
                timeout=self.config.request_timeout,
            )
            self.register_provider(ollama)
        except Exception as e:
            logger.warning(
                "Failed to auto-discover Ollama provider: %s",
                str(e),
                extra={
                    "module": "ai", 
                    "operation": "auto_discover_ollama_failed",
                    "params": {"error": str(e)}
                }
            )


__all__ = ["LLMClient"]
