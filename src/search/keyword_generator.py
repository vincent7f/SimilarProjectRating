"""
AI-Powered Keyword Generator.

Uses LLM to generate multiple optimized GitHub search keyword groups
from a user's natural language query, targeting different aspects
(functionality, tech stack, use case, implementation).

AI驱动的关键词生成器。
使用LLM从用户自然语言查询生成多组优化的GitHub搜索关键词，
针对不同方面（功能、技术栈、用例、实现方式）。
"""

from __future__ import annotations

import json
from typing import List, Optional

from src.ai.llm_client import LLMClient
from src.ai.prompts import build_keyword_prompt, KEYWORD_GENERATION_PROMPT
from src.models.search import KeywordGroup, SearchQuery
from src.utils.logger import get_logger

logger = get_logger(__name__)


class KeywordGenerator:
    """Generates GitHub-optimized search keywords using AI.

    Takes a user's natural language description of what they're looking for,
    consults the LLM to produce 3-5 keyword groups that cover different search
    angles, and returns them ready for GitHub API consumption.

    使用AI生成GitHub优化搜索的关键词生成器。
接收用户对所需内容的自然语言描述，咨询LLM生成3-5个覆盖不同搜索角度的
关键词组，并返回它们以供GitHub API使用。

    Attributes:
        llm_client: LLM client for generation.
                   用于生成的LLM客户端。
        num_groups: Number of keyword groups to generate per request.
                   每次请求生成的关键词组数量。
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        num_groups: int = 5,
    ) -> None:
        self.llm_client = llm_client
        self.num_groups = num_groups

    async def generate(
        self,
        query: str,
        language_hint: Optional[str] = None,
        num_groups: Optional[int] = None,
    ) -> List[KeywordGroup]:
        """Generate search keyword groups from a user query.

        从用户查询生成搜索关键词组。

        Args:
            query: Natural language description of desired functionality.
                  对所需功能的自然语言描述。
            language_hint: Optional preferred programming language hint.
                         可选的首选编程语言提示。
            num_groups: Override default number of groups to generate.
                       覆盖默认的要生成的组数量。

        Returns:
            List of KeywordGroup objects with primary, extensions, category.
             包含primary、extensions、category的KeywordGroup对象列表。
        """
        if not self.llm_client:
            raise RuntimeError("LLMClient required for KeywordGeneration.")

        effective_num = num_groups or self.num_groups

        prompt = build_keyword_prompt(
            user_query=query,
            num_groups=effective_num,
        )

        logger.info(
            "module=search", operation="keyword_generation_start",
            params={"query": query, "num_groups": effective_num},
        )

        try:
            raw_response = await self.llm_client.generate(prompt)
            result = json.loads(raw_response)

            if not isinstance(result, list):
                logger.warning(
                    "module=search", operation="keyword_parse_not_list",
                    params={"type": type(result).__name__},
                )
                return []

            groups: List[KeywordGroup] = []
            for item in result[:effective_num]:
                if not isinstance(item, dict):
                    continue

                group = KeywordGroup(
                    primary=item.get("primary", ""),
                    extensions=item.get("extensions", []),
                    language=language_hint or item.get("language"),
                    category=item.get("category", "general"),
                    rationale=item.get("rationale", ""),
                )

                # Validate minimum requirements / 验证最低要求
                if group.primary:
                    groups.append(group)
                else:
                    logger.warning(
                        "module=search",
                        operation="skipping_empty_keyword_group",
                        params={"item": str(item)[:100]},
                    )

            logger.info(
                "module=search", operation="keyword_generation_complete",
                params={
                    "query": query,
                    "groups_generated": len(groups),
                    "group_names": [g.primary for g in groups],
                },
            )
            return groups

        except json.JSONDecodeError as e:
            logger.error(
                "module=search", operation="keyword_json_parse_error",
                params={
                    "error": str(e),
                    "raw_preview": raw_response[:200] if 'raw_response' in dir() else "",
                },
            )
            # Fallback: create single group from query / 后备：从查询创建单个组
            return [
                KeywordGroup(
                    primary=query,
                    language=language_hint,
                    category="fallback",
                    rationale="JSON parse failed; used raw query as fallback.",
                )
            ]

        except Exception as e:
            logger.error(
                "module=search", operation="keyword_generation_error",
                params={"error": str(e), "query": query},
            )
            raise

    async def generate_search_queries(
        self,
        query: str,
        **kwargs: Any,
    ) -> List[str]:
        """Generate formatted GitHub search query strings.

        生成格式化的GitHub搜索查询字符串。

        Args:
            query: User input.
                  用户输入。
            **kwargs: Passed through to generate().
                     传递给generate()。

        Returns:
            List of query strings ready for GitHub API /search/repositories.
             准备好用于GitHub API /search/repositories的查询字符串列表。
        """
        groups = await self.generate(query, **kwargs)
        return [g.build_search_query() for g in groups]


__all__ = ["KeywordGenerator"]
