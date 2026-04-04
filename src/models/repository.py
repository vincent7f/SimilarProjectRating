"""
Repository Domain Models.

Data classes representing GitHub repositories, releases, assets,
and related metadata returned by the GitHub REST API.

仓库领域模型。
表示GitHub仓库、发布版本、资产以及GitHub REST API返回的相关元数据的dataclass。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class LicenseInfo:
    """Software license information for a repository.

    Represents the license detected or specified for a GitHub repository,
    including SPDX identifier and any additional details available.

    仓库的软件许可证信息。
表示为GitHub仓库检测或指定的许可证，
包括SPDX标识符和任何其他可用细节。

    Attributes:
        spdx_id: SPDX license identifier (e.g., 'MIT', 'Apache-2.0', 'GPL-3.0').
                 SPDX许可证标识符（例如'MIT'、'Apache-2.0'、'GPL-3.0'）。
        name: Full license name (e.g., 'MIT License').
               完整许可证名称（例如'MIT License'）。
        url: URL to the full license text.
             完整许可证文本的URL。
    """
    spdx_id: str = ""
    name: str = ""
    url: str = ""


@dataclass
class Asset:
    """Release asset (attached file) information.

    Represents a file attached to a GitHub release, such as source archives,
    compiled binaries, or documentation packages.

    发布资产（附加文件）信息。
表示附加到GitHub发布的文件，如源代码归档、编译二进制文件或文档包。

    Attributes:
        id: Unique asset identifier.
             唯一资产标识符。
        name: Asset filename (e.g., 'project-v1.0.0.zip').
             资产文件名（例如'project-v1.0.0.zip'）。
        download_url: Direct download URL for the asset.
                      资产的直接下载URL。
        size_bytes: File size in bytes.
                    文件大小（字节）。
        content_type: MIME type of the asset file.
                     资产文件的MIME类型。
        download_count: Number of times this asset has been downloaded.
                       此资产的下载次数。
    """
    id: int = 0
    name: str = ""
    download_url: str = ""
    size_bytes: int = 0
    content_type: str = "application/zip"
    download_count: int = 0


@dataclass
class Release:
    """GitHub release version information.

    Represents a published release on a GitHub repository, including
    its tag, publication date, and downloadable archive URLs.

    GitHub发布版本信息。
表示GitHub仓库上的已发布版本，包括其标签、发布日期和可下载的归档URL。

    Attributes:
        tag_name: Git tag identifying this release (e.g., 'v1.0.0').
                  标识此版本的Git标签（例如'v1.0.0'）。
        name: Human-readable release name (may differ from tag).
              可读的发布名称（可能与标签不同）。
        body: Release notes/description body in Markdown format.
              Markdown格式的发布说明/描述正文。
        published_at: Date and time when the release was published.
                      发布日期和时间。
        archive_url: URL to download the source code zipball for this release.
                    下载此发布版本的源代码zipball的URL。
        is_prerelease: Whether this is a pre-release (alpha/beta/rc).
                       是否为预发布版（alpha/beta/rc）。
        is_latest: Whether this is the latest release for the repository.
                   是否为仓库的最新发布版本。
        assets: List of files attached to this release.
                附加到此发布的文件列表。
    """
    tag_name: str = ""
    name: str = ""
    body: str = ""
    published_at: Optional[datetime] = None
    archive_url: str = ""
    is_prerelease: bool = False
    is_latest: bool = False
    assets: List[Asset] = field(default_factory=list)

    @property
    def version_number(self) -> str:
        """Extract semantic version number from tag_name.

        Attempts to parse a semver-compatible version string from the tag,
        stripping 'v' prefix if present.

        从tag_name中提取语义化版本号。
尝试从标签中解析semver兼容的版本字符串，
如果存在则去除'v'前缀。

        Returns:
            Cleaned version string (e.g., '1.0.0' from 'v1.0.0').
            清理后的版本字符串（例如从'v1.0.0'得到'1.0.0'）。
        """
        version = self.tag_name.lstrip("vV")
        return version.split("/")[0]  # Handle tags like 'release/v1.0'


@dataclass
class Repository:
    """Core repository model representing a GitHub project.

    This is the primary domain entity used throughout the analysis pipeline.
    Contains metadata retrieved from the GitHub REST API including statistics,
    timestamps, and classification data.

    表示GitHub项目的核心仓库模型。
这是分析流水线中使用的主要领域实体。
包含从GitHub REST API检索到的元数据，包括统计信息、时间戳和分类数据。

    Attributes:
        id: Unique GitHub repository identifier.
             唯一GitHub仓库标识符。
        name: Repository name (without owner).
             仓库名称（不含所有者）。
        full_name: Full repository identifier in 'owner/repo' format.
                   完整仓库标识符，格式为'owner/repo'。
        description: Short description of the project's purpose and functionality.
                     项目用途和功能的简短描述。
        url: HTML URL to the repository page.
             仓库页面的HTML URL。
        stars: Total star count (popularity indicator).
               总star数（受欢迎程度指标）。
        forks: Total fork count (reuse indicator).
               总fork数（复用指标）。
        open_issues: Count of currently open issues.
                     当前开放的Issue数量。
        watchers: Count of users watching this repository.
                  关注此仓库的用户数量。
        primary_language: Main programming language (e.g., 'Python', 'TypeScript').
                         主要编程语言（例如'Python'、'TypeScript'）。
        topics: Repository topic tags assigned by maintainers.
                维护者分配的仓库主题标签。
        created_at: Repository creation date and time.
                   仓库创建日期和时间。
        updated_at: Last time metadata was updated by GitHub.
                   GitHub最后更新元数据的时间。
        pushed_at: Last commit push date and time.
                  最后一次提交推送的日期和时间。
        default_branch: Default branch name (usually 'main' or 'master').
                        默认分支名称（通常为'main'或'master'）。
        license_info: License information if declared.
                      声明的许可证信息（如有）。
        archived: Whether the repository has been archived (read-only).
                 仓库是否已被归档（只读）。
        size_kb: Repository size in kilobytes (approximate).
                 仓库大小（千字节）（近似值）。
    """
    id: int = 0
    name: str = ""
    full_name: str = ""
    description: str = ""
    url: str = ""
    html_url: str = ""
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    watchers: int = 0
    primary_language: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None
    default_branch: str = "main"
    license_info: Optional[LicenseInfo] = None
    archived: bool = False
    size_kb: int = 0

    @classmethod
    def from_api_response(cls, data: dict) -> Repository:
        """Construct a Repository instance from GitHub API JSON response.

        Maps raw API response fields to typed Repository attributes with
        appropriate parsing for dates, nested objects, and lists.

        从GitHub API JSON响应构造Repository实例。
将原始API响应字段映射到类型化的Repository属性，
对日期、嵌套对象和列表进行适当的解析。

        Args:
            data: Dictionary from GitHub REST API response payload.
                  来自GitHub REST API响应负载的字典。

        Returns:
            Fully populated Repository instance.
            完全填充的Repository实例。
        """
        from src.models.common import _parse_datetime

        license_data = data.get("license")
        license_info = None
        if license_data:
            license_info = LicenseInfo(
                spdx_id=license_data.get("spdx_id", "") or "",
                name=license_data.get("name", "") or "",
                url=license_data.get("url", "") or "",
            )

        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            description=data.get("description", "") or "",
            url=data.get("url", "") or "",
            html_url=data.get("html_url", "") or "",
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            open_issues=data.get("open_issues_count", 0),
            watchers=data.get("watchers_count", 0) or data.get("subscribers_count", 0),
            primary_language=data.get("language"),
            topics=data.get("topics") or [],
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            pushed_at=_parse_datetime(data.get("pushed_at")),
            default_branch=data.get("default_branch", "main"),
            license_info=license_info,
            archived=data.get("archived", False),
            size_kb=data.get("size", 0),
        )

    @property
    def age_days(self) -> int:
        """Calculate repository age in days since creation.

        计算自创建以来的仓库天数。

        Returns:
            Number of days since creation, or 0 if date unknown.
            自创建以来的天数，如日期未知则返回0。
        """
        if not self.created_at:
            return 0
        delta = datetime.utcnow() - self.created_at.replace(tzinfo=None)
        return max(0, delta.days)

    @property
    def days_since_last_push(self) -> int:
        """Calculate days since the last commit push.

        计算自上次提交推送以来的天数。

        Returns:
            Days since last push, or -1 if unknown.
            自上次推送以来的天数，未知则返回-1。
        """
        if not self.pushed_at:
            return -1
        delta = datetime.utcnow() - self.pushed_at.replace(tzinfo=None)
        return max(0, delta.days)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 datetime string to datetime object.

    将ISO 8601日期时间字符串解析为datetime对象。

    Args:
        value: ISO 8601 formatted datetime string or None.
               ISO 8601格式的日期时间字符串或None。

    Returns:
        Parsed datetime object or None if input is invalid/empty.
        解析后的datetime对象，如输入无效/空则返回None。
    """
    if not value:
        return None
    try:
        # Handle ISO format with Z suffix / 处理带Z后缀的ISO格式
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        return dt
    except (ValueError, TypeError):
        return None
