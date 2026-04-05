#!/usr/bin/env python3
"""
Test GitReverse.com integration functionality.

This script tests the GitReverse client, prompt analyzer, and adaptive pipeline
to ensure proper integration with the existing code analysis system.

测试GitReverse.com集成功能。
此脚本测试GitReverse客户端、prompt分析器和自适应流水线，
确保与现有代码分析系统的正确集成。
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.search.gitreverse_client import GitReverseClient, get_gitreverse_prompt_for_repo
from src.analysis.prompt_analyzer import PromptAnalyzer
from src.analysis.adaptive_pipeline import AdaptiveAnalysisPipeline
from src.models.repository import Repository
from src.utils.config import Config, GitReverseConfig, AIConfig


async def test_gitreverse_client():
    """Test GitReverse client fetching."""
    print("=" * 60)
    print("Testing GitReverse Client...")
    print("=" * 60)
    
    # Create test repository
    test_repo = Repository(
        full_name="nearai/ironclaw",
        name="ironclaw",
        owner="nearai",
        description="A sample project to test GitReverse integration",
        language="Python",
        stars=500,
        forks=100,
        watchers=50,
        issues_count=10,
        open_issues_count=2,
        days_since_last_push=30,
        license_info="MIT",
        topics=["machine-learning", "python", "ai"],
        url="https://github.com/nearai/ironclaw"
    )
    
    # Test with default config
    client = GitReverseClient()
    
    try:
        # Test URL conversion
        gitreverse_url = client._github_url_to_gitreverse_url(test_repo.full_name)
        print(f"✓ GitHub URL converted to GitReverse URL: {gitreverse_url}")
        
        # Test fetching prompt (this may fail if network/API issue)
        print(f"\nFetching prompt for {test_repo.full_name}...")
        prompt = await client.get_project_prompt(test_repo)
        
        if prompt:
            print(f"✓ Successfully fetched GitReverse prompt")
            print(f"  Prompt length: {len(prompt)} characters")
            print(f"  First 200 chars: {prompt[:200]}...")
        else:
            print(f"✗ Failed to fetch prompt (will use fallback in production)")
            print(f"  This is expected if GitReverse.com is not accessible")
        
        await client.close()
        
    except Exception as e:
        print(f"✗ GitReverse client test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_prompt_analyzer():
    """Test prompt-based code analyzer."""
    print("\n" + "=" * 60)
    print("Testing Prompt Analyzer...")
    print("=" * 60)
    
    # Create test repository
    test_repo = Repository(
        full_name="django/django",
        name="django",
        owner="django",
        description="The Web framework for perfectionists with deadlines.",
        language="Python",
        stars=75000,
        forks=28000,
        watchers=5000,
        issues_count=2000,
        open_issues_count=100,
        days_since_last_push=1,
        license_info="BSD",
        topics=["web-framework", "python", "django"],
        url="https://github.com/django/django"
    )
    
    # Configure to enable GitReverse but with fallback
    gitreverse_config = GitReverseConfig(
        enabled=True,
        fallback_to_code=True,
        timeout_seconds=10
    )
    
    # Configure AI
    ai_config = AIConfig(
        provider="ollama",
        model="gemma4:26b-a4b-it-q4_K_M",
        temperature=0.3
    )
    
    # Create prompt analyzer
    analyzer = PromptAnalyzer(config=gitreverse_config, ai_config=ai_config)
    
    try:
        print(f"Analyzing {test_repo.full_name} using GitReverse prompt...")
        
        # This will try to fetch from GitReverse, then fall back to heuristic scoring
        metrics = await analyzer.analyze(test_repo)
        
        print(f"✓ Prompt analysis completed")
        print(f"  Overall score: {metrics.overall_score:.1f}/100")
        print(f"  Code style score: {metrics.code_style_score:.1f}/100")
        print(f"  Test coverage: {metrics.test_coverage:.1f}/100")
        print(f"  Has tests: {metrics.has_tests}")
        print(f"  Dependency count: {metrics.dependency_count}")
        print(f"  Document completeness: {metrics.doc_completeness:.1f}/100")
        print(f"  Architecture score: {metrics.architecture_score:.1f}/100")
        
        if metrics.errors:
            print(f"  Errors: {metrics.errors}")
        
        await analyzer.close()
        
    except Exception as e:
        print(f"✗ Prompt analyzer test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_adaptive_pipeline():
    """Test adaptive pipeline that chooses between prompt and code analysis."""
    print("\n" + "=" * 60)
    print("Testing Adaptive Pipeline...")
    print("=" * 60)
    
    # Load config
    try:
        config = Config.from_yaml("configs/config.yaml")
        # Enable GitReverse for this test
        config.gitreverse.enabled = True
        config.gitreverse.fallback_to_code = True
        
        print(f"Configuration loaded with GitReverse: {config.gitreverse.enabled}")
        
        # Create two test repositories: one popular (likely good for prompt), one less known
        repos = [
            Repository(
                full_name="facebook/react",
                name="react",
                owner="facebook",
                description="A declarative, efficient, and flexible JavaScript library for building user interfaces.",
                language="JavaScript",
                stars=220000,
                forks=46000,
                watchers=10000,
                issues_count=1500,
                open_issues_count=200,
                days_since_last_push=5,
                license_info="MIT",
                topics=["react", "javascript", "ui", "frontend"],
                url="https://github.com/facebook/react"
            ),
            Repository(
                full_name="small-org/small-project",
                name="small-project",
                owner="small-org",
                description="A small utility library",
                language="Python",
                stars=15,
                forks=3,
                watchers=5,
                issues_count=2,
                open_issues_count=0,
                days_since_last_push=365,
                license_info=None,
                topics=["utility", "python"],
                url="https://github.com/small-org/small-project"
            )
        ]
        
        # Create adaptive pipeline
        pipeline = AdaptiveAnalysisPipeline(
            config=config,
            parallel_analysis=True,
            max_concurrent=2  # Process both repos concurrently
        )
        
        print(f"Analyzing {len(repos)} repositories with adaptive pipeline...")
        print(f"GitReverse enabled: {config.gitreverse.enabled}")
        
        results = await pipeline.analyze_batch(repos)
        
        print(f"\n✓ Adaptive pipeline analysis completed for {len(results)} repositories")
        
        for i, result in enumerate(results):
            repo = repos[i]
            print(f"\n  Repository: {repo.full_name}")
            print(f"    Overall score: {result.overall_score:.1f}/100")
            print(f"    Analysis duration: {result.analysis_duration_ms}ms")
            
            # Check metadata for analysis method used
            if hasattr(result, 'metadata') and result.metadata:
                method = result.metadata.get('analysis_method', 'unknown')
                used_prompt = result.metadata.get('used_prompt_analyzer', False)
                used_code = result.metadata.get('used_code_analyzer', False)
                
                print(f"    Analysis method: {method}")
                print(f"    Used prompt analyzer: {used_prompt}")
                print(f"    Used code analyzer: {used_code}")
            
            # Show statistics from pipeline
            print(f"    Pipeline stats: prompt_analyses={pipeline.stats['prompt_analyses']}, "
                  f"code_analyses={pipeline.stats['code_analyses']}, "
                  f"fallbacks={pipeline.stats['fallbacks']}")
        
        # Print overall statistics
        total_analyses = len(repos)
        prompt_percentage = (pipeline.stats['prompt_analyses'] / total_analyses) * 100 if total_analyses > 0 else 0
        
        print(f"\n  Overall statistics:")
        print(f"    Prompt analyses: {pipeline.stats['prompt_analyses']}/{total_analyses} "
              f"({prompt_percentage:.1f}%)")
        print(f"    Code analyses: {pipeline.stats['code_analyses']}/{total_analyses}")
        print(f"    Fallbacks: {pipeline.stats['fallbacks']}")
        print(f"    Total duration: {pipeline.stats['total_duration_ms']}ms")
        
        await pipeline.close()
        
    except Exception as e:
        print(f"✗ Adaptive pipeline test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    print("GitReverse Integration Test Suite")
    print("=" * 60)
    
    # Test 1: GitReverse client
    await test_gitreverse_client()
    
    # Test 2: Prompt analyzer
    await test_prompt_analyzer()
    
    # Test 3: Adaptive pipeline
    await test_adaptive_pipeline()
    
    print("\n" + "=" * 60)
    print("Test suite completed!")
    print("=" * 60)
    
    print("\nUsage examples with GitReverse:")
    print("1. Enable GitReverse globally (config.yaml):")
    print('   gitreverse:')
    print('     enabled: true')
    print('     fallback_to_code: true')
    print('')
    print("2. Force GitReverse via CLI:")
    print('   python src/main.py "web framework" --use-gitreverse')
    print('')
    print("3. Disable GitReverse:")
    print('   python src/main.py "web framework" --disable-gitreverse')
    print('')
    print("4. Disable fallback (strict GitReverse-only):")
    print('   python src/main.py "web framework" --use-gitreverse --no-gitreverse-fallback')


if __name__ == "__main__":
    asyncio.run(main())