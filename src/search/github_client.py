"""
GitHub REST API v3 Client.

Provides async HTTP methods for interacting with the GitHub API, including
repository search, metadata retrieval, release information, archive URLs,
community metrics, and rate limit management.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.models.repository import Repository, Release, _parse_datetime
from src.utils.config import GitHubConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitStatus:
    """Current GitHub API rate limit status."""

    remaining: int = 0
    reset_time: int = 0
    limit: int = 60
    used: int = 0

    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= 0

    @property
    def seconds_until_reset(self) -> int:
        now = int(time.time())
        return max(0, self.reset_time - now)


class GitHubClient:
    """Async GitHub REST API v3 client.

    Handles all interactions with GitHub's REST API including search,
    repository details, releases, and community metrics. Implements
    automatic rate limit handling with queue-wait logic.
    """

    BASE_URL: str = "https://api.github.com"

    def __init__(self, config: Optional[GitHubConfig] = None) -> None:
        self.config = config or GitHubConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit = RateLimitStatus(
            limit=self.config.rate_limit,
            remaining=self.config.rate_limit,
        )
        self._headers: Dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SimilarProjectRating/0.1.0",
        }
        if self.config.is_authenticated:
            self._headers["Authorization"] = f"token {self.config.api_token}"

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers=self._headers,
                follow_redirects=True,
            )
        return self._client

    # ------------------------------------------------------------------
    # Rate Limit Management
    # ------------------------------------------------------------------

    async def check_rate_limit(self) -> RateLimitStatus:
        try:
            resp = await self.client.get(f"{self.BASE_URL}/rate_limit")
            data = resp.json().get("resources", {}).get("core", {})
            self._rate_limit = RateLimitStatus(
                remaining=data.get("remaining", 0),
                reset_time=data.get("reset", 0),
                limit=data.get("limit", self.config.rate_limit),
                used=(data.get("limit", self.config.rate_limit)
                      - data.get("remaining", 0)),
            )
        except Exception as e:
            logger.warning(
                "module=search", operation="check_rate_limit_failed",
                params={"error": str(e)},
            )
        return self._rate_limit

    async def _wait_if_needed(self) -> None:
        if self._rate_limit.remaining < 5 and self._rate_limit.seconds_until_reset > 0:
            wait = self._rate_limit.seconds_until_reset + 2
            logger.warning(
                "module=search", operation="rate_limit_wait",
                params={"wait_seconds": wait},
            )
            await asyncio.sleep(wait)
            await self.check_rate_limit()

    def _update_rate_from_response(self, response: httpx.Response) -> None:
        if "X-RateLimit-Remaining" in response.headers:
            self._rate_limit = RateLimitStatus(
                remaining=int(response.headers["X-RateLimit-Remaining"]),
                reset_time=int(response.headers["X-RateLimit-Reset"]),
                limit=int(response.headers["X-RateLimit-Limit"]),
                used=self._rate_limit.limit
                     - int(response.headers["X-RateLimit-Remaining"]),
            )

    # ------------------------------------------------------------------
    # Repository Search
    # ------------------------------------------------------------------

    async def search_repositories(
        self,
        query: str,
        per_page: int = 30,
        max_results: int = 50,
        sort: str = "stars",
        order: str = "desc",
    ) -> List[Repository]:
        await self._wait_if_needed()

        all_repos: List[Repository] = []
        page = 1
        per_page = min(per_page, 100)

        while len(all_repos) < max_results:
            try:
                resp = await self.client.get(
                    f"{self.BASE_URL}/search/repositories",
                    params={
                        "q": query,
                        "per_page": per_page,
                        "page": page,
                        "sort": sort,
                        "order": order,
                    },
                )
                self._update_rate_from_response(resp)
                resp.raise_for_status()

                data = resp.json()
                items = data.get("items", [])

                for item in items:
                    repo = Repository.from_api_response(item)
                    all_repos.append(repo)

                total_count = data.get("total_count", 0)
                logger.debug(
                    "module=search", operation="github_search",
                    params={
                        "query": query,
                        "page": page,
                        "this_page": len(items),
                        "total_so_far": len(all_repos),
                        "total_available": total_count,
                    },
                )

                if len(all_repos) >= max_results or len(items) < per_page:
                    break
                page += 1

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    logger.error(
                        "module=search", operation="search_rate_limited",
                        params={"error": str(e)},
                    )
                    await asyncio.sleep(60)
                    continue
                raise

        return all_repos[:max_results]

    # ------------------------------------------------------------------
    # Single Repository Details
    # ------------------------------------------------------------------

    async def get_repository(self, owner: str, repo: str) -> Repository:
        await self._wait_if_needed()

        resp = await self.client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}",
        )
        self._update_rate_from_response(resp)
        resp.raise_for_status()

        return Repository.from_api_response(resp.json())

    # ------------------------------------------------------------------
    # Release Information
    # ------------------------------------------------------------------

    async def get_latest_release(self, owner: str, repo: str) -> Optional[Release]:
        await self._wait_if_needed()

        try:
            resp = await self.client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/releases/latest",
            )
            self._update_rate_from_response(resp)

            if resp.status_code == 404:
                logger.info(
                    "module=search", operation="no_release_found",
                    params={"repo": f"{owner}/{repo}"},
                )
                return None

            resp.raise_for_status()
            data = resp.json()

            assets_data = data.get("assets", [])
            assets = [
                Asset(
                    id=a["id"],
                    name=a["name"],
                    download_url=a["browser_download_url"],
                    size_bytes=a["size"],
                    content_type=a["content_type"],
                    download_count=a["download_count"],
                )
                for a in assets_data
            ]

            return Release(
                tag_name=data.get("tag_name", ""),
                name=data.get("name", ""),
                body=data.get("body", ""),
                published_at=_parse_datetime(data.get("published_at")),
                archive_url=f"https://api.github.com/repos/{owner}/{repo}/zipball/{data['tag_name']}",
                is_prerelease=data.get("prerelease", False),
                is_latest=True,
                assets=assets,
            )

        except Exception as e:
            logger.warning(
                "module=search", operation="get_latest_release_error",
                params={"repo": f"{owner}/{repo}", "error": str(e)},
            )
            return None

    async def get_repo_archive_url(
        self,
        owner: str,
        repo: str,
        ref: Optional[str] = None,
    ) -> str:
        target_ref = ref or (await self.get_repository(owner, repo)).default_branch
        return f"{self.BASE_URL}/repos/{owner}/{repo}/zipball/{target_ref}"

    # ------------------------------------------------------------------
    # Community Metrics
    # ------------------------------------------------------------------

    async def get_community_metrics(
        self,
        owner: str,
        repo: str,
    ) -> Dict[str, Any]:
        await self._wait_if_needed()

        metrics: Dict[str, Any] = {}

        # Contributors
        try:
            resp = await self.client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contributors",
                params={"per_page": 10, "anon": "false"},
            )
            if resp.status_code == 200:
                contributors = resp.json()
                metrics["top_contributors"] = [
                    {"login": c["login"], "contributions": c["contributions"]}
                    for c in contributors[:10]
                ]
                metrics["contributor_count"] = _extract_link_total(resp)
        except Exception as e:
            logger.debug("module=search", operation="contributors_fetch_failed",
                          params={"error": str(e)})

        # Basic repo stats
        try:
            repo_resp = await self.client.get(f"{self.BASE_URL}/repos/{owner}/{repo}")
            if repo_resp.status_code == 200:
                repo_data = repo_resp.json()
                metrics["open_issues"] = repo_data.get("open_issues", 0)
                metrics["forks"] = repo_data.get("forks_count", 0)
                metrics["watchers"] = repo_data.get("subscribers_count", 0)
        except Exception:
            pass

        return metrics

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


def _extract_link_total(response: httpx.Response) -> int:
    """Extract total count from Link header pagination."""
    link_header = response.headers.get("Link", "")
    if 'rel="last"' in link_header:
        import re
        match = re.search(r"page=(\d+)[^>]*>;\s*rel=""last""", link_header)
        if match:
            return int(match.group(1))
    return 0


__all__ = ["GitHubClient", "RateLimitStatus"]
