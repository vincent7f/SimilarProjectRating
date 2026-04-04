"""
AI Integration Module - LLM-powered intelligence layer.

Provides unified LLM client interface with Ollama (primary),
OpenAI-compatible APIs (fallback), and LiteLLM (routing) support.
Also includes recommendation and explanation generation capabilities.

AI集成模块 - LLM驱动的智能层。
提供统一的LLM客户端接口，支持Ollama（首选）、OpenAI兼容API（备选）
和LiteLLM（路由）后端。同时包含推荐和解释生成能力。
"""

from src.ai.llm_client import LLMClient
from src.ai.recommender import Recommender
from src.ai.explainer import Explainer

__all__ = [
    "LLMClient",
    "Recommender",
    "Explainer",
]
