#!/usr/bin/env python3
"""
Environment Check Script for Similar Project Rating System.

A standalone script to check all system dependencies and services
before running the main analysis pipeline.

相似项目评分系统的环境检查脚本.
一个独立的脚本,用于在运行主分析流水线前检查所有系统依赖项和服务.
"""

import asyncio
import argparse
import sys
import os

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    """Main entry point for environment check script."""
    parser = argparse.ArgumentParser(
        description="Environment Check for Similar Project Rating System",
        epilog=(
            "Examples:\n"
            "  python scripts/env_check.py                    # Basic check\n"
            "  python scripts/env_check.py --config configs/config.yaml  # With custom config\n"
            "  python scripts/env_check.py --strict           # Strict mode\n"
            "  python scripts/env_check.py --report my_report.json  # Save report\n"
        )
    )
    
    parser.add_argument("-c", "--config", type=str, default="configs/config.yaml",
                        help="Path to configuration file (default: configs/config.yaml)")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as failures (strict mode)")
    parser.add_argument("--no-ai", action="store_true",
                        help="Skip AI provider checks")
    parser.add_argument("--no-gitreverse", action="store_true",
                        help="Skip GitReverse checks")
    parser.add_argument("--report", type=str, default=None,
                        help="Save detailed report to JSON file")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed output for each check")
    
    args = parser.parse_args()
    
    # Try to import the environment checker
    try:
        from src.utils.environment_checker import EnvironmentChecker
        
        # Initialize checker
        checker = EnvironmentChecker(args.config)
        
        print("=" * 80)
        print("SIMILAR PROJECT RATING SYSTEM - ENVIRONMENT CHECK")
        print("=" * 80)
        
        # Load configuration
        config = None
        try:
            import yaml
            with open(args.config, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"[INFO] Using default settings (config load failed: {e})")
        
        # Run checks
        print("\n[1/4] Checking Python environment...")
        
        # Run package checks (synchronous)
        checker_results = await checker.run_checks(
            config=config,
            check_ai_provider=not args.no_ai,
            check_gitreverse=not args.no_gitreverse
        )
        
        # Print results
        print("\n[2/4] Checking external services...")
        print("[3/4] Compiling results...")
        
        checker.print_report()
        
        print("\n[4/4] Generating final assessment...")
        
        # Save report if requested
        if args.report:
            import json
            try:
                report_data = {
                    "summary": checker.summary(),
                    "results": [r.to_dict() for r in checker_results]
                }
                with open(args.report, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False)
                print(f"\n[INFO] Detailed report saved to: {args.report}")
            except Exception as e:
                print(f"[ERROR] Failed to save report: {e}")
        
        # Determine exit code
        has_critical = checker.has_critical_failures()
        summary = checker.summary()
        
        if has_critical:
            print("\n❌ [FAILURE] Critical environment issues found.")
            print("   The system cannot run until these issues are resolved.")
            print("\n   Suggestions:")
            print("   1. Check the suggestions above for each failed item")
            print("   2. Ensure required Python packages are installed")
            print("   3. Check network connectivity and API access")
            sys.exit(1)
        
        elif args.strict and summary['warnings'] > 0:
            print("\n⚠️ [STRICT MODE FAILURE] Warnings treated as failures in strict mode.")
            print("   To bypass, run without --strict flag.")
            sys.exit(1)
        
        elif summary['warnings'] > 0:
            print("\n⚠️ [WARNING] Non-critical issues detected.")
            print("   The system can run, but some features may be limited.")
            print("\n   To resolve:")
            print("   - Review the warnings above")
            print("   - Consider fixing them for optimal performance")
            sys.exit(0)
        
        else:
            print("\n✅ [SUCCESS] All environment checks passed!")
            print("   The system is ready to run.")
            sys.exit(0)
        
    except ImportError as e:
        print(f"[ERROR] Failed to import environment checker: {e}")
        print("\n   This usually indicates missing dependencies.")
        print("\n   Solution:")
        print("   1. Run: pip install -r requirements/base.txt -r requirements/ai.txt")
        print("   2. Ensure you're in the correct directory")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Environment check failed unexpectedly: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())