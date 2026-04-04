"""
Maturity Analyzer.

Evaluates a project's production-readiness by examining version management
discipline, CI/CD infrastructure completeness, governance practices,
license presence, and supporting ecosystem indicators.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.models.metrics import MaturityMetrics
from src.models.common import score_to_maturity
from src.models.repository import Repository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MaturityAnalyzer:
    """Project production-readiness and governance assessment analyzer."""

    SEMVER_PATTERN = re.compile(
        r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def __init__(self, github_client: Any = None) -> None:
        self.github_client = github_client

    async def analyze(self, repository: Repository) -> MaturityMetrics:
        """Assess project maturity across all dimensions."""
        start_time = time.time()

        logger.info(
            "module=analysis", operation="maturity_analysis_start",
            params={"repo": repository.full_name},
        )

        try:
            code_dir = self._get_code_dir_if_available(repository)

            # Version management / 版本管理
            version_data = await self._analyze_versioning(repository)
            release_data = await self._analyze_releases(repository)

            # CI/CD infrastructure / CI/CD基础设施
            ci_data = self._analyze_ci_cd(code_dir)

            # Governance / 治理
            gov_data = self._analyze_governance(code_dir)

            # Ecosystem / 生态系统
            eco_data = self._analyze_ecosystem(code_dir)

            # Combine into final metrics / 组合为最终指标
            version_score = version_data["score"] * 0.35
            cicd_score = ci_data["score"] * 0.30
            gov_score = gov_data["score"] * 0.20
            eco_score = eco_data["score"] * 0.15
            overall = version_score + cicd_score + gov_score + eco_score

            maturity_level = score_to_maturity(overall).value

            metrics = MaturityMetrics(
                release_count=release_data["count"],
                uses_semver=version_data["uses_semver"],
                latest_version=release_data["latest"],
                days_since_last_release=release_data["days_since"],
                release_frequency_days=release_data["frequency"],
                has_ci_config=ci_data["has_ci"],
                ci_platform=ci_data["platform"],
                has_cd_pipeline=ci_data["has_cd"],
                has_automated_tests=ci_data["has_tests"],
                has_code_quality_check=ci_data["has_quality_check"],
                has_license=gov_data["has_license"],
                license_type=gov_data["license_type"],
                has_code_of_conduct=gov_data["has_conduct"],
                has_contributing_guide=gov_data["has_contributing"],
                has_security_policy=gov_data["has_security_policy"],
                has_issue_template=gov_data["has_issue_template"],
                has_pr_template=gov_data["has_pr_template"],
                has_discussion_forum=eco_data["has_forum"],
                has_website=eco_data["has_website"],
                has_roadmap=eco_data["has_roadmap"],
                has_changelog=eco_data["has_changelog"],
                maturity_level=maturity_level,
                overall_score=min(100.0, max(0.0, round(overall, 1))),
                analysis_duration_ms=int((time.time() - start_time) * 1000),
            )

            logger.info(
                "module=analysis", operation="maturity_analysis_complete",
                params={
                    "repo": repository.full_name,
                    "level": maturity_level,
                    "score": metrics.overall_score,
                    "duration_ms": metrics.analysis_duration_ms,
                },
            )
            return metrics

        except Exception as e:
            logger.error(
                "module=analysis", operation="maturity_analysis_error",
                params={"repo": repository.full_name, "error": str(e)},
            )
            return MaturityMetrics(
                overall_score=0.0,
                errors=[str(e)],
                analysis_duration_ms=int((time.time() - start_time) * 1000),
            )

    async def _analyze_versioning(self, repo: Repository) -> Dict[str, Any]:
        """Check for semantic version usage and version discipline."""
        result: Dict[str, Any] = {"uses_semver": False, "score": 0.0}

        if self.github_client:
            try:
                parts = repo.full_name.split("/")
                release = await self.github_client.get_latest_release(parts[0], parts[1])
                if release:
                    result["uses_semver"] = bool(self.SEMVER_PATTERN.match(release.tag_name))
                    result["score"] = 80.0 if result["uses_semver"] else 50.0
            except Exception:
                pass

        # Heuristic fallback / 启发式后备
        if not result["uses_semver"]:
            desc = repo.description or ""
            if re.search(r"v?\d+\.\d+\.\d+", desc):
                result["uses_semver"] = True
                result["score"] = 70.0
            elif repo.license_info:
                result["score"] = 40.0
            else:
                result["score"] = 15.0

        return result

    async def _analyze_releases(self, repo: Repository) -> Dict[str, Any]:
        """Analyze release history."""
        result: Dict[str, Any] = {
            "count": 0, "latest": None, "days_since": -1, "frequency": 0.0,
        }

        if self.github_client:
            try:
                parts = repo.full_name.split("/")
                release = await self.github_client.get_latest_release(parts[0], parts[1])
                if release:
                    result["count"] = 1
                    result["latest"] = release.version_number
                    if release.published_at:
                        delta = datetime.now(timezone.utc) - (
                            release.published_at.replace(tzinfo=None)
                        )
                        result["days_since"] = max(-1, delta.days)
            except Exception:
                pass

        if result["count"] == 0 and repo.age_days > 60:
            result["frequency"] = float(repo.age_days // max(1, repo.age_days // 30))
        elif result["days_since"] > 0:
            result["frequency"] = float(result["days_since"])
        else:
            result["frequency"] = 999.0

        return result

    def _analyze_ci_cd(self, code_dir: Optional[str]) -> Dict[str, Any]:
        """Detect CI/CD configuration."""
        result: Dict[str, Any] = {
            "has_ci": False, "platform": None, "has_cd": False,
            "has_tests": False, "has_quality_check": False, "score": 0.0,
        }

        p = Path(code_dir) if code_dir else Path(".")

        ci_indicators = [
            ("github_actions", ".github/workflows"),
            ("travis", ".travis.yml"),
            ("circleci", ".circleci"),
            ("jenkins", "Jenkinsfile"),
            ("gitlab", ".gitlab-ci.yml"),
        ]

        for platform, path_str in ci_indicators:
            if (p / path_str).exists():
                result["has_ci"] = True
                result["platform"] = platform
                break

        cd_files = [".github/workflows/deploy.yml", "Dockerfile",
                     "docker-compose.yml", "Procfile"]
        for cd_f in cd_files:
            if (p / cd_f).exists():
                result["has_cd"] = True
                break

        test_ci = [".github/workflows/test.yml", "tox.ini", "noxfile.py"]
        for tc in test_ci:
            if (p / tc).exists():
                result["has_tests"] = True
                break

        qc_files = [".github/workflows/lint.yml", "pre-commit-config.yaml"]
        for qcf in qc_files:
            if (p / qcf).exists():
                result["has_quality_check"] = True
                break

        if result["has_ci"]:
            result["score"] += 40.0
        if result["has_cd"]:
            result["score"] += 25.0
        if result["has_tests"]:
            result["score"] += 20.0
        if result["has_quality_check"]:
            result["score"] += 15.0

        return result

    def _analyze_governance(self, code_dir: Optional[str]) -> Dict[str, Any]:
        """Check governance documents."""
        result: Dict[str, Any] = {
            "has_license": False, "license_type": None,
            "has_conduct": False, "has_contributing": False,
            "has_security": False, "has_issue_template": False,
            "has_pr_template": False, "score": 0.0,
        }

        p = Path(code_dir) if code_dir else Path(".")

        license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md",
                         "COPYING", "LICENCE"]
        for lf in license_files:
            if (p / lf).exists():
                result["has_license"] = True
                try:
                    content = (p / lf).read_text(encoding="utf-8", errors="ignore")[:500]
                    for spdx in ["MIT", "Apache", "GPL", "BSD", "ISC", "MPL"]:
                        if spdx.lower() in content.lower():
                            result["license_type"] = spdx
                            break
                except Exception:
                    result["license_type"] = "Unknown"
                break

        gov_map = {
            "CODE_OF_CONDUCT.md": "has_conduct",
            "CONDUCT.md": "has_conduct",
            "CONTRIBUTING.md": "has_contributing",
            "SECURITY.md": "has_security",
            "SECURITY_POLICY.md": "has_security",
        }
        for fname, key in gov_map.items():
            if (p / fname).exists():
                result[key] = True

        template_dirs = [".github/ISSUE_TEMPLATE/",
                        ".github/PULL_REQUEST_TEMPLATE/"]
        for td in template_dirs:
            if (p / td).is_dir():
                files_in_td = list((p / td).iterdir())
                if any(f.is_file() for f in files_in_td):
                    if "issue" in td.lower():
                        result["has_issue_template"] = True
                    else:
                        result["has_pr_template"] = True

        # Score calculation / 分数计算
        score_parts = [
            (result["has_license"], 25.0),
            (result["has_contributing"], 20.0),
            (result["has_security"], 15.0),
            (result["has_conduct"], 10.0),
            (result["has_issue_template"] or result["has_pr_template"], 15.0),
        ]
        for condition, points in score_parts:
            if condition:
                result["score"] += points
        if result["has_license"] and result["has_contributing"]:
            result["score"] += 15.0

        return result

    def _analyze_ecosystem(self, code_dir: Optional[str]) -> Dict[str, Any]:
        """Evaluate ecosystem support infrastructure."""
        result: Dict[str, Any] = {
            "has_forum": False, "has_website": False,
            "has_roadmap": False, "has_changelog": False, "score": 0.0,
        }
        p = Path(code_dir) if code_dir else Path(".")

        forum_indicators = ["DISCUSSIONS.md", "docs/community.md", "SUPPORT.md"]
        for fi in forum_indicators:
            if (p / fi).exists():
                result["has_forum"] = True
                break

        website_indicators = ["WEBSITE.md", "docs/website.md", "URL"]
        for wi in website_indicators:
            if (p / wi).exists():
                result["has_website"] = True
                break

        roadmap_files = ["ROADMAP.md", "docs/roadmap.md", "TODO.md"]
        for rf in roadmap_files:
            if (p / rf).exists():
                result["has_roadmap"] = True
                break

        changelog_files = ["CHANGELOG.md", "CHANGES.md", "HISTORY.md", "NEWS.md"]
        for cl in changelog_files:
            if (p / cl).exists():
                result["has_changelog"] = True
                break

        score_items = [
            (result["has_changelog"], 30.0),
            (result["has_forum"], 25.0),
            (result["has_roadmap"], 20.0),
            (result["has_website"], 15.0),
        ]
        for condition, pts in score_items:
            if condition:
                result["score"] += pts
        if result["has_changelog"] and result["has_forum"]:
            result["score"] += 10.0

        return result

    def _get_code_dir_if_available(self, repo: Repository) -> Optional[str]:
        """Try to find existing extracted code directory."""
        from src.storage.file_manager import FileManager
        fm = FileManager()
        workspace = fm.create_project_workspace(repo.full_name)
        code_dir = workspace / "code"
        if code_dir.exists():
            return str(code_dir)
        return None


__all__ = ["MaturityAnalyzer"]
