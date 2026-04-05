#!/usr/bin/env python3
"""
Similar Project Rating System - CLI Entry Point.

A intelligent GitHub open-source project analysis and comparison tool.
Users input natural language queries to search, analyze, score, and rank
similar GitHub projects across multiple dimensions with AI recommendations.

相似项目评分系统 - CLI入口。
一个智能的GitHub开源项目分析与比较工具。用户输入自然语言查询，
即可在多个维度上搜索、分析、评分和排名相似的GitHub项目，并获得AI推荐。
"""

import argparse
import asyncio
import sys
import logging
import uuid
from datetime import datetime
from typing import Optional

# Try to import session manager and git helper for auto-commit functionality
# 尝试导入会话管理器和git助手用于自动提交功能
try:
    from src.utils.session_manager import SessionManager, StepStatus
    from src.utils.git_helper import GitHelper, auto_commit_current_step
    HAS_AUTO_COMMIT = True
except ImportError:
    HAS_AUTO_COMMIT = False
    print("[WARNING] Auto-commit dependencies not available. Install with: pip install -e .")


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Parses and validates all CLI options including query, output format,
    AI provider selection, and verbosity controls.

    解析命令行参数。
    解析并验证所有CLI选项，包括查询、输出格式、AI提供商选择和详细程度控制。

    Args:
        argv: Argument list (defaults to sys.argv[1:]).
              参数列表（默认为sys.argv[1:]）。

    Returns:
        Parsed and validated namespace of arguments.
        解析和验证后的参数命名空间。
    """
    parser = argparse.ArgumentParser(
        prog="similar-project-rating",
        description=(
            "GitHub Similar Project Rating System - Analyze and compare "
            "open-source projects across multiple dimensions.\n"
            "GitHub相似项目评分系统 - 在多个维度上分析和比较开源项目。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python -m similar_project_rating "project management tool"\n'
            '  python -m similar_project_rating "react component library" --max-projects 15\n'
            '  python -m similar_project_rating "database orm" --provider openai --model gpt-4\n'
            "\n"
            "示例:\n"
            '  python -m similar_project_rating "项目管理工具"\n'
            '  python -m similar_project_rating "react组件库" --max-projects 15\n'
            '  python -m similar_project_rating "数据库ORM" --provider openai --model gpt-4\n'
        ),
    )

    # Required: user search query / 必需：用户搜索查询
    parser.add_argument(
        "query",
        type=str,
        help="Natural language query describing the desired project functionality. "
             "描述期望项目功能的自然语言查询。",
    )

    # Optional: configuration / 可选：配置相关
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to custom configuration file (default: configs/config.yaml). "
             "自定义配置文件路径（默认：configs/config.yaml）。",
    )
    parser.add_argument(
        "-n", "--max-projects",
        type=int,
        default=20,
        help="Maximum number of projects to analyze (default: 20). "
             "分析的最大项目数量（默认：20）。",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="./data/results/",
        help="Output directory for reports (default: ./data/results/). "
             "报告的输出目录（默认：./data/results/）。",
    )

    # Optional: AI provider settings / 可选：AI提供商设置
    parser.add_argument(
        "-p", "--provider",
        type=str,
        choices=["ollama", "openai", "litellm"],
        default=None,
        help="AI provider to use (default: from config or ollama). "
             "使用的AI提供商（默认：从配置或ollama）。",
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default=None,
        help="AI model name (default: from config). "
             "AI模型名称（默认：从配置）。",
    )

    # Optional: behavior controls / 可选：行为控制
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose/debug output. "
             "启用详细/调试输出。",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="Disable caching for all API calls. "
             "禁用所有API调用的缓存。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Search only without performing full analysis (preview mode). "
             "仅搜索而不执行完整分析（预览模式）。",
    )
    
    # Auto-commit functionality for step completion
    # 步骤完成后的自动提交功能
    parser.add_argument(
        "--auto-commit",
        action="store_true",
        default=False,
        help="Automatically create git commits after each successful step. "
             "Each commit includes step identifier and description. "
             "在每个成功步骤后自动创建git提交。每个提交包含步骤标识符和描述。",
    )
    parser.add_argument(
        "--no-auto-commit",
        action="store_true",
        default=False,
        help="Disable auto-commit even if configured in settings. "
             "即使设置中启用了也禁用自动提交。",
    )
    parser.add_argument(
        "--use-worktrees",
        action="store_true",
        default=False,
        help="Use git worktrees for parallel step execution. "
             "Each major step runs in its own worktree. "
             "使用git worktrees进行并行步骤执行。每个主要步骤在自己的worktree中运行。",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Identifier for this analysis session (used in commit messages). "
             "If not provided, auto-generated timestamp will be used. "
             "此分析会话的标识符（用于提交消息）。如未提供，将使用自动生成的时间戳。",
    )
    
    # Resume and concurrency functionality for task recovery and parallel execution
    # 用于任务恢复和并行执行的恢复和并发功能
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Enable session resumption from checkpoint. "
             "Requires --session-id of an existing session. "
             "从检查点启用会话恢复。需要现有会话的--session-id。",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        default=False,
        help="Disable resume functionality (force new session). "
             "禁用恢复功能（强制新会话）。",
    )
    parser.add_argument(
        "--max-concurrent-non-ai",
        type=int,
        default=5,
        help="Maximum concurrent non-AI dependent tasks (default: 5). "
             "非AI依赖任务的最大并发数（默认：5）。",
    )
    parser.add_argument(
        "--max-concurrent-ai",
        type=int,
        default=1,
        help="Maximum concurrent AI-dependent tasks (default: 1). "
             "AI依赖任务的最大并发数（默认：1）。",
    )
    parser.add_argument(
        "--disable-parallel-ai",
        action="store_true",
        default=False,
        help="Disable parallel execution for AI tasks (force serial). "
             "禁用AI任务的并行执行（强制串行）。",
    )

    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> int:
    """Execute the main analysis pipeline asynchronously.

    Orchestrates the full workflow:
    1. Initialize configuration and logging
    2. Generate search keywords via AI
    3. Search GitHub for candidate projects
    4. Filter irrelevant projects via AI relevance check
    5. Analyze filtered projects in parallel (code/community/maturity)
    6. Calculate multi-dimensional scores
    7. Rank and generate recommendations
    8. Output reports and session summary
    9. Auto-commit step-by-step if enabled
    10. Task checkpointing and resume support (new)

    异步执行主分析流水线。
    编排完整的工作流程：
    1. 初始化配置和日志
    2. 通过AI生成搜索关键词
    3. 在GitHub上搜索候选项目
    4. 通过AI相关性检查过滤不相关项目
    5. 并行分析过滤后的项目（代码/社区/成熟度）
    6. 计算多维分数
    7. 排名并生成推荐
    8. 输出报告和会话总结
    9. 如已启用，自动提交每个步骤
    10. 任务检查点和恢复支持（新增）

    Args:
        args: Parsed command-line arguments.
              解析后的命令行参数。

    Returns:
        Exit code: 0 for success, non-zero for failure.
        退出码：0表示成功，非零表示失败。
    """
    # Setup auto-commit configuration
    # 设置自动提交配置
    enable_auto_commit = (
        HAS_AUTO_COMMIT and 
        args.auto_commit and 
        not args.no_auto_commit
    )
    
    # Setup resume configuration
    # 设置恢复配置
    enable_resume = args.resume and not args.no_resume
    
    # Setup parallel execution configuration
    # 设置并行执行配置
    max_concurrent_ai = 1 if args.disable_parallel_ai else args.max_concurrent_ai
    max_concurrent_non_ai = args.max_concurrent_non_ai
    
    if enable_auto_commit:
        print("[INFO] Auto-commit mode: ENABLED")
        if args.use_worktrees:
            print("[INFO] Git worktrees mode: ENABLED")
    else:
        print("[INFO] Auto-commit mode: DISABLED")
    
    session_id = args.session_id or f"session-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Initialize resume system
    # 初始化恢复系统
    if enable_resume and args.session_id:
        print(f"[INFO] Resume mode: ENABLED for session {args.session_id}")
        print(f"[INFO] Parallel execution: AI tasks={max_concurrent_ai}, Non-AI tasks={max_concurrent_non_ai}")
    elif enable_resume and not args.session_id:
        print("[WARNING] Resume enabled but no session-id provided. Starting new session.")
        enable_resume = False
    else:
        print("[INFO] Resume mode: DISABLED")
    
    # Initialize session manager for step tracking if auto-commit enabled
    # 如果启用自动提交，初始化会话管理器用于步骤追踪
    session_manager = None
    if enable_auto_commit and HAS_AUTO_COMMIT:
        try:
            session_manager = SessionManager(session_id=session_id)
            await session_manager.initialize()
            print(f"[INFO] Session tracking initialized: {session_id}")
        except Exception as e:
            print(f"[WARNING] Failed to initialize session manager: {e}")
            enable_auto_commit = False
    
    # Initialize git helper for auto-commit if enabled
    # 如果启用，初始化git助手用于自动提交
    git_helper = None
    if enable_auto_commit and HAS_AUTO_COMMIT:
        try:
            git_helper = GitHelper(".")
            await git_helper.ensure_git_initialized()
        except Exception as e:
            print(f"[WARNING] Failed to initialize git helper: {e}")
            enable_auto_commit = False
    
    # Record pipeline starting step
    # 记录流水线起始步骤
    if enable_auto_commit and session_manager:
        await session_manager.record_step(
            step_id="pipeline-start",
            step_name="Pipeline initialization",
            description="Started analysis pipeline for user query",
            status="in_progress",
            metadata={
                "query": args.query,
                "resume_enabled": str(enable_resume),
                "max_concurrent_ai": str(max_concurrent_ai),
                "max_concurrent_non_ai": str(max_concurrent_non_ai)
            }
        )
    
    print(f"[INFO] Query: {args.query}")
    print(f"[INFO] Max projects: {args.max_projects}")
    print(f"[INFO] Output dir: {args.output}")
    if args.provider:
        print(f"[INFO] AI Provider: {args.provider}")
    if args.model:
        print(f"[INFO] AI Model: {args.model}")
    if args.dry_run:
        print("[INFO] Mode: dry-run (search only)")
    print(f"[INFO] Session ID: {session_id}")
    print(f"[INFO] Parallel settings: AI tasks={max_concurrent_ai}, Non-AI tasks={max_concurrent_non_ai}")
    
    try:
        # Import the resume-enabled orchestrator
        # 导入支持恢复的协调器
        try:
            from src.pipeline.orchestrator_resume import run_with_resume
            resume_module_available = True
        except ImportError as e:
            print(f"[WARNING] Resume module not available: {e}")
            from src.pipeline.orchestrator import PipelineOrchestrator
            resume_module_available = False
        
        if resume_module_available and enable_resume:
            # Use resume-enabled pipeline
            # 使用支持恢复的流水线
            print("[INFO] Using resume-enabled pipeline with task checkpointing")
            
            session, resume_manager = await run_with_resume(
                query=args.query,
                session_id=args.session_id or session_id,
                max_projects=args.max_projects,
                max_concurrent_non_ai=max_concurrent_non_ai,
                max_concurrent_ai=max_concurrent_ai,
                dry_run=args.dry_run,
                resume=enable_resume,
                use_enhanced_pipeline=True  # Always use enhanced pipeline for AI/non-AI control
            )
            
            # Check if session resumed from checkpoint
            # 检查是否从检查点恢复
            if resume_manager and resume_manager.state:
                completion_pct = resume_manager.get_completion_percentage()
                next_index, completed_tasks = resume_manager.get_resume_point()
                
                if len(completed_tasks) > 0:
                    print(f"[INFO] Resumed from checkpoint: {completion_pct:.1f}% complete")
                    print(f"[INFO] Previously completed tasks: {', '.join(completed_tasks[:5])}" + 
                          (f" and {len(completed_tasks)-5} more" if len(completed_tasks) > 5 else ""))
            
            status_str = session.status.value if hasattr(session.status, 'value') else str(session.status)
            print(f"[INFO] Analysis completed with status: {status_str}")
            
            if session.report_path:
                print(f"[INFO] Markdown report generated: {session.report_path}")
            
            # Auto-commit after successful pipeline execution
            # 成功执行流水线后自动提交
            if enable_auto_commit and session_manager and session.status == "COMPLETED":
                await _auto_commit_step_if_enabled(
                    git_helper, session_manager, session_id,
                    step_id="pipeline-complete",
                    step_name="Pipeline completion",
                    step_description="Completed analysis pipeline with resume support",
                    metadata={
                        "duration_seconds": str(session.summary.total_duration_seconds if hasattr(session.summary, 'total_duration_seconds') else "0"),
                        "projects_analyzed": str(session.summary.projects_analyzed if hasattr(session.summary, 'projects_analyzed') else "0"),
                        "resume_used": str(enable_resume and len(completed_tasks) > 0)
                    }
                )
            
            return 0 if session.status in ["COMPLETED", "completed", SessionStatus.COMPLETED] else 1
            
        else:
            # Fall back to original pipeline (without resume support)
            # 回退到原始流水线（不支持恢复）
            print("[INFO] Using standard pipeline (resume support not available)")
            
            from src.pipeline.orchestrator import PipelineOrchestrator
            orchestrator = PipelineOrchestrator()
            
            # Override config if CLI arguments provided
            # 如果提供了CLI参数，覆盖配置
            if args.provider or args.model:
                config = load_config()
                if args.provider:
                    config.ai.provider = args.provider
                if args.model:
                    config.ai.model = args.model
                orchestrator = PipelineOrchestrator(config=config)
            
            session = await orchestrator.run(
                query=args.query,
                max_projects=args.max_projects,
                dry_run=args.dry_run
            )
            
            status_str = session.status.value if hasattr(session.status, 'value') else str(session.status)
            print(f"[INFO] Analysis completed with status: {status_str}")
            
            if session.report_path:
                print(f"[INFO] Markdown report generated: {session.report_path}")
            
            # Auto-commit after successful pipeline execution
            # 成功执行流水线后自动提交
            if enable_auto_commit and session_manager and session.status == "COMPLETED":
                await _auto_commit_step_if_enabled(
                    git_helper, session_manager, session_id,
                    step_id="pipeline-complete",
                    step_name="Pipeline completion",
                    step_description="Completed analysis pipeline (standard mode)",
                    metadata={
                        "duration_seconds": str(session.summary.total_duration_seconds if hasattr(session.summary, 'total_duration_seconds') else "0"),
                        "projects_analyzed": str(session.summary.projects_analyzed if hasattr(session.summary, 'projects_analyzed') else "0")
                    }
                )
            
            return 0 if session.status in ["COMPLETED", "completed", SessionStatus.COMPLETED] else 1
            
    except Exception as e:
        print(f"[ERROR] Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Auto-commit for failed pipeline
        # 失败的流水线自动提交
        if enable_auto_commit and session_manager:
            await _auto_commit_step_if_enabled(
                git_helper, session_manager, session_id,
                step_id="pipeline-failed",
                step_name="Pipeline failure",
                step_description="Pipeline execution failed",
                status="failed",
                metadata={"error": str(e)}
            )
        
        return 1


async def _auto_commit_step_if_enabled(
    git_helper: Optional["GitHelper"],
    session_manager: Optional["SessionManager"],
    session_id: str,
    step_id: str,
    step_name: str,
    step_description: str,
    include_files: Optional[List[str]] = None,
) -> bool:
    """Helper to auto-commit a step if auto-commit is enabled and configured."""
    if not git_helper or not session_manager:
        return False
    
    try:
        # Record step start
        await session_manager.record_step_start(
            step_id=step_id,
            step_name=step_name,
            description=f"{step_name}: {step_description}"
        )
        
        # Perform the actual step work would be here...
        # 实际执行步骤的代码会在这里...
        
        # Auto-commit the step
        success = await git_helper.auto_commit_step(
            step_name=step_id,
            step_description=f"{step_name}: {step_description}",
            include_files=include_files,
            force_add=False
        )
        
        if success:
            await session_manager.record_step_completion(
                step_id=step_id,
                status="completed",
                metadata={"auto_committed": True}
            )
        else:
            await session_manager.record_step_completion(
                step_id=step_id,
                status="failed",
                metadata={"auto_committed": False, "error": "Auto-commit failed"}
            )
        
        return success
        
    except Exception as e:
        print(f"[ERROR] Auto-commit helper error: {e}")
        return False


def main(argv: Optional[list] = None) -> int:
    """Synchronous entry point wrapping the async main function.

    Synchronous wrapper that sets up and tears down the async event loop
    around the main pipeline execution.

    同步入口函数，包装异步main函数。
    在主流水线执行周围设置和清理异步事件循环。

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).
              命令行参数（默认为sys.argv[1:]）。

    Returns:
        Exit code passed from async_main.
        从async_main传递的退出码。
    """
    args = parse_args(argv)
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    sys.exit(main())
