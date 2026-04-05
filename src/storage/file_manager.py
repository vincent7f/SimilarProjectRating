"""
File Manager - Temporary file and report output management.

Handles temporary directory creation for code downloads, archive extraction,
result serialization, and cleanup operations during analysis execution.

文件管理器 - 临时文件和报告输出管理.
处理代码下载,归档解压,结果序列化和分析执行期间
清理操作的临时目录创建.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class FileManager:
    """Manages filesystem operations for code download temp directories and report outputs.

    Provides safe abstractions for creating isolated working directories per-project,
    extracting archives, writing structured reports, and cleaning up resources.

    管理代码下载临时目录和报告输出的文件系统操作.
为每个项目创建隔离的工作目录,提取归档,编写结构化报告
和清理资源的安全抽象层.

    Attributes:
        base_temp_dir: Root directory for all temporary files.
                      所有临时文件的根目录.
        output_dir: Directory where final reports are written.
                   最终报告写入的目录.
    """

    def __init__(
        self,
        base_temp_dir: str = "./data/temp",
        output_dir: str = "./data/results",
    ) -> None:
        """Initialize with configurable base paths.

        使用可配置的基础路径初始化.

        Args:
            base_temp_dir: Root path for temporary extraction directories.
                          临时提取目录的根路径.
            output_dir: Path for writing analysis result reports.
                       写入分析结果报告的路径.
        """
        self.base_temp_dir = Path(base_temp_dir)
        self.output_dir = Path(output_dir)

        # Ensure base directories exist / 确保基础目录存在
        self.base_temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Temp Directory Management / 临时目录管理
    # ------------------------------------------------------------------

    def create_project_workspace(self, repo_full_name: str) -> Path:
        """Create an isolated workspace directory for analyzing a specific project.

        Creates a unique subdirectory under base_temp_dir named after the project's
        full name (with sanitized characters). Safe to call multiple times for same
        project (returns existing path).

        为分析特定项目创建隔离的工作区目录.
在base_temp_dir下创建以项目全名命名的唯一子目录(字符已净化).
对同一项目多次调用是安全的(返回现有路径).

        Args:
            repo_full_name: Repository identifier ('owner/repo').
                           仓库标识符('owner/repo').

        Returns:
            Path to the workspace directory ready for use.
             可使用的工作区目录路径.
        """
        safe_name = repo_full_name.replace("/", "_").replace("\\", "_")
        workspace = self.base_temp_dir / safe_name
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def get_code_directory(self, repo_full_name: str) -> Path:
        """Get or create the expected extracted code directory for a project.

        获取或创建项目的预期解压代码目录.

        Args:
            repo_full_name: Repository identifier.
                           仓库标识符.

        Returns:
            Path where extracted code should reside.
             解压代码应位于的路径.
        """
        workspace = self.create_project_workspace(repo_full_name)
        code_dir = workspace / "code"
        code_dir.mkdir(parents=True, exist_ok=True)
        return code_dir

    def cleanup_project_workspace(self, repo_full_name: str) -> bool:
        """Remove all temporary files for a completed project analysis.

        删除已完成项目分析的所有临时文件.

        Args:
            repo_full_name: Repository identifier whose files to clean.
                           要清理的仓库标识符.

        Returns:
            True if removal succeeded, False otherwise (e.g., not found).
             删除成功则返回True,否则返回False(例如未找到).
        """
        safe_name = repo_full_name.replace("/", "_").replace("\\", "_")
        workspace = self.base_temp_dir / safe_name
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
            return True
        return False

    def cleanup_all_workspaces(self) -> int:
        """Remove all temporary workspace directories.

        删除所有临时工作区目录.

        Returns:
            Number of workspaces removed.
             删除的工作区数量.
        """
        count = 0
        for item in self.base_temp_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                count += 1
        return count

    # ------------------------------------------------------------------
    # Archive Handling / 归档处理
    # ------------------------------------------------------------------

    def download_archive_to_workspace(
        self,
        repo_full_name: str,
        archive_url: str,
    ) -> Optional[Path]:
        """Download and extract a repository archive into the project workspace.

        Downloads from the provided URL (typically GitHub zipball URL), extracts
        contents into the workspace/code directory, and returns the root path
        of the extracted code.

        将仓库归档下载并提取到项目工作区中.
从提供的URL下载(通常是GitHub zipball URL),将内容提取到workspace/code目录,
并返回提取代码的根路径.

        Args:
            repo_full_name: Repository identifier for workspace naming.
                           用于工作区命名的仓库标识符.
            archive_url: Direct download URL for the archive file.
                        归档文件的直接下载URL.

        Returns:
            Path to the extracted code root directory, or None on failure.
             解压后的代码根目录路径,失败时返回None.
        """
        import httpx

        workspace = self.create_project_workspace(repo_full_name)
        archive_path = workspace / f"{repo_full_name.replace('/', '_')}.zip"

        try:
            response = httpx.get(archive_url, follow_redirects=True, timeout=300)
            response.raise_for_status()

            with open(archive_path, "wb") as f:
                f.write(response.content)

            # Extract ZIP archive / 解压ZIP归档
            import zipfile

            extract_target = workspace / "extracted"
            extract_target.mkdir(exist_ok=True=True)

            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_target)

            # GitHub zipballs contain a single root folder; find it / GitHub zipball包含单个根文件夹;找到它
            extracted_items = list(extract_target.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                code_root = extracted_items[0]
            else:
                code_root = extract_target

            # Move to standard location / 移动到标准位置
            code_dir = self.get_code_directory(repo_full_name)
            if code_root != code_dir:
                # Copy contents / 复制内容
                for item in code_root.iterdir():
                    dest = code_dir / item.name
                    if dest.exists():
                        shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
                    shutil.move(str(item), str(dest))

            # Clean up archive / 清理归档
            archive_path.unlink(missing_ok=True)
            if extract_target != code_dir:
                shutil.rmtree(extract_target, ignore_errors=True)

            return code_dir

        except Exception:
            # Clean up partial state / 清理部分状态
            if archive_path.exists():
                archive_path.unlink(missing_ok=True)
            return None

    # ------------------------------------------------------------------
    # Report Output / 报告输出
    # ------------------------------------------------------------------

    def save_report(
        self,
        data: Dict[str, Any],
        filename: str,
        format_type: str = "json",
    ) -> Path:
        """Write analysis results to a report file in the output directory.

        将分析结果写入输出目录中的报告文件.

        Args:
            data: Report data dictionary to serialize.
                 要序列化的报告数据字典.
            filename: Base filename (without extension).
                     基本文件名(不带扩展名).
            format_type: Output format ('json', 'markdown', 'md', 'txt').
                        输出格式('json','markdown','md','txt').

        Returns:
            Path to the written report file.
             写入的报告文件路径.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if format_type.lower() in ("markdown", "md"):
            filepath = self.output_dir / f"{filename}.md"
            content = self._format_markdown(data)
        elif format_type.lower() == "json":
            filepath = self.output_dir / f"{filename}.json"
            content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        else:
            filepath = self.output_dir / f"{filename}.{format_type}"
            content = str(data)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def _format_markdown(self, data: Dict[str, Any]) -> str:
        """Convert structured data to Markdown report format.

        将结构化数据转换为Markdown报告格式.

        Args:
            data: Report data dictionary.
                 报告数据字典.

        Returns:
            Formatted Markdown string.
             格式化的Markdown字符串.
        """
        lines = [f"# Analysis Report: {data.get('query', 'Untitled')}", ""]
        lines.append(f"**Generated:** {_now_iso()}")

        if "results" in data:
            lines.append("\n## Results\n")
            for idx, result in enumerate(data["results"], 1):
                name = result.get("project_full_name", "?")
                score = result.get("comprehensive_score", 0)
                tier = result.get("tier", "?")
                lines.append(f"### {idx}. **{name}** | Score: {score:.1f} | Tier: {tier}")

                reason = result.get("recommendation_reason", "")
                if reason:
                    lines.append(f"\n> {reason}\n")

        if "summary" in data:
            lines.append("\n## Summary\n")
            for key, val in data["summary"].items():
                lines.append(f"- **{key}:** {val}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Utility Methods / 工具方法
    # ------------------------------------------------------------------

    def get_workspace_size_bytes(self, repo_full_name: str) -> int:
        """Calculate total size of a project's workspace in bytes.

        计算项目工作区的总大小(字节).

        Args:
            repo_full_name: Repository identifier.
                           仓库标识符.

        Returns:
            Total size in bytes, or 0 if workspace doesn't exist.
             总字节大小,如工作区不存在则为0.
        """
        safe_name = repo_full_name.replace("/", "_").replace("\\", "_")
        workspace = self.base_temp_dir / safe_name
        if not workspace.exists():
            return 0
        return sum(f.stat().st_size for f in workspace.rglob("*") if f.is_file())

    def get_all_workspace_sizes(self) -> Dict[str, int]:
        """Get sizes of all current workspaces.

        获取所有当前工作区的大小.

        Returns:
            Mapping of repo_full_name -> size in bytes.
             repo_full_name -> 字节大小的映射.
        """
        sizes: Dict[str, int] = {}
        for item in self.base_temp_dir.iterdir():
            if item.is_dir():
                name = item.name.replace("_", "/", 1)
                size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                sizes[name] = size
        return sizes


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string.

    以ISO 8601字符串形式返回当前UTC时间.
    """
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["FileManager"]
