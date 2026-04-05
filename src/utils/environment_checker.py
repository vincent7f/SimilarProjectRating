#!/usr/bin/env python3
"""
Environment Checker for Similar Project Rating System.

Checks all required dependencies and external services before running analysis:
1. Python library dependencies
2. Ollama service availability
3. GitHub API connectivity
4. GitReverse.com connectivity (optional)

相似项目评分系统的环境检查器.
在运行分析前检查所有必需的依赖项和外部服务：
1. Python库依赖
2. Ollama服务可用性
3. GitHub API连接性
4. GitReverse.com连接性(可选)
"""

import asyncio
import importlib.metadata
import importlib.util
import socket
import sys
import subprocess
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass

try:
    import httpx
    import yaml
    from rich.console import Console
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    import logging


class CheckStatus(Enum):
    """Status of an environment check."""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    """Result of a single environment check."""
    name: str
    description: str
    status: CheckStatus
    details: str = ""
    required: bool = True
    suggestion: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "details": self.details,
            "required": self.required,
            "suggestion": self.suggestion
        }


class EnvironmentChecker:
    """Comprehensive environment checker for the Similar Project Rating system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the environment checker.
        
        Args:
            config_path: Path to configuration file (optional).
        """
        self.console = Console() if RICH_AVAILABLE else None
        self.config_path = config_path
        self.config = None
        self.results: List[CheckResult] = []
        
        # Load configuration if available
        if config_path:
            self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            if yaml:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]Warning: Failed to load config: {e}[/yellow]")
            else:
                print(f"Warning: Failed to load config: {e}")
    
    def _check_python_version(self) -> CheckResult:
        """Check if Python version meets requirements."""
        name = "Python Version"
        description = "Minimum Python 3.9+ required"
        
        major, minor = sys.version_info[:2]
        version_str = f"{major}.{minor}"
        
        if major == 3 and minor >= 9:
            status = CheckStatus.PASS
            details = f"Python {version_str} meets requirements"
        else:
            status = CheckStatus.FAIL
            details = f"Python {version_str} is below minimum requirement (3.9+)"
        
        return CheckResult(
            name=name,
            description=description,
            status=status,
            details=details,
            required=True,
            suggestion="Upgrade to Python 3.9 or newer"
        )
    
    def _check_library(self, package_name: str, min_version: Optional[str] = None) -> CheckResult:
        """Check if a Python library is installed."""
        try:
            # Try to get version from metadata (preferred for pyproject.toml)
            version = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            # Fallback to __version__ attribute
            try:
                module = importlib.import_module(package_name)
                version = getattr(module, '__version__', 'unknown')
            except ImportError:
                version = None
        
        if version:
            # Version comparison if min_version specified
            if min_version:
                from packaging import version as packaging_version
                try:
                    current = packaging_version.parse(version)
                    required = packaging_version.parse(min_version)
                    
                    if current >= required:
                        status = CheckStatus.PASS
                        details = f"{package_name} {version} installed (>= {min_version} required)"
                    else:
                        status = CheckStatus.FAIL
                        details = f"{package_name} {version} outdated (>= {min_version} required)"
                        suggestion = f"pip install --upgrade {package_name}>={min_version}"
                except Exception:
                    status = CheckStatus.WARN
                    details = f"{package_name} installed (unable to verify version {min_version} requirement)"
            else:
                status = CheckStatus.PASS
                details = f"{package_name} {version} installed"
        else:
            status = CheckStatus.FAIL
            details = f"{package_name} not installed"
            suggestion = f"pip install {package_name}{f'>={min_version}' if min_version else ''}"
        
        is_required = package_name in ['httpx', 'pyyaml', 'rich']
        
        return CheckResult(
            name=f"Package: {package_name}",
            description=f"Required Python library",
            status=status,
            details=details,
            required=is_required,
            suggestion=suggestion if 'suggestion' in locals() else ""
        )
    
    def _check_httpx_async(self) -> CheckResult:
        """Check if httpx with async support is available."""
        name = "HTTPX Async Support"
        description = "httpx[http2] required for async HTTP requests"
        
        try:
            import httpx
            # Try to create an async client to verify httpx works
            client = httpx.AsyncClient()
            status = CheckStatus.PASS
            details = "httpx with async support available"
        except ImportError as e:
            status = CheckStatus.FAIL
            details = f"httpx not properly installed: {str(e)}"
            suggestion = "pip install 'httpx[http2]'"
        except Exception as e:
            status = CheckStatus.WARN
            details = f"httpx check failed: {str(e)}"
        
        return CheckResult(
            name=name,
            description=description,
            status=status,
            details=details,
            required=True,
            suggestion=suggestion if 'suggestion' in locals() else ""
        )
    
    async def _check_ollama_service(self, api_base: str = "http://localhost:11434") -> CheckResult:
        """Check if Ollama service is running and accessible."""
        name = "Ollama Service"
        description = "Ollama local AI service connection"
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{api_base}/api/tags")
                
                if response.status_code == 200:
                    status = CheckStatus.PASS
                    details = f"Ollama service running at {api_base}"
                else:
                    status = CheckStatus.FAIL
                    details = f"Ollama service at {api_base} returned status {response.status_code}"
                    suggestion = f"Start Ollama with 'ollama serve' or check {api_base}"
        
        except httpx.ConnectError:
            status = CheckStatus.FAIL
            details = f"Cannot connect to Ollama at {api_base}"
            suggestion = "Start Ollama with 'ollama serve' and ensure it's running"
        except Exception as e:
            status = CheckStatus.WARN
            details = f"Ollama check error: {str(e)}"
        
        return CheckResult(
            name=name,
            description=description,
            status=status,
            details=details,
            required=False,  # Only required if using Ollama provider
            suggestion=suggestion if 'suggestion' in locals() else ""
        )
    
    async def _check_github_api(self, token: Optional[str] = None) -> CheckResult:
        """Check GitHub API connectivity."""
        name = "GitHub API"
        description = "GitHub API connectivity and rate limits"
        
        base_url = "https://api.github.com"
        headers = {}
        if token:
            headers["Authorization"] = f"token {token}"
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                # Test rate limit endpoint (doesn't count against rate limit)
                response = await client.get(f"{base_url}/rate_limit")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'resources' in data:
                        core = data['resources'].get('core', {})
                        remaining = core.get('remaining', 0)
                        limit = core.get('limit', 60)
                        
                        if token:
                            if remaining > 0:
                                status = CheckStatus.PASS
                                details = f"GitHub API connected (Token available), Rate limit: {remaining}/{limit}"
                            else:
                                status = CheckStatus.WARN
                                details = f"GitHub API token valid but rate limit exhausted: {remaining}/{limit}"
                                suggestion = "Wait for rate limit reset or use a different token"
                        else:
                            if remaining > 10:
                                status = CheckStatus.WARN
                                details = f"GitHub API connected (No token), Rate limit low: {remaining}/{limit}"
                                suggestion = "Set GITHUB_TOKEN environment variable for higher limits"
                            elif remaining > 0:
                                status = CheckStatus.WARN
                                details = f"GitHub API connected (No token), Rate limit very low: {remaining}/{limit}"
                                suggestion = "Set GITHUB_TOKEN environment variable immediately"
                            else:
                                status = CheckStatus.FAIL
                                details = f"GitHub API anonymous rate limit exhausted: {remaining}/{limit}"
                                suggestion = "Set GITHUB_TOKEN environment variable or wait for reset"
                    else:
                        status = CheckStatus.PASS
                        details = "GitHub API connected (rate limit info not available)"
                else:
                    status = CheckStatus.FAIL
                    details = f"GitHub API returned status {response.status_code}"
                    suggestion = "Check internet connection and GitHub API status"
        
        except httpx.ConnectError:
            status = CheckStatus.FAIL
            details = "Cannot connect to GitHub API"
            suggestion = "Check internet connection and firewall settings"
        except Exception as e:
            status = CheckStatus.WARN
            details = f"GitHub API check error: {str(e)}"
        
        # Additional check for token validity if provided
        if token and status == CheckStatus.PASS:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                    # Make a simple API call to verify token
                    response = await client.get(f"{base_url}/user")
                    if response.status_code != 200:
                        status = CheckStatus.WARN
                        details += f" (Token invalid: status {response.status_code})"
                        suggestion = "Check GITHUB_TOKEN validity"
            except Exception:
                pass
        
        required = True  # GitHub API is always required
        if not token and status == CheckStatus.FAIL:
            # Treat as warning if no token
            status = CheckStatus.WARN
            required = False
        
        return CheckResult(
            name=name,
            description=description,
            status=status,
            details=details,
            required=required,
            suggestion=suggestion if 'suggestion' in locals() else ""
        )
    
    async def _check_gitreverse_service(self, base_url: str = "https://gitreverse.com") -> CheckResult:
        """Check GitReverse.com service connectivity."""
        name = "GitReverse Service"
        description = "GitReverse.com project analysis service"
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/")
                
                if response.status_code < 500:
                    status = CheckStatus.PASS
                    details = f"GitReverse.com accessible at {base_url}"
                else:
                    status = CheckStatus.WARN
                    details = f"GitReverse.com returned status {response.status_code}"
                    suggestion = f"Check {base_url} or disable GitReverse with --disable-gitreverse"
        
        except (httpx.ConnectError, socket.gaierror):
            status = CheckStatus.WARN
            details = f"Cannot connect to GitReverse.com at {base_url}"
            suggestion = "Check internet connection or disable GitReverse with --disable-gitreverse"
        except Exception as e:
            status = CheckStatus.WARN
            details = f"GitReverse check error: {str(e)}"
        
        return CheckResult(
            name=name,
            description=description,
            status=status,
            details=details,
            required=False,  # Optional feature
            suggestion=suggestion if 'suggestion' in locals() else ""
        )
    
    def _check_internet_connectivity(self) -> CheckResult:
        """Check basic internet connectivity."""
        name = "Internet Connectivity"
        description = "Basic internet access for external APIs"
        
        try:
            # Try to resolve a known reliable domain
            socket.gethostbyname("github.com")
            status = CheckStatus.PASS
            details = "Internet connectivity verified"
        except socket.gaierror:
            status = CheckStatus.FAIL
            details = "Cannot resolve external domains (no internet connection)"
            suggestion = "Check network connection and DNS settings"
        except Exception as e:
            status = CheckStatus.WARN
            details = f"Internet connectivity check failed: {str(e)}"
        
        return CheckResult(
            name=name,
            description=description,
            status=status,
            details=details,
            required=True,
            suggestion=suggestion if 'suggestion' in locals() else ""
        )
    
    def _check_file_permissions(self) -> CheckResult:
        """Check if we have write permissions in required directories."""
        name = "File Permissions"
        description = "Write access to output directories"
        
        required_dirs = [
            "./data/results",
            "./logs",
            "./data/cache"
        ]
        
        failed_dirs = []
        import os
        
        for dir_path in required_dirs:
            try:
                # Create directory if it doesn't exist
                os.makedirs(dir_path, exist_ok=True)
                
                # Test write permission
                test_file = os.path.join(dir_path, ".test_write_permission")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                
            except (PermissionError, OSError) as e:
                failed_dirs.append(f"{dir_path}: {str(e)}")
        
        if not failed_dirs:
            status = CheckStatus.PASS
            details = "All required directories have write permissions"
        else:
            status = CheckStatus.FAIL
            details = f"Write permission issues: {', '.join(failed_dirs[:3])}"
            suggestion = "Check directory permissions or run with appropriate user rights"
            if len(failed_dirs) > 3:
                details += f" and {len(failed_dirs)-3} more"
        
        return CheckResult(
            name=name,
            description=description,
            status=status,
            details=details,
            required=True,
            suggestion=suggestion if 'suggestion' in locals() else ""
        )
    
    def _check_required_packages(self) -> List[CheckResult]:
        """Check all required Python packages from requirements files."""
        # Base requirements (from requirements/base.txt)
        base_requirements = {
            'httpx': '0.27.0',
            'pyyaml': '6.0',
            'rich': '13.0',
            'jinja2': '3.1',
            'pydantic': '2.0',
            'aiofiles': '23.0',
            'python-dateutil': '2.8',
            'unzip-it': '0.1.1',
        }
        
        # AI requirements (from requirements/ai.txt)
        ai_requirements = {
            'litellm': '1.35.0',
            'openai': '1.20.0',
            'anthropic': '0.30.0',
        }
        
        results = []
        
        # Check base requirements
        for package, version in base_requirements.items():
            results.append(self._check_library(package, version))
        
        # Check httpx async support
        results.append(self._check_httpx_async())
        
        # Check AI requirements (not required for basic functionality)
        for package, version in ai_requirements.items():
            result = self._check_library(package, version)
            if result.status == CheckStatus.FAIL:
                # Downgrade AI requirements to warnings
                result.status = CheckStatus.WARN
                result.required = False
                result.details = f"{result.details} (AI features may be limited)"
            results.append(result)
        
        return results
    
    async def _check_ai_provider_service(self, provider: str, config: Dict) -> Optional[CheckResult]:
        """Check specific AI provider service based on configuration."""
        if provider == "ollama":
            api_base = config.get('ai', {}).get('api_base', 'http://localhost:11434')
            return await self._check_ollama_service(api_base)
        elif provider == "openai":
            name = "OpenAI API"
            description = "OpenAI API connectivity"
            api_key = config.get('ai', {}).get('api_key', '')
            
            if not api_key:
                return CheckResult(
                    name=name,
                    description=description,
                    status=CheckStatus.WARN,
                    details="No OpenAI API key configured",
                    required=False,
                    suggestion="Set AI_API_KEY environment variable or configure in config.yaml"
                )
            
            # We'll do a basic check by trying to import openai
            # Full validation requires an actual API call
            try:
                import openai
                return CheckResult(
                    name=name,
                    description=description,
                    status=CheckStatus.PASS,
                    details="OpenAI library available, API key configured",
                    required=False
                )
            except ImportError:
                return CheckResult(
                    name=name,
                    description=description,
                    status=CheckStatus.WARN,
                    details="OpenAI library not installed",
                    required=False,
                    suggestion="pip install openai"
                )
        
        return None
    
    async def run_checks(self, 
                         config: Optional[Dict] = None,
                         check_ai_provider: bool = True,
                         check_gitreverse: bool = True) -> List[CheckResult]:
        """
        Run all environment checks.
        
        Args:
            config: Dictionary containing configuration (optional).
            check_ai_provider: Whether to check AI provider services.
            check_gitreverse: Whether to check GitReverse service.
        
        Returns:
            List of CheckResult objects.
        """
        self.results = []
        
        # 1. Basic system checks
        self.results.append(self._check_python_version())
        self.results.append(self._check_internet_connectivity())
        self.results.append(self._check_file_permissions())
        
        # 2. Package checks
        self.results.extend(self._check_required_packages())
        
        # 3. External service checks (async)
        github_token = None
        if config and 'github' in config:
            github_token = config['github'].get('api_token', '')
        elif self.config and 'github' in self.config:
            github_token = self.config['github'].get('api_token', '')
        
        # Check GitHub API
        github_result = await self._check_github_api(github_token)
        self.results.append(github_result)
        
        # Check GitReverse if enabled
        if check_gitreverse:
            gitreverse_url = "https://gitreverse.com"
            if config and 'gitreverse' in config:
                gitreverse_url = config['gitreverse'].get('base_url', gitreverse_url)
            elif self.config and 'gitreverse' in self.config:
                gitreverse_url = self.config['gitreverse'].get('base_url', gitreverse_url)
            
            gitreverse_result = await self._check_gitreverse_service(gitreverse_url)
            self.results.append(gitreverse_result)
        
        # Check AI provider if enabled
        if check_ai_provider:
            effective_config = config or self.config
            if effective_config and 'ai' in effective_config:
                provider = effective_config['ai'].get('provider', 'ollama')
                ai_result = await self._check_ai_provider_service(provider, effective_config)
                if ai_result:
                    self.results.append(ai_result)
        
        return self.results
    
    def has_critical_failures(self) -> bool:
        """Check if there are any critical failures that should stop execution."""
        for result in self.results:
            if result.required and result.status == CheckStatus.FAIL:
                return True
        return False
    
    def summary(self) -> Dict:
        """Generate a summary of all checks."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARN)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAIL)
        critical_failures = self.has_critical_failures()
        
        return {
            "total_checks": total,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "has_critical_failures": critical_failures,
            "can_proceed": not critical_failures
        }
    
    def print_report(self) -> None:
        """Print a formatted report of all checks."""
        summary = self.summary()
        
        if RICH_AVAILABLE:
            self._print_rich_report(summary)
        else:
            self._print_text_report(summary)
    
    def _print_rich_report(self, summary: Dict) -> None:
        """Print a rich-formatted report."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        # Summary panel
        summary_text = f"""
[bold]Total Checks:[/bold] {summary['total_checks']}
[bold green]✓ Passed:[/bold green] {summary['passed']}
[bold yellow]⚠ Warnings:[/bold yellow] {summary['warnings']}
[bold red]✗ Failed:[/bold red] {summary['failed']}
"""
        
        if summary['has_critical_failures']:
            summary_text += "\n[bold red]❌ CRITICAL FAILURES DETECTED - Cannot proceed[/bold red]"
        elif summary['failed'] > 0:
            summary_text += "\n[bold yellow]⚠ Non-critical issues detected - Can proceed with limitations[/bold yellow]"
        else:
            summary_text += "\n[bold green]✅ All checks passed - Ready to proceed[/bold green]"
        
        console.print(Panel(summary_text, title="[bold]Environment Check Summary[/bold]", border_style="blue"))
        
        # Detailed table
        table = Table(title="Detailed Check Results", show_header=True, header_style="bold")
        table.add_column("Name", style="cyan", width=30)
        table.add_column("Status", width=10)
        table.add_column("Description", width=40)
        table.add_column("Details", width=50)
        
        for result in self.results:
            if result.status == CheckStatus.PASS:
                status_text = f"[green]✓ {result.status.value}[/green]"
            elif result.status == CheckStatus.WARN:
                status_text = f"[yellow]⚠ {result.status.value}[/yellow]"
            elif result.status == CheckStatus.FAIL:
                status_text = f"[red]✗ {result.status.value}[/red]"
            else:
                status_text = f"[grey]⏭ {result.status.value}[/grey]"
            
            # Add required indicator
            name_text = f"{result.name} {'[red]*[/red]' if result.required else ''}"
            
            # Truncate details if too long
            details = result.details
            if len(details) > 45:
                details = details[:42] + "..."
            
            table.add_row(name_text, status_text, result.description, details)
        
        console.print(table)
        
        # Show suggestions for failed/warning items
        suggestions = []
        for result in self.results:
            if result.suggestion and result.status in [CheckStatus.FAIL, CheckStatus.WARN]:
                suggestions.append(f"• [yellow]{result.name}:[/yellow] {result.suggestion}")
        
        if suggestions:
            console.print("\n[bold]Suggestions:[/bold]")
            for suggestion in suggestions:
                console.print(suggestion)
    
    def _print_text_report(self, summary: Dict) -> None:
        """Print a plain text report."""
        print("\n" + "="*80)
        print("ENVIRONMENT CHECK SUMMARY")
        print("="*80)
        print(f"Total Checks: {summary['total_checks']}")
        print(f"✓ Passed: {summary['passed']}")
        print(f"⚠ Warnings: {summary['warnings']}")
        print(f"✗ Failed: {summary['failed']}")
        
        if summary['has_critical_failures']:
            print("\n❌ CRITICAL FAILURES DETECTED - Cannot proceed")
        elif summary['failed'] > 0:
            print("\n⚠ Non-critical issues detected - Can proceed with limitations")
        else:
            print("\n✅ All checks passed - Ready to proceed")
        
        print("\n" + "="*80)
        print("DETAILED CHECK RESULTS")
        print("="*80)
        
        for i, result in enumerate(self.results, 1):
            status_marker = {
                CheckStatus.PASS: "✓",
                CheckStatus.WARN: "⚠",
                CheckStatus.FAIL: "✗",
                CheckStatus.SKIP: "⏭"
            }.get(result.status, "?")
            
            required_marker = " *" if result.required else ""
            
            print(f"{i:2d}. {status_marker} {result.name}{required_marker}")
            print(f"    Description: {result.description}")
            print(f"    Status: {result.status.value}")
            print(f"    Details: {result.details}")
            if result.suggestion:
                print(f"    Suggestion: {result.suggestion}")
            print()
        
        # Show suggestions
        suggestions = []
        for result in self.results:
            if result.suggestion and result.status in [CheckStatus.FAIL, CheckStatus.WARN]:
                suggestions.append(result)
        
        if suggestions:
            print("="*80)
            print("SUGGESTIONS")
            print("="*80)
            for result in suggestions:
                print(f"• {result.name}: {result.suggestion}")
        
        print("="*80)


async def main():
    """Command-line entry point for standalone environment check."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check environment for Similar Project Rating System"
    )
    parser.add_argument("-c", "--config", type=str, default="configs/config.yaml",
                        help="Path to configuration file")
    parser.add_argument("--no-ai", action="store_true",
                        help="Skip AI provider checks")
    parser.add_argument("--no-gitreverse", action="store_true",
                        help="Skip GitReverse checks")
    
    args = parser.parse_args()
    
    checker = EnvironmentChecker(args.config)
    print("Running environment checks...")
    await checker.run_checks(
        check_ai_provider=not args.no_ai,
        check_gitreverse=not args.no_gitreverse
    )
    
    checker.print_report()
    
    # Return exit code based on critical failures
    if checker.has_critical_failures():
        print("\nExiting with error due to critical failures.")
        sys.exit(1)
    else:
        print("\nEnvironment check completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())