"""
Pytest Configuration and Shared Fixtures.

Provides mock clients, sample data, and common test utilities
used across all unit and integration test modules.

pytest配置和共享Fixture。
提供在所有单元测试和集成测试模块中使用的
模拟客户端、示例数据和通用测试工具。
"""

import os
import sys
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure src package is importable / 确保src包可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ---------------------------------------------------------------------------
# GitHub Client Mock Fixture / GitHub客户端模拟Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_github_client() -> MagicMock:
    """Create a mocked GitHubClient with predefined responses.

    Returns a MagicMock configured to simulate typical GitHub API responses
    for repository search, metadata retrieval, and release queries.

    创建具有预定义响应的模拟GitHubClient。
返回一个MagicMock，用于模拟仓库搜索、元数据获取和发布查询的典型GitHub API响应。

    Yields:
        Configured MagicMock mimicking GitHubClient.
        模拟GitHubClient的已配置MagicMock。
    """
    client = MagicMock()
    client.search_repositories = AsyncMock(return_value=[])
    client.get_repository = AsyncMock()
    client.get_latest_release = AsyncMock(return_value=None)
    client.get_repo_archive_url = AsyncMock()
    client.get_community_metrics = AsyncMock()
    client.check_rate_limit = MagicMock(
        return_value=MagicMock(remaining=5000, reset_time=0)
    )
    yield client


# ---------------------------------------------------------------------------
# LLM Client Mock Fixture / LLM客户端模拟Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mocked LLMClient with predefined responses.

    Returns a MagicMock that simulates LLM responses for keyword generation,
    relevance judgment, recommendation, and explanation generation tasks.

    创建具有预定义响应的模拟LLM客户端。
返回一个MagicMock，用于模拟关键词生成、相关性判断、推荐
和解释生成任务的LLM响应。

    Yields:
        Configured MagicMock mimicking LLMClient.
        模拟LLMClient的已配置MagicMock。
    """
    client = MagicMock()
    client.generate = AsyncMock(
        return_value='{"keywords": ["test keyword"]}'
    )
    client.generate_structured = AsyncMock(return_value={})
    client.get_provider_status = MagicMock()
    yield client


# ---------------------------------------------------------------------------
# Sample Repository Data Fixture / 示例仓库数据Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_repository() -> dict:
    """Provide sample repository data for testing.

    Returns a dictionary representing a typical GitHub repository's
    metadata as returned by the GitHub REST API.

    提供用于测试的示例仓库数据。
返回表示典型GitHub仓库元数据的字典（如GitHub REST API返回）。

    Returns:
        Dictionary with repository fields populated with realistic test values.
        填充了真实测试值的仓库字段字典。
    """
    return {
        "id": 123456789,
        "name": "awesome-project",
        "full_name": "owner/awesome-project",
        "description": "An awesome open-source project for demonstration purposes",
        "url": "https://github.com/owner/awesome-project",
        "html_url": "https://github.com/owner/awesome-project",
        "stars": 1500,
        "forks": 320,
        "open_issues": 15,
        "language": "Python",
        "topics": ["python", "awesome", "opensource"],
        "created_at": "2023-01-15T10:30:00Z",
        "updated_at": "2024-06-01T08:00:00Z",
        "pushed_at": "2024-05-28T14:22:00Z",
        "default_branch": "main",
        "license": {"spdx_id": "MIT"},
    }


# ---------------------------------------------------------------------------
# Temporary Directory Fixture / 临时目录Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_data_dir(tmp_path) -> Generator[str, None, None]:
    """Create a temporary directory structure mirroring the data/ layout.

    Creates and yields a temporary path with cache/ and results/
    subdirectories, cleaned up automatically after each test.

    创建镜像data/目录结构的临时目录路径。
创建并生成带有cache/和results/子目录的临时路径，每次测试后自动清理。

    Yields:
        Path string to the temporary data directory.
        临时数据目录的路径字符串。
    """
    cache_dir = tmp_path / "cache"
    results_dir = tmp_path / "results"
    cache_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)
    yield str(tmp_path)


# ---------------------------------------------------------------------------
# CLI Arguments Fixture / CLI参数Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_cli_args() -> argparse.Namespace:
    """Provide sample parsed CLI arguments for testing.

    Returns a Namespace with typical command-line argument values
    used in pipeline execution tests.

    提供用于测试的示例解析CLI参数。
返回包含流水线执行测试中使用的典型命令行参数值的Namespace。

    Returns:
        Namespace with sample argument values.
        包含示例参数值的Namespace。
    """
    import argparse

    return argparse.Namespace(
        query="project management tool",
        config=None,
        max_projects=20,
        output="./data/results/",
        provider=None,
        model=None,
        verbose=False,
        no_cache=False,
        dry_run=False,
    )
