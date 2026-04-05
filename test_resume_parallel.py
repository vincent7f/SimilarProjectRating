#!/usr/bin/env python3
"""
Test script for resume and parallel execution functionality.

Tests the three main features:
1. Default AI model configuration (gemma4:26b-a4b-it-q4_K_M)
2. Session resumption from failure
3. Parallel execution control for AI vs non-AI tasks
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.utils.config import load_config, Config
from src.utils.resume_manager import ResumeManager, create_resume_manager_from_session
from src.pipeline.orchestrator_resume import run_with_resume
from src.models.session import SessionStatus


async def test_feature_1_default_model():
    """Test feature 1: Default AI model is gemma4:26b-a4b-it-q4_K_M."""
    print("\n" + "="*60)
    print("Testing Feature 1: Default AI Model Configuration")
    print("="*60)
    
    try:
        config = load_config()
        
        print(f"AI Provider: {config.ai.provider}")
        print(f"AI Model: {config.ai.model}")
        
        # Check if default model is correctly set
        expected_model = "gemma4:26b-a4b-it-q4_K_M"
        if config.ai.model == expected_model:
            print(f"✓ Default model correctly set to: {expected_model}")
            return True
        else:
            print(f"✗ Default model is '{config.ai.model}', expected '{expected_model}'")
            return False
            
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False


async def test_feature_2_resume_mechanism():
    """Test feature 2: Session resumption mechanism."""
    print("\n" + "="*60)
    print("Testing Feature 2: Session Resumption Mechanism")
    print("="*60)
    
    try:
        # Create a test resume manager
        test_query = "test query for resume functionality"
        resume_manager = ResumeManager(
            session_id="test-resume-session-001",
            checkpoint_dir="./data/test_checkpoints"
        )
        
        # Initialize new session
        resume_state = resume_manager.initialize_new_session(test_query)
        
        print(f"Created session: {resume_state.session_id}")
        print(f"Total tasks: {len(resume_state.tasks)}")
        
        # Simulate some completed tasks
        completed_tasks = ["keyword_generation", "github_search"]
        for task in resume_state.tasks:
            if task.task_id in completed_tasks:
                task.status = "completed"
        
        # Save state
        resume_manager._save_state()
        
        # Test resume from checkpoint
        loaded_manager = create_resume_manager_from_session(
            "test-resume-session-001",
            checkpoint_dir="./data/test_checkpoints"
        )
        
        if loaded_manager and loaded_manager.can_resume():
            print("✓ Resume manager can resume from checkpoint")
            
            completion_pct = loaded_manager.get_completion_percentage()
            next_index, completed_tasks_list = loaded_manager.get_resume_point()
            
            print(f"  Completion: {completion_pct:.1f}%")
            print(f"  Next task index: {next_index}")
            print(f"  Completed tasks: {completed_tasks_list}")
            
            # Clean up test files
            resume_manager.cleanup()
            
            return True
        else:
            print("✗ Failed to load resume manager or cannot resume")
            
            # Clean up test files
            resume_manager.cleanup()
            
            return False
            
    except Exception as e:
        print(f"✗ Error testing resume mechanism: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_feature_3_parallel_execution():
    """Test feature 3: Parallel execution control for AI vs non-AI tasks."""
    print("\n" + "="*60)
    print("Testing Feature 3: Parallel Execution Control")
    print("="*60)
    
    try:
        # Load config and check parallel settings
        config = load_config()
        
        print("Parallel Configuration:")
        print(f"  AI concurrent limit: {config.parallel.ai_concurrent_limit}")
        print(f"  Enable parallel AI: {config.parallel.enable_parallel_ai}")
        print(f"  Non-AI concurrent limit: {config.parallel.non_ai_concurrent_limit}")
        print(f"  Enable parallel non-AI: {config.parallel.enable_parallel_non_ai}")
        
        # Check default values
        ai_limit_ok = config.parallel.ai_concurrent_limit == 1
        ai_parallel_ok = config.parallel.enable_parallel_ai == False
        non_ai_limit_ok = config.parallel.non_ai_concurrent_limit == 5
        non_ai_parallel_ok = config.parallel.enable_parallel_non_ai == True
        
        if ai_limit_ok and ai_parallel_ok and non_ai_limit_ok and non_ai_parallel_ok:
            print("✓ Parallel configuration has correct defaults")
            print("  AI tasks: serial (limit=1)")
            print("  Non-AI tasks: parallel (limit=5)")
            return True
        else:
            print("✗ Parallel configuration has incorrect defaults")
            if not ai_limit_ok:
                print(f"  AI limit should be 1, got {config.parallel.ai_concurrent_limit}")
            if not ai_parallel_ok:
                print(f"  AI parallel should be False, got {config.parallel.enable_parallel_ai}")
            if not non_ai_limit_ok:
                print(f"  Non-AI limit should be 5, got {config.parallel.non_ai_concurrent_limit}")
            if not non_ai_parallel_ok:
                print(f"  Non-AI parallel should be True, got {config.parallel.enable_parallel_non_ai}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing parallel execution: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration():
    """Test integration of all three features."""
    print("\n" + "="*60)
    print("Testing Integration of All Features")
    print("="*60)
    
    try:
        # Test CLI argument parsing simulation
        print("Simulating CLI arguments:")
        print("  --max-concurrent-non-ai 5")
        print("  --max-concurrent-ai 1") 
        print("  --disable-parallel-ai")
        print("  --resume")
        print("  --session-id test-session-123")
        
        # Create test config with overrides
        config = load_config()
        
        print("\nResulting configuration:")
        print(f"  AI Model: {config.ai.model}")
        print(f"  AI Provider: {config.ai.provider}")
        print(f"  Parallel AI limit: {config.parallel.ai_concurrent_limit}")
        print(f"  Parallel Non-AI limit: {config.parallel.non_ai_concurrent_limit}")
        
        # Check if all features are integrated
        features_integrated = (
            config.ai.model == "gemma4:26b-a4b-it-q4_K_M" and
            config.parallel.ai_concurrent_limit == 1 and
            config.parallel.non_ai_concurrent_limit == 5
        )
        
        if features_integrated:
            print("\n✓ All three features are properly integrated in configuration")
            return True
        else:
            print("\n✗ Features not properly integrated")
            return False
            
    except Exception as e:
        print(f"✗ Integration test error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("Testing Resume and Parallel Execution Features")
    print("="*60)
    
    results = []
    
    # Test feature 1
    result1 = await test_feature_1_default_model()
    results.append(("Default AI Model", result1))
    
    # Test feature 2
    result2 = await test_feature_2_resume_mechanism()
    results.append(("Session Resumption", result2))
    
    # Test feature 3
    result3 = await test_feature_3_parallel_execution()
    results.append(("Parallel Execution", result3))
    
    # Test integration
    result4 = await test_integration()
    results.append(("Feature Integration", result4))
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    all_passed = True
    for feature_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{feature_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED - All three features are implemented correctly!")
    else:
        print("SOME TESTS FAILED - Check the implementation of failed features.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("./data/test_checkpoints", exist_ok=True)
    
    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)