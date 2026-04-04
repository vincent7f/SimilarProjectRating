"""
Git Helper - Git operations wrapper for auto-commit functionality.

Implements automatic git commit after successful steps according to the design spec:
- Each step should be automatically committed to GitHub
- Support git worktree for parallel development

Git助手 - Git操作封装，用于自动提交功能。

根据设计规范实现成功步骤后的自动git提交：
- 每一步都应自动提交到GitHub
- 支持git worktree进行并行开发
"""

import asyncio
import subprocess
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class GitHelper:
    """Git operations helper for auto-commit functionality."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.git_path = self.repo_path / '.git'
        self.worktrees_dir = self.repo_path / '.git' / 'worktrees'
        
    async def ensure_git_initialized(self) -> bool:
        """Ensure git repository is properly initialized."""
        if not self.git_path.exists():
            logger.warning("Git repository not initialized at %s", self.repo_path)
            return False
        return True
    
    async def get_current_branch(self) -> str:
        """Get current git branch."""
        try:
            result = await self._run_git_command(["branch", "--show-current"])
            return result.strip()
        except Exception as e:
            logger.warning(f"Failed to get current branch: {e}")
            return "main"
    
    async def get_changed_files(self) -> List[str]:
        """Get list of changed/untracked files."""
        try:
            # Get unstaged changes
            result = await self._run_git_command(["status", "--porcelain"])
            files = []
            for line in result.strip().split('\n'):
                if line:
                    # Parse git status output: XY path
                    status, path = line[:2], line[3:]
                    files.append((status.strip(), path.strip()))
            return files
        except Exception as e:
            logger.warning(f"Failed to get changed files: {e}")
            return []
    
    async def auto_commit_step(self, 
                              step_name: str,
                              step_description: str,
                              include_files: Optional[List[str]] = None,
                              force_add: bool = False) -> bool:
        """
        Automatically commit changes for a completed step.
        
        Args:
            step_name: Identifier for the step (e.g., "step-1-1")
            step_description: Human-readable description of what was done
            include_files: Specific files to include (None for all)
            force_add: Whether to force add even if .gitignore would exclude
        
        Returns:
            bool: True if commit successful, False otherwise
        """
        try:
            if not await self.ensure_git_initialized():
                logger.warning("Git not initialized, skipping auto-commit")
                return False
            
            branch = await self.get_current_branch()
            changed_files = await self.get_changed_files()
            
            if not changed_files and not force_add:
                logger.info("No changes detected for step %s", step_name)
                return True
            
            # Stage files
            if include_files:
                # Add specific files
                for file_path in include_files:
                    await self._run_git_command(["add", file_path])
                logger.info("Staged %d specified files for step %s", len(include_files), step_name)
            else:
                # Add all changes
                await self._run_git_command(["add", "--all"])
                logger.info("Staged all changes for step %s", step_name)
            
            # Check if there are actually changes to commit
            status_result = await self._run_git_command(["status", "--porcelain"])
            if not status_result.strip():
                logger.info("No changes to commit after staging for step %s", step_name)
                return True
            
            # Commit with informative message
            commit_msg = f"[Auto-commit] Step: {step_name} - {step_description}"
            await self._run_git_command(["commit", "-m", commit_msg])
            
            logger.info(
                "Successfully committed step %s on branch %s: %s",
                step_name, branch, step_description
            )
            
            # Optional: push if remote is configured
            # await self._try_push(branch)
            
            return True
            
        except Exception as e:
            logger.error("Auto-commit failed for step %s: %s", step_name, str(e))
            return False
    
    async def create_worktree_for_step(self, step_name: str) -> Optional[str]:
        """
        Create a git worktree for parallel step execution.
        
        Args:
            step_name: Step identifier used for worktree name
            
        Returns:
            Optional[str]: Path to worktree if created, None otherwise
        """
        try:
            worktree_name = f"worktree-{step_name}"
            worktree_path = self.repo_path / ".." / f"{self.repo_path.name}-{worktree_name}"
            
            if not self.worktrees_dir.exists():
                self.worktrees_dir.mkdir(parents=True, exist_ok=True)
            
            # Create worktree
            await self._run_git_command(["worktree", "add", str(worktree_path), "HEAD"])
            
            logger.info("Created worktree for step %s at %s", step_name, worktree_path)
            return str(worktree_path)
            
        except Exception as e:
            logger.warning("Failed to create worktree for step %s: %s", step_name, str(e))
            return None
    
    async def merge_worktree_back(self, worktree_path: str, step_name: str) -> bool:
        """
        Merge changes from a worktree back to main branch.
        
        Args:
            worktree_path: Path to the worktree
            step_name: Step identifier for commit message
            
        Returns:
            bool: True if merge successful, False otherwise
        """
        try:
            # Switch to main branch
            await self._run_git_command(["checkout", "main"])
            
            # Merge worktree branch
            await self._run_git_command(["merge", f"worktree-{step_name}", "--no-ff", "-m", f"Merged worktree for step {step_name}"])
            
            # Cleanup worktree
            await self._run_git_command(["worktree", "remove", worktree_path, "--force"])
            
            logger.info("Successfully merged worktree for step %s", step_name)
            return True
            
        except Exception as e:
            logger.error("Failed to merge worktree for step %s: %s", step_name, str(e))
            return False
    
    async def session_summary_commit(self, 
                                   session_id: str, 
                                   success_count: int, 
                                   failure_count: int,
                                   summary_text: str) -> bool:
        """
        Create a summary commit at the end of a session.
        
        Args:
            session_id: Unique session identifier
            success_count: Number of successful steps
            failure_count: Number of failed steps
            summary_text: Detailed summary text
            
        Returns:
            bool: True if successful
        """
        try:
            commit_msg = (
                f"[Session Summary] {session_id}\n\n"
                f"✅ Success: {success_count}\n"
                f"❌ Failure: {failure_count}\n\n"
                f"Summary:\n{summary_text}"
            )
            
            await self._run_git_command(["add", "--all"])
            await self._run_git_command(["commit", "-m", commit_msg])
            
            logger.info("Session summary committed for session %s", session_id)
            await self._try_push()
            
            return True
            
        except Exception as e:
            logger.error("Failed to commit session summary: %s", str(e))
            return False
    
    async def _run_git_command(self, args: List[str]) -> str:
        """Run git command and return output."""
        cmd = ["git", "-C", str(self.repo_path)] + args
        logger.debug("Running git command: %s", " ".join(cmd))
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Git command failed: {stderr.decode().strip()}")
        
        return stdout.decode().strip()
    
    async def _try_push(self, branch: str = "main") -> bool:
        """Try to push to remote if configured."""
        try:
            # Check if remote exists
            result = await self._run_git_command(["remote"])
            if not result.strip():
                logger.debug("No remote configured, skipping push")
                return False
            
            await self._run_git_command(["push", "origin", branch])
            logger.info("Pushed to remote origin/%s", branch)
            return True
            
        except Exception as e:
            logger.warning("Failed to push to remote: %s (remote may not be configured)", str(e))
            return False


# Default instance for convenience
git_helper: Optional[GitHelper] = None


def get_git_helper(repo_path: Optional[str] = None) -> GitHelper:
    """Get or create global git helper instance."""
    global git_helper
    if git_helper is None:
        if repo_path is None:
            # Try to auto-detect repository root
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                if (parent / '.git').exists():
                    repo_path = str(parent)
                    logger.info("Auto-detected git repo at %s", repo_path)
                    break
            if repo_path is None:
                raise RuntimeError("No git repository found and no repo_path provided")
        
        git_helper = GitHelper(repo_path)
    
    return git_helper


async def auto_commit_current_step(step_name: str, step_description: str) -> bool:
    """
    Convenience function to auto-commit current step.
    
    This is the main entry point for step auto-commit.
    """
    helper = get_git_helper()
    return await helper.auto_commit_step(step_name, step_description)


__all__ = ["GitHelper", "get_git_helper", "auto_commit_current_step"]