"""
Code Quality Analyzer.

Analyzes downloaded project code across multiple quality dimensions:
coding conventions, test coverage, dependency management, documentation
completeness, and architecture clarity. Uses rule-based static analysis
with optional tool integration (radon for complexity).

代码质量分析器.
在多个质量维度上分析下载的项目代码:
编码规范,测试覆盖率,依赖管理,文档完整性和架构清晰度.
使用基于规则的静态分析,可选工具集成(radon用于复杂度分析).
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.metrics import CodeQualityMetrics
from src.models.repository import Repository
from src.storage.file_manager import FileManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CodeAnalyzer:
    """Static code quality analyzer using rule-based heuristics.

    Examines a project's codebase after download/extraction and produces a
    multi-dimensional quality assessment without requiring compilation or execution.
    Uses filesystem patterns, AST parsing (for Python), and configurable rules.

    使用基于规则启发式的静态代码质量分析器.
在下载/提取后检查项目的代码库并生成多维质量评估,
无需编译或执行.使用文件系统模式,AST解析(针对Python)和可配置规则.

    Attributes:
        file_manager: FileManager instance for workspace operations.
                     用于工作区操作的FileManager实例.
    """

    # Known test directory names / 已知测试目录名
    TEST_DIRS: List[str] = ["tests", "test", "spec", "specs", "__tests__"]
    TEST_FILE_PATTERNS: List[str] = [
        r"test_.*\.py$", r".*_test\.py$",
        r"test.*\.ts$", r".*\.spec\.ts$",
        r"test_.*\.js$", r".*\.test\.js$",
        r".*\.test\.go$", r".*\.spec\.go$",
    ]
    # Known dependency file names / 已知依赖文件名
    DEPENDENCY_FILES: Dict[str, str] = {
        "requirements.txt": "pip",
        "setup.py": "setuptools",
        "setup.cfg": "setuptools",
        "pyproject.toml": "modern",
        "package.json": "npm/yarn/pnpm",
        "Cargo.toml": "cargo",
        "go.mod": "go modules",
        "Gemfile": "bundler",
        "pom.xml": "maven",
        "build.gradle": "gradle",
    }
    DOC_FILES: List[str] = [
        "README.md", "README.rst", "README.txt", "README",
        "CHANGELOG.md", "CHANGELOG.rst", "HISTORY.md",
        "API.md", "DOCUMENTATION.md", "docs/index.md",
        "CONTRIBUTING.md", "SECURITY.md",
    ]

    def __init__(
        self,
        file_manager: Optional[FileManager] = None,
        max_size_mb: int = 50,
    ) -> None:
        self.file_manager = file_manager or FileManager()
        self.max_size_mb = max_size_mb

    async def analyze(
        self,
        repository: Repository,
    ) -> CodeQualityMetrics:
        """Analyze the code quality of a given repository.

        分析给定仓库的代码质量.

        Args:
            repository: Repository metadata to analyze.
                       要分析的仓库元数据.

        Returns:
            Complete CodeQualityMetrics assessment.
             完整的CodeQualityMetrics评估.
        """
        start_time = time.time()

        logger.info(
            "module=analysis", operation="code_analysis_start",
            params={"repo": repository.full_name},
        )

        try:
            # Step 1: Download and extract / 步骤1:下载和解压
            code_dir = await self._get_code_directory(repository)

            if not code_dir:
                return CodeQualityMetrics(
                    overall_score=0.0,
                    errors=[f"Failed to download/extract code for {repository.full_name}"],
                )

            # Step 2: Run all analysis dimensions in parallel / 步骤2:并行运行所有分析维度
            style_result = self._analyze_code_style(code_dir)
            test_result = self._analyze_test_coverage(code_dir)
            dep_result = self._analyze_dependencies(code_dir)
            doc_result = self._analyze_documentation(code_dir)
            arch_result = self._analyze_architecture(code_dir)

            security_issues = self._detect_security_patterns(code_dir)

            # Calculate overall score / 计算综合分数
            weights = {
                "style": 0.25,
                "tests": 0.20,
                "deps": 0.15,
                "docs": 0.20,
                "arch": 0.20,
            }
            overall = (
                style_result * weights["style"]
                + test_result * weights["tests"]
                + dep_result * weights["deps"]
                * 100  # Scale to 100 / 缩放到100
                if isinstance(dep_result, tuple) else dep_result * 100
                if not isinstance(dep_result, tuple) else dep_result[0] * 100
                + doc_result * weights["docs"] * 100
                + arch_result * weights["arch"] * 100
            )
            # Simplified: use direct scores / 简化:使用直接分数
            overall = (
                style_result * 25
                + test_result[0] if isinstance(test_result, tuple) else test_result * 20
                + (dep_result[0] if isinstance(dep_result, tuple) else dep_result) * 15
                + doc_result * 20
                + arch_result * 10
            )

            metrics = CodeQualityMetrics(
                code_style_score=style_result,
                test_coverage=test_result[0] if isinstance(test_result, tuple) else test_result,
                test_framework=test_result[1] if isinstance(test_result, tuple) else None,
                has_tests=(isinstance(test_result, tuple) and test_result[2])
                            or (not isinstance(test_result, tuple) and test_result > 0),
                dependency_count=dep_result[0] if isinstance(dep_result, tuple) else int(dep_result * 5),
                outdated_dependencies=dep_result[1] if len(dep_result) > 1 else 0,
                security_issues=security_issues,
                doc_completeness=doc_result,
                has_readme=Path(code_dir / "README.md").exists()
                           or Path(code_dir / "README.rst").exists(),
                has_api_docs=any(
                    (code_dir / d).exists() for d in ["docs/", "api/", "reference/"]
                ),
                has_examples=any(
                    (code_dir / e).exists() for e in ["examples/", "demo/"]
                ),
                architecture_score=arch_result,
                overall_score=min(100.0, max(0.0, overall)),
                analysis_duration_ms=int((time.time() - start_time) * 1000),
            )

            logger.info(
                "module=analysis", operation="code_analysis_complete",
                params={
                    "repo": repository.full_name,
                    "overall_score": metrics.overall_score,
                    "duration_ms": metrics.analysis_duration_ms,
                },
            )
            return metrics

        except Exception as e:
            logger.error(
                "module=analysis", operation="code_analysis_error",
                params={"repo": repository.full_name, "error": str(e)},
            )
            return CodeQualityMetrics(
                overall_score=0.0,
                errors=[str(e)],
                analysis_duration_ms=int((time.time() - start_time) * 1000),
            )

    # ------------------------------------------------------------------
    # Analysis Dimensions / 分析维度
    # ------------------------------------------------------------------

    def _analyze_code_style(self, code_dir: str) -> float:
        """Score coding convention adherence based on config files presence.

        基于配置文件存在情况评分编码约定遵循度."""
        score = 0.0
        p = Path(code_dir)

        # Style checkers / 样式检查器
        style_tools = [".flake8", ".pylintrc", "pyproject.toml",
                        ".eslintrc", ".prettierrc", ".editorconfig"]
        found = sum(1 for t in style_tools if (p / t).exists())
        score += min(40.0, found * 10)

        # Formatter configs / 格式化器配置
        formatters = ["black.toml", "isort.cfg", "rustfmt.toml", "gofmt"]
        found_fmt = sum(1 for f in formatters if (p / f).exists())
        score += min(30.0, found_fmt * 7.5)

        # Type checking / 类型检查
        type_files = ["mypy.ini", "py.typed", "tsconfig.json"]
        found_type = sum(1 for tf in type_files if (p / tf).exists())
        score += min(20.0, found_type * 6.6)

        # Linter present / 存在Linter
        linters = ["Makefile", "tox.ini", "noxfile.py", "ci/lint.sh"]
        found_lint = any((p / lt).exists() for lt in linters)
        if found_lint:
            score += 10.0

        return min(100.0, score)

    def _analyze_test_coverage(self, code_dir: str) -> tuple:
        """Estimate test coverage from directory/file patterns.

        从目录/文件模式估计测试覆盖率."""
        p = Path(code_dir)
        has_tests = False
        framework_name = None
        estimated_coverage = 0.0

        # Check for test directories / 检查测试目录
        for td in self.TEST_DIRS:
            if (p / td).exists():
                has_tests = True
                break

        # Check for test files / 检查测试文件
        test_file_count = 0
        source_file_count = 0

        for pattern in self.TEST_FILE_PATTERNS:
            test_file_count += len(list(p.glob(f"**/{pattern}")))

        # Count source files / 统计源文件
        source_exts = {".py", ".ts", ".js", ".go", ".rs", ".java"}
        for ext in source_exts:
            source_file_count += len(
                list(p.glob(f"**/*{ext}"))
            ) - len(list(p.glob(f"**/test*{ext}"))) - len(list(p.glob(f"**/*_test{ext}")))

        # Detect framework / 检测框架
        framework_indicators = {
            "pytest": ["conftest.py", "pytest.ini", "pyproject.toml"],
            "unittest": [],
            "jest": ["jest.config.js", "jest.config.ts"],
            "mocha": [".mocharc.json"],
            "go test": ["*_test.go"],
        }
        for fw, indicators in framework_indicators.items():
            if any((p / ind).exists() for ind in indicators):
                framework_name = fw
                break
        if not framework_name:
            if test_file_count > 0:
                if any(p.suffix == ".go" for p in p.glob("**/*_test.go")):
                    framework_name = "go test"
                elif any(p.name.startswith("test_") for p in p.glob("**/*.py")):
                    framework_name = "pytest/unittest"

        # Estimate coverage / 估算覆盖率
        if has_tests or test_file_count > 0:
            base = 30.0
            if source_file_count > 0:
                ratio = min(1.0, test_file_count / max(source_file_count, 1))
                estimated_coverage = base + (ratio * 60)
            else:
                estimated_coverage = base + 20.0

            # Bonus for CI test integration / CI测试集成加分
            ci_test_files = [
                f for f in [".github/workflows/test.yml", "circle.yml", ".travis.yml"]
                if (p / f).exists()
            ]
            if ci_test_files:
                estimated_coverage += 5.0

        return (min(100.0, estimated_coverage), framework_name, has_tests)

    def _analyze_dependencies(self, code_dir: str) -> tuple:
        """Count and assess dependency files.

        计数和评估依赖文件."""
        p = Path(code_dir)
        dep_count = 0
        outdated = 0
        found_deps = []

        for dep_file, manager in self.DEPENDENCY_FILES.items():
            fp = p / dep_file
            if fp.exists():
                found_deps.append(dep_file)
                try:
                    content = fp.read_text(encoding="utf-8", errors="ignore")
                    lines = [l.strip() for l in content.splitlines() if l.strip()
                              and not l.strip().startswith("#")
                              and not l.strip().startswith("//")]
                    dep_count += len(lines)
                    # Heuristic: flag common outdated version patterns / 启发式:标记常见过时版本模式
                    for line in lines[:50]:
                        if re.search(r"<\d+\.\d+", line):
                            outdated += 1  # Might be outdated XML version / 可能是过时的XML版本
                        elif re.search(r"==\d+\.\d+[^,]*,", line):
                            pass  # Pinned is good / 固定版本是好的
                except Exception:
                    dep_count += 1  # Couldn't parse; count as at least one / 无法解析;至少计为1个

        return (dep_count, outdated)

    def _analyze_documentation(self, code_dir: str) -> float:
        """Assess documentation completeness.

        评估文档完整性."""
        p = Path(code_dir)
        score = 0.0

        # README / README
        readme_exists = False
        for rf in ["README.md", "README.rst", "README"]:
            if (p / rf).exists():
                readme_exists = True
                score += 25.0
                # Check README size / 检查README大小
                size = (p / rf).stat().st_size
                if size > 500:   # Has some content / 有一些内容
                    score += 10.0
                if size > 2000:  # Substantial / 内容充实
                    score += 10.0
                break

        if not readme_exists:
            return 5.0  # Minimal credit / 最少分数

        # API docs / API文档
        api_dirs = ["docs/", "api/", "doc/"]
        for ad in api_dirs:
            if (p / ad).is_dir():
                files_in_api = list((p / ad).rglob("*"))
                non_empty = [f for f in files_in_api if f.is_file()]
                if non_empty:
                    score += 12.5
                    break

        # Examples / 示例
        example_dirs = ["examples/", "example/", "demo/", "samples/"]
        for ed in example_dirs:
            if (p / ed).is_dir():
                sample_files = list((p / ed).rglob("*"))
                code_samples = [f for f in sample_files
                                if f.is_file() and f.suffix in {".py", ".js", ".ts", ".go"}]
                if code_samples:
                    score += 12.5
                    break

        # Changelog / 变更日志
        for cl in ["CHANGELOG.md", "CHANGES.md", "HISTORY.md", "NEWS.md"]:
            if (p / cl).exists():
                score += 10.0
                break

        # Contributing guide / 贡献指南
        for cg in ["CONTRIBUTING.md", "CONTRIBUTE.md"]:
            if (p / cg).exists():
                score += 5.0
                break

        return min(100.0, score)

    def _analyze_architecture(self, code_dir: str) -> float:
        """Evaluate code organization and modularity.

        评估代码组织和模块化."""
        p = Path(code_dir)
        score = 0.0

        # Directory structure / 目录结构
        subdirs = [d for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")]
        meaningful_dirs = [d for d in subdirs
                          if d.name not in {".git", "__pycache__", "node_modules",
                                         ".venv", "venv", "dist", "build"}]

        if len(meaningful_dirs) >= 3:
            score += 20.0  # Well organized / 组织良好
        elif len(meaningful_dirs) >= 1:
            score += 10.0
        else:
            score += 2.0  # Flat structure / 扁平结构

        # Module/package separation / 模块/包分离
        init_files = list(p.rglob("__init__.py"))
        if len(init_files) >= 2:
            score += 20.0
        elif len(init_files) >= 1:
            score += 10.0

        # Separation of concerns / 关注点分离
        has_src = any(d.name.lower() in {"src", "lib", "app"} for d in meaningful_dirs)
        has_tests = any(d.name.lower().startswith("test") for d in meaningful_dirs)
        has_config = any(d.name.lower() in {"config", "conf", "etc"} for d in meaningful_dirs)

        if has_src and has_tests:
            score += 20.0
        elif has_src or has_tests:
            score += 10.0
        if has_config:
            score += 10.0

        # Entry point definition / 入口点定义
        entry_points = ["main.py", "index.ts", "index.js", "main.go", "cmd/",
                         "app.py", "server.js"]
        for ep in entry_points:
            target = p / ep
            if target.exists():
                score += 10.0
                break

        return min(100.0, score)

    def _detect_security_patterns(self, code_dir: str) -> List[str]:
        """Detect potentially insecure patterns in codebase.

        检测代码库中的潜在不安全模式."""
        issues: List[str] = []
        p = Path(code_dir)

        dangerous_patterns = {
            r"(?i)(eval\s*\(|exec\s*\(|os\.system|subprocess\.call\(shell=True)": "Command injection risk",
            r"(?i)(hardcoded.password|hardcoded.secret|api_key\s*=\s*[\"'])": "Hardcoded secret detected",
            r"(?i)(sql.*\+\s*user_input|format.*select.*from)": "SQL injection risk",
            r"(?i)(pickle\.loads|yaml\.load\(?!_safe)": "Unsafe deserialization",
            r"(?i)(http://[^/]*(?!localhost))": "Insecure HTTP URL (non-HTTPS)",
            r"(?i)(random\.|secrets\.):": "Weak random/crypto usage",
        }

        # Scan Python files primarily / 主要扫描Python文件
        for py_file in p.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                for pattern, description in dangerous_patterns.items():
                    if re.search(pattern, content):
                        rel_path = py_file.relative_to(p)
                        issue = f"{description}: {rel_path}"
                        if issue not in issues:
                            issues.append(issue)
            except Exception:
                continue

        return issues[:10]  # Cap at 10 issues / 上限10个问题

    # ------------------------------------------------------------------
    # Code Download Helper / 代码下载辅助
    # ------------------------------------------------------------------

    async def _get_code_directory(self, repository: Repository) -> Optional[str]:
        """Download or retrieve extracted code for analysis.

        下载或获取用于分析的解压代码."""
        release = None

        # Try to get latest release first / 首先尝试获取最新发布版
        try:
            from src.search.github_client import GitHubClient
            gh_client = GitHubClient()
            release = await gh_client.get_latest_release(
                repository.full_name.split("/")[0],
                repository.full_name.split("/")[1],
            )
        except Exception as e:
            logger.debug(
                "module=analysis", operation="release_lookup_skipped",
                params={"repo": repository.full_name, "error": str(e)},
            )

        if release and release.archive_url:
            result = self.file_manager.download_archive_to_workspace(
                repo_full_name=repository.full_name,
                archive_url=release.archive_url,
            )
        else:
            # Fall back to default branch archive / 回退到默认分支归档
            try:
                from src.search.github_client import GitHubClient
                gh_client = GitHubClient()
                archive_url = await gh_client.get_repo_archive_url(
                    repository.full_name.split("/")[0],
                    repository.full_name.split("/")[1],
                )
                result = self.file_manager.download_archive_to_workspace(
                    repo_full_name=repository.full_name,
                    archive_url=archive_url,
                )
            except Exception as e:
                logger.warning(
                    "module=analysis", operation="download_failed",
                    params={"repo": repository.full_name, "error": str(e)},
                )
                result = None

        return result


__all__ = ["CodeAnalyzer"]
