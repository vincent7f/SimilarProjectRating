"""
Search Module - GitHub project discovery and filtering.

Provides AI-powered keyword generation, GitHub API client,
and relevance-based project filtering capabilities.

搜索模块 - GitHub项目发现与过滤。
提供AI驱动的关键词生成、GitHub API客户端
以及基于相关性的项目过滤功能。
"""

from src.search.github_client import GitHubClient
from src.search.keyword_generator import KeywordGenerator
from src.search.project_filter import ProjectFilter

__all__ = ["GitHubClient", "KeywordGenerator", "ProjectFilter"]
