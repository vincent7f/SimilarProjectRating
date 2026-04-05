"""
GitReverse.com API Client.

Provides async HTTP methods for interacting with GitReverse.com API,
which generates textual project prompts from GitHub repository URLs.

GitReverse.com API客户端.
提供与GitReverse.com API交互的异步HTTP方法,
该API从GitHub仓库URL生成文本化项目prompt.

GitReverse format: https://gitreverse.com/{owner}/{repo}
Example: https://github.com/nearai/ironclaw -> https://gitreverse.com/nearai/ironclaw
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from src.models.repository import Repository
from src.utils.config import GitReverseConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GitReverseClient:
    """Async GitReverse.com HTTP client.

    Handles all interactions with GitReverse.com API including fetching
    project prompts, caching responses, and error handling.

    GitReverse.com异步HTTP客户端.
    处理与GitReverse.com API的所有交互,包括获取项目prompt,
    缓存响应和错误处理.

    Attributes:
        config: GitReverse service configuration.
                GitReverse服务配置.
        _client: HTTPX async client instance.
                 HTTPX异步客户端实例.
        _cache: In-memory prompt cache dictionary.
                内存中prompt缓存字典.
    """

    def __init__(self, config: Optional[GitReverseConfig] = None) -> None:
        self.config = config or GitReverseConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Request headers
        self._headers: Dict[str, str] = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 SimilarProjectRating/0.1.0",
            "Cache-Control": "no-cache",
        }

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy initialize HTTPX client.

        延迟初始化HTTPX客户端."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers=self._headers,
                follow_redirects=True,
            )
        return self._client

    def _get_cache_key(self, repo_full_name: str) -> str:
        """Generate cache key for repository.

        为仓库生成缓存键."""
        return f"gitreverse::{repo_full_name}"

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Retrieve prompt from cache if not expired.

        如果未过期,从缓存中检索prompt."""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            # Check if cache entry is still valid
            if time.time() < entry.get("expires_at", 0):
                logger.debug(
                    "module=search", operation="gitreverse_cache_hit",
                    params={"repo": cache_key.split("::")[1]},
                )
                return entry.get("prompt")
            else:
                # Cache expired, remove it
                del self._cache[cache_key]
        return None

    def _save_to_cache(self, cache_key: str, prompt: str) -> None:
        """Save prompt to cache with expiration.

        将prompt保存到缓存中并设置过期时间."""
        self._cache[cache_key] = {
            "prompt": prompt,
            "expires_at": time.time() + self.config.cache_duration_seconds,
            "cached_at": time.time(),
        }

    def _github_url_to_gitreverse_url(self, repo_full_name: str) -> str:
        """Convert GitHub URL to GitReverse URL.

        将GitHub URL转换为GitReverse URL.

        Args:
            repo_full_name: Repository full name (owner/repo).
                            仓库完整名称(所有者/仓库).

        Returns:
            GitReverse.com URL for the repository.
            仓库的GitReverse.com URL.
        """
        # Extract owner and repo name
        if "/" not in repo_full_name:
            raise ValueError(f"Invalid repo name format: {repo_full_name}")

        owner, repo = repo_full_name.split("/", 1)
        # Remove .git suffix if present
        repo = repo.replace(".git", "")
        
        return f"{self.config.base_url.rstrip('/')}/{owner}/{repo}"

    async def get_project_prompt(self, repository: Repository) -> Optional[str]:
        """Fetch textual project description from GitReverse.com.

        从GitReverse.com获取文本化项目描述.

        Args:
            repository: Repository metadata.
                        仓库元数据.

        Returns:
            Project prompt text or None if not available.
            项目prompt文本,如果不可用则返回None.
        """
        if not self.config.enabled:
            logger.debug(
                "module=search", operation="gitreverse_disabled",
                params={"repo": repository.full_name},
            )
            return None

        # Check cache first
        cache_key = self._get_cache_key(repository.full_name)
        cached_prompt = self._get_from_cache(cache_key)
        if cached_prompt:
            logger.info(
                "module=search", operation="gitreverse_prompt_cached",
                params={"repo": repository.full_name, "cache_key": cache_key},
            )
            return cached_prompt

        # Not in cache, fetch from GitReverse.com
        gitreverse_url = self._github_url_to_gitreverse_url(repository.full_name)
        
        logger.info(
            "module=search", operation="gitreverse_request_start",
            params={"repo": repository.full_name, "url": gitreverse_url},
        )

        retry_count = 0
        while retry_count <= self.config.max_retries:
            try:
                start_time = time.time()
                
                # Make HTTP request to GitReverse.com
                response = await self.client.get(gitreverse_url, follow_redirects=True)
                
                # Check response status
                if response.status_code == 200:
                    # Parse the HTML response to extract prompt
                    # GitReverse seems to display the prompt directly in the page
                    prompt_html = response.text
                    
                    # Extract the main content
                    prompt_text = self._extract_prompt_from_html(prompt_html)
                    
                    if prompt_text:
                        # Save to cache
                        self._save_to_cache(cache_key, prompt_text)
                        
                        duration = int((time.time() - start_time) * 1000)
                        logger.info(
                            "module=search", operation="gitreverse_request_success",
                            params={
                                "repo": repository.full_name,
                                "duration_ms": duration,
                                "prompt_length": len(prompt_text),
                            },
                        )
                        return prompt_text
                    else:
                        logger.warning(
                            "module=search", operation="gitreverse_parse_error",
                            params={"repo": repository.full_name, "status": response.status_code},
                        )
                        break  # Can't parse, exit retry loop
                        
                elif response.status_code == 404:
                    logger.warning(
                        "module=search", operation="gitreverse_not_found",
                        params={"repo": repository.full_name, "url": gitreverse_url},
                    )
                    break  # Project not found on GitReverse, no point retrying
                    
                elif response.status_code in [429, 503]:
                    # Rate limited or service unavailable
                    retry_delay = min(30, (retry_count + 1) * 5)
                    logger.warning(
                        "module=search", operation="gitreverse_rate_limited",
                        params={
                            "repo": repository.full_name,
                            "status": response.status_code,
                            "retry_count": retry_count + 1,
                            "retry_delay": retry_delay,
                        },
                    )
                    await asyncio.sleep(retry_delay)
                    retry_count += 1
                    continue
                    
                else:
                    logger.warning(
                        "module=search", operation="gitreverse_error",
                        params={
                            "repo": repository.full_name,
                            "status": response.status_code,
                            "retry_count": retry_count + 1,
                        },
                    )
                    retry_count += 1
                    if retry_count <= self.config.max_retries:
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    continue
                    
            except httpx.TimeoutException:
                logger.warning(
                    "module=search", operation="gitreverse_timeout",
                    params={
                        "repo": repository.full_name,
                        "retry_count": retry_count + 1,
                        "timeout": self.config.timeout_seconds,
                    },
                )
                retry_count += 1
                if retry_count <= self.config.max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                continue
                
            except Exception as e:
                logger.error(
                    "module=search", operation="gitreverse_exception",
                    params={
                        "repo": repository.full_name,
                        "error": str(e),
                        "retry_count": retry_count + 1,
                    },
                )
                retry_count += 1
                if retry_count <= self.config.max_retries:
                    await asyncio.sleep(2 ** retry_count)
                continue

        # All retries failed
        logger.error(
            "module=search", operation="gitreverse_failed",
            params={
                "repo": repository.full_name,
                "max_retries": self.config.max_retries,
                "fallback": self.config.fallback_to_code,
            },
        )
        return None

    def _extract_prompt_from_html(self, html_content: str) -> str:
        """Extract prompt text from GitReverse.com HTML response.

        从GitReverse.com HTML响应中提取prompt文本.

        Args:
            html_content: Raw HTML from GitReverse.com.
                          来自GitReverse.com的原始HTML.

        Returns:
            Extracted prompt text or empty string if not found.
            提取的prompt文本,如果未找到则返回空字符串.
        """
        # Simple HTML parsing to extract text content
        # GitReverse likely presents the prompt in a structured format
        # We'll try several approaches
        
        prompt_parts = []
        
        # Approach 1: Look for <main>, <article>, or <div> with class containing "prompt", "description", "content"
        import re
        
        # Pattern for main content divs
        content_patterns = [
            r'<main[^>]*>(.*?)</main>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*(prompt|description|content|text|markdown)[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*id="[^"]*(main|content|prompt)[^"]*"[^>]*>(.*?)</div>',
        ]
        
        for pattern in content_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Extract text from match
                matched_text = match if isinstance(match, str) else match[-1]
                # Clean HTML tags
                clean_text = re.sub(r'<[^>]+>', ' ', matched_text)
                # Normalize whitespace
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                if clean_text and len(clean_text) > 100:  # Reasonable minimum length
                    prompt_parts.append(clean_text)
        
        # Approach 2: Extract all text and take the largest contiguous block
        if not prompt_parts:
            # Remove scripts and styles
            clean_html = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove remaining HTML tags
            text_only = re.sub(r'<[^>]+>', '\n', clean_html)
            
            # Split into lines and find the longest paragraph
            lines = text_only.split('\n')
            lines = [line.strip() for line in lines if line.strip()]
            
            if lines:
                # Find the longest line/paragraph
                longest_line = max(lines, key=len)
                if len(longest_line) > 200:  # Must be substantial content
                    prompt_parts.append(longest_line)
        
        # Combine all found parts
        if prompt_parts:
            combined = '\n\n'.join(prompt_parts)
            # Limit length to avoid huge prompts
            if len(combined) > 10000:
                combined = combined[:10000] + "... [prompt truncated]"
            return combined
        
        return ""  # No prompt found

    async def close(self) -> None:
        """Close HTTP client connection.

        关闭HTTP客户端连接."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def get_gitreverse_prompt_for_repo(
    repository: Repository, 
    config: Optional[GitReverseConfig] = None
) -> Optional[str]:
    """Convenience function to get prompt for a single repository.

    获取单个仓库prompt的便捷函数.

    Args:
        repository: Repository object.
                    仓库对象.
        config: Optional GitReverse configuration.
                可选的GitReverse配置.

    Returns:
        Prompt text or None.
        Prompt文本或None.
    """
    async with GitReverseClient(config) as client:
        return await client.get_project_prompt(repository)


__all__ = ["GitReverseClient", "get_gitreverse_prompt_for_repo"]