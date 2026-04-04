"""
Similar Project Rating System - Main Package.

A intelligent GitHub open-source project analysis and comparison system.
This system searches, analyzes, scores, and ranks similar GitHub projects
across multiple dimensions using AI-powered insights.

相似项目评分系统 - 主包。
一个智能的GitHub开源项目分析与比较系统，通过AI驱动的洞察力，
在多个维度上搜索、分析、评分和排名相似的GitHub项目。
"""

__version__ = "0.1.0"
__author__ = "Similar Project Rating Team"

# Lazy imports to avoid circular deps / 延迟导入以避免循环依赖
def _lazy_import():
    from src.pipeline.orchestrator import PipelineOrchestrator
    globals()["PipelineOrchestrator"] = PipelineOrchestrator
