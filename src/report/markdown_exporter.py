#!/usr/bin/env python3
"""
Markdown Exporter - Ensures all project outputs are Markdown files.

This module provides mandatory Markdown export functionality for the 
Similar Project Rating System. All analysis results must be saved as 
Markdown (.md) files according to user requirements.

Markdown导出器 - 确保所有项目输出都是Markdown文件。

此模块为相似项目评分系统提供强制性的Markdown导出功能。
根据用户要求，所有分析结果必须保存为Markdown(.md)文件。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from textwrap import dedent

from src.models.analysis import RankedProject
from src.models.repository import Repository
from src.report.generator import ReportGenerator
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MarkdownExporter:
    """Mandatory Markdown export manager for all project outputs.
    
    This class ensures compliance with the requirement that 
    "项目输出的结果，必须是markdown文件" (project outputs must be Markdown files).
    """
    
    def __init__(
        self, 
        output_dir: str = "./data/results",
        include_json_metadata: bool = False,
        bilingual_output: bool = True
    ) -> None:
        """Initialize Markdown exporter.
        
        Args:
            output_dir: Directory to save Markdown reports
            include_json_metadata: Whether to include JSON metadata as comment
            bilingual_output: Whether to include Chinese translations
        """
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.include_json_metadata = include_json_metadata
        self.bilingual_output = bilingual_output
        self.report_generator = ReportGenerator()
        
        logger.info(f"Markdown exporter initialized. Output directory: {self.output_dir}")
    
    def export_ranked_projects(
        self,
        query: str,
        ranked: List[RankedProject],
        session_id: Optional[str] = None,
        duration_seconds: float = 0.0,
        explanation: Optional[Dict[str, Any]] = None,
        format_type: str = "detailed"  # "detailed", "summary", "comparison"
    ) -> Path:
        """Export ranked project analysis results to Markdown file.
        
        This is the primary export function for analysis results.
        
        Args:
            query: User's original search query
            ranked: List of ranked project results
            session_id: Optional session identifier
            duration_seconds: Total analysis duration
            explanation: AI-generated explanation metadata
            format_type: Type of Markdown format to generate
        
        Returns:
            Path to the generated Markdown file
        """
        # Generate filename based on query and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_'))[:50]
        safe_query = safe_query.replace(" ", "_").replace("-", "_").lower()
        
        if session_id:
            filename = f"analysis_session_{session_id}_{timestamp}_{safe_query}.md"
        else:
            filename = f"analysis_{timestamp}_{safe_query}.md"
        
        filepath = self.output_dir / filename
        
        # Generate Markdown content based on format type
        if format_type == "summary":
            content = self._generate_summary_report(
                query, ranked, session_id, duration_seconds, explanation
            )
        elif format_type == "comparison":
            content = self._generate_comparison_report(
                query, ranked, session_id, duration_seconds, explanation
            )
        else:  # detailed (default)
            content = self._generate_detailed_report(
                query, ranked, session_id, duration_seconds, explanation
            )
        
        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Markdown report saved: {filepath}")
        logger.info(f"Report contains {len(ranked)} ranked projects, query: '{query}'")
        
        # Also save metadata if requested
        if self.include_json_metadata:
            self._save_metadata(filepath, query, ranked, session_id, explanation)
        
        return filepath
    
    def _generate_detailed_report(
        self,
        query: str,
        ranked: List[RankedProject],
        session_id: Optional[str],
        duration_seconds: float,
        explanation: Optional[Dict[str, Any]]
    ) -> str:
        """Generate detailed Markdown report."""
        timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
        
        # Use the existing report generator for consistency
        markdown_content = self.report_generator.generate_markdown_report(
            query, ranked, explanation, timestamp
        )
        
        # Enhanced with additional information
        enhanced_content = [
            "# Similar Project Rating Report - Detailed Analysis",
            "",
            f"**Query（查询）:** {query}",
            f"**Generated（生成时间）:** {timestamp}",
            f"**Session ID（会话ID）:** {session_id or 'N/A'}",
            f"**Analysis Duration（分析耗时）:** {duration_seconds:.1f} seconds",
            f"**Total Projects Analyzed（总分析项目数）:** {len(ranked)}",
            ""
        ]
        
        if self.bilingual_output:
            enhanced_content.extend([
                "## Executive Summary / 执行摘要",
                ""
            ])
        
        # Add explanation if available
        if explanation:
            if self.bilingual_output:
                enhanced_content.extend([
                    f"**Overview（概览）:** {explanation.get('overview_en', '')}",
                    f"**概览:** {explanation.get('overview_zh', '')}",
                    ""
                ])
            else:
                enhanced_content.extend([
                    f"**Overview:** {explanation.get('overview_en', '')}",
                    ""
                ])
        
        # Add the markdown content
        enhanced_content.append(markdown_content)
        
        # Add detailed breakdown for top projects
        if ranked:
            enhanced_content.extend([
                "",
                "## Top Projects Analysis / 优秀项目分析",
                ""
            ])
            
            for rp in ranked[:5]:  # Top 5 projects
                enhanced_content.extend([
                    f"### **{rp.rank}. {rp.project.full_name}**",
                    f"**Score（得分）:** {rp.score.comprehensive:.1f}/100",
                    f"**Tier（等级）:** {rp.tier.value}",
                    f"**Stars（⭐⭐）:** {rp.project.stars:,}",
                    f"**Language（语言）:** {rp.project.primary_language or 'N/A'}",
                    f"**URL:** [{rp.project.html_url or rp.project.url}]({rp.project.html_url or rp.project.url})",
                    ""
                ])
                
                if rp.highlights:
                    enhanced_content.append("**Strengths（优势）:**")
                    for highlight in rp.highlights[:3]:  # Top 3 strengths
                        enhanced_content.append(f"- {highlight}")
                    enhanced_content.append("")
                
                if rp.concerns:
                    enhanced_content.append("**Concerns（关注点）:**")
                    for concern in rp.concerns[:3]:  # Top 3 concerns
                        enhanced_content.append(f"- {concern}")
                    enhanced_content.append("")
        
        # Add methodology section
        enhanced_content.extend([
            "",
            "## Methodology / 方法论",
            "",
            "### Scoring Dimensions / 评分维度",
            """
1. **Code Quality（代码质量 - 25%）**: Code structure, test coverage, documentation, complexity
2. **Community Activity（社区活跃度 - 20%）**: Recent commits, open issues, contributor count
3. **Functional Completeness（功能完整性 - 18%）**: Feature set, API design, project scope
4. **Project Maturity（项目成熟度 - 15%）**: Version history, release frequency, governance
5. **User Evaluation（用户评价 - 12%）**: Star growth, project popularity, user feedback
6. **Maintainability（可持续性 - 10%）**: Issue resolution time, CI/CD setup, project health

**Total Weight（总权重）:** 100%
            """,
            ""
        ])
        
        # Add tier explanation
        enhanced_content.extend([
            "### Tier System / 等级系统",
            """
- **S Tier（卓越级）**: ≥90 points - Production-ready with excellent documentation
- **A Tier（优秀级）**: 80-89 points - Very solid, suitable for most use cases
- **B Tier（良好级）**: 65-79 points - Good quality, may need some customization
- **C Tier（普通级）**: 50-64 points - Acceptable for specific use cases
- **D Tier（基础级）**: <50 points - Early stage or limited functionality
            """,
            ""
        ])
        
        # Add recommendations
        enhanced_content.extend([
            "## Recommendations / 推荐",
            ""
        ])
        
        if explanation:
            if self.bilingual_output:
                enhanced_content.extend([
                    f"**Conclusion（结论）:** {explanation.get('conclusion_en', '')}",
                    f"**结论:** {explanation.get('conclusion_zh', explanation.get('conclusion_en', ''))}",
                    ""
                ])
            else:
                enhanced_content.extend([
                    f"**Conclusion:** {explanation.get('conclusion_en', '')}",
                    ""
                ])
        
        if ranked:
            top_project = ranked[0]
            enhanced_content.extend([
                f"**Top Recommendation（首选推荐）:** {top_project.project.full_name}",
                f"**Reason（推荐理由）:** {top_project.highlights[0] if top_project.highlights else 'Comprehensive score leader'}",
                ""
            ])
        
        # Footer
        enhanced_content.extend([
            "---",
            "*Generated by Similar Project Rating System / 由相似项目评分系统生成*",
            "*All results are saved as Markdown files as per requirement / 根据要求，所有结果均保存为Markdown文件*",
            f"*Report saved at: {filepath}*",
        ])
        
        return "\n".join(enhanced_content)
    
    def _generate_summary_report(
        self,
        query: str,
        ranked: List[RankedProject],
        session_id: Optional[str],
        duration_seconds: float,
        explanation: Optional[Dict[str, Any]]
    ) -> str:
        """Generate summary Markdown report."""
        timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
        
        content = [
            "# Similar Project Rating - Summary Report",
            "",
            f"## Query: {query}",
            f"**Date:** {timestamp}",
            f"**Session:** {session_id or 'N/A'}",
            f"**Duration:** {duration_seconds:.1f}s",
            f"**Projects:** {len(ranked)}",
            ""
        ]
        
        if ranked:
            content.extend([
                "## Top 3 Recommendations",
                ""
            ])
            
            for rp in ranked[:3]:
                content.extend([
                    f"### {rp.rank}. **{rp.project.full_name}**",
                    f"- **Score:** {rp.score.comprehensive:.1f}/100 | **Tier:** {rp.tier.value}",
                    f"- **Stars:** {rp.project.stars:,} | **Language:** {rp.project.primary_language or 'N/A'}",
                    f"- **URL:** {rp.project.html_url or rp.project.url}",
                    ""
                ])
        
        if explanation and explanation.get('conclusion_en'):
            content.extend([
                "## AI Recommendation",
                "",
                explanation.get('conclusion_en', ''),
                ""
            ])
        
        content.extend([
            "---",
            "*Similar Project Rating System - Markdown Export*",
        ])
        
        return "\n".join(content)
    
    def _generate_comparison_report(
        self,
        query: str,
        ranked: List[RankedProject],
        session_id: Optional[str],
        duration_seconds: float,
        explanation: Optional[Dict[str, Any]]
    ) -> str:
        """Generate comparison table Markdown report."""
        timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
        
        content = [
            "# Similar Project Comparison Report",
            "",
            f"## Query: {query}",
            f"**Date:** {timestamp} | **Projects:** {len(ranked)}",
            ""
        ]
        
        # Comparison table
        content.extend([
            "## Comparison Table",
            "",
            "| Rank | Project | Score | Tier | Stars | Language | Forks | Last Updated |",
            "|------|---------|-------|------|-------|----------|-------|--------------|",
        ])
        
        for rp in ranked:
            repo = rp.project
            last_updated = repo.updated_at[:10] if repo.updated_at else "N/A"
            content.append(
                f"| {rp.rank} | [{repo.full_name}]({repo.html_url}) | "
                f"{rp.score.comprehensive:.1f} | {rp.tier.value} | "
                f"{repo.stars:,} | {repo.primary_language or '-'} | "
                f"{repo.forks or 0} | {last_updated} |"
            )
        
        # Score breakdown for top project
        if ranked:
            top_score = ranked[0].score
            content.extend([
                "",
                "## Score Breakdown (Top Project)",
                "",
                f"**Project:** {ranked[0].project.full_name}",
                f"**Total Score:** {top_score.comprehensive:.1f}/100",
                "",
                "| Dimension | Score | Weight | Weighted Score |",
                "|-----------|-------|--------|----------------|",
                f"| Code Quality | {top_score.code_quality:.1f} | 25% | {top_score.code_quality * 0.25:.1f} |",
                f"| Community Activity | {top_score.community_activity:.1f} | 20% | {top_score.community_activity * 0.20:.1f} |",
                f"| Functional Completeness | {top_score.functional_completeness:.1f} | 18% | {top_score.functional_completeness * 0.18:.1f} |",
                f"| Project Maturity | {top_score.project_maturity:.1f} | 15% | {top_score.project_maturity * 0.15:.1f} |",
                f"| User Evaluation | {top_score.user_evaluation:.1f} | 12% | {top_score.user_evaluation * 0.12:.1f} |",
                f"| Maintainability | {top_score.maintainability:.1f} | 10% | {top_score.maintainability * 0.10:.1f} |",
            ])
        
        content.extend([
            "",
            "---",
            "*Markdown comparison report generated by Similar Project Rating System*",
        ])
        
        return "\n".join(content)
    
    def _save_metadata(
        self,
        markdown_filepath: Path,
        query: str,
        ranked: List[RankedProject],
        session_id: Optional[str],
        explanation: Optional[Dict[str, Any]]
    ) -> None:
        """Save JSON metadata alongside Markdown file."""
        metadata_filepath = markdown_filepath.with_suffix('.json')
        
        metadata = {
            "export_info": {
                "query": query,
                "session_id": session_id,
                "markdown_file": str(markdown_filepath),
                "exported_at": datetime.now().isoformat(),
                "total_projects": len(ranked),
            },
            "top_projects": [
                {
                    "rank": rp.rank,
                    "full_name": rp.project.full_name,
                    "score": rp.score.comprehensive,
                    "tier": rp.tier.value,
                    "url": rp.project.html_url,
                }
                for rp in ranked[:5]
            ]
        }
        
        with open(metadata_filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Metadata saved: {metadata_filepath}")
    
    def export_session_summary(
        self,
        session_id: str,
        success_steps: int,
        failed_steps: int,
        total_duration: float,
        executed_steps: List[Dict[str, Any]],
        experience_entries: List[Dict[str, Any]] = None
    ) -> Path:
        """Export session summary to Markdown file.
        
        Args:
            session_id: Unique session identifier
            success_steps: Number of successful steps
            failed_steps: Number of failed steps
            total_duration: Total session duration in seconds
            executed_steps: List of executed steps with metadata
            experience_entries: Lessons learned from the session
        
        Returns:
            Path to the generated Markdown file
        """
        filename = f"session_summary_{session_id}.md"
        filepath = self.output_dir / filename
        
        timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
        
        content = [
            "# Analysis Session Summary",
            "",
            f"**Session ID:** {session_id}",
            f"**Completed:** {timestamp}",
            f"**Total Duration:** {total_duration:.1f} seconds",
            "",
            "## Execution Summary",
            "",
            f"- ✅ **Successful Steps:** {success_steps}",
            f"- ❌ **Failed Steps:** {failed_steps}",
            f"- 📊 **Success Rate:** {(success_steps / max(1, success_steps + failed_steps)) * 100:.1f}%",
            ""
        ]
        
        if executed_steps:
            content.extend([
                "## Step Execution Details",
                "",
                "| Step ID | Name | Status | Duration | Timestamp |",
                "|---------|------|--------|----------|-----------|",
            ])
            
            for step in executed_steps:
                status_emoji = "✅" if step.get("status") == "completed" else "❌"
                content.append(
                    f"| {step.get('id', 'N/A')} | {step.get('name', 'N/A')} | "
                    f"{status_emoji} | {step.get('duration', 0):.1f}s | "
                    f"{step.get('timestamp', 'N/A')} |"
                )
            
            content.append("")
        
        if experience_entries:
            content.extend([
                "## Lessons Learned",
                "",
                "| Category | Lesson | Impact |",
                "|----------|--------|--------|",
            ])
            
            for exp in experience_entries[:10]:  # Top 10 lessons
                category = exp.get("category", "info")
                lesson = exp.get("lesson", "")[:100]
                impact = exp.get("impact", "medium")
                
                content.append(f"| {category} | {lesson} | {impact} |")
            
            content.append("")
        
        # Recommendations for next session
        content.extend([
            "## Recommendations for Next Session",
            "",
            "1. **Improve Success Rate:** Focus on steps with high failure rates",
            "2. **Optimize Performance:** Address steps with longest duration",
            "3. **Apply Lessons:** Implement improvements based on experience",
            ""
        ])
        
        content.extend([
            "---",
            "*Generated by Similar Project Rating System - Session Manager*",
            f"*Markdown export location: {filepath}*",
        ])
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
        
        logger.info(f"Session summary saved as Markdown: {filepath}")
        return filepath
    
    def ensure_markdown_output(self, filepath: Path) -> bool:
        """Validate that file has .md extension and is valid Markdown."""
        if filepath.suffix.lower() != '.md':
            logger.warning(f"File {filepath} does not have .md extension")
            return False
        
        try:
            # Quick validation - check if file exists and is readable
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1024)  # Read first 1KB
                
                # Basic check for Markdown structure
                if '# ' in content or '## ' in content or '```' in content:
                    return True
                else:
                    logger.warning(f"File {filepath} may not contain valid Markdown syntax")
                    return False
            else:
                logger.warning(f"File {filepath} does not exist")
                return False
                
        except Exception as e:
            logger.error(f"Error validating Markdown file {filepath}: {e}")
            return False


# Global instance for convenience
global_markdown_exporter = None

def get_markdown_exporter() -> MarkdownExporter:
    """Get or create global Markdown exporter instance."""
    global global_markdown_exporter
    if global_markdown_exporter is None:
        global_markdown_exporter = MarkdownExporter()
    return global_markdown_exporter


def export_results_as_markdown(
    query: str,
    ranked_results: List[RankedProject],
    **kwargs
) -> Path:
    """Convenience function for immediate Markdown export.
    
    This is the primary entry point for enforcing Markdown output.
    """
    exporter = get_markdown_exporter()
    return exporter.export_ranked_projects(query, ranked_results, **kwargs)


__all__ = [
    "MarkdownExporter",
    "get_markdown_exporter", 
    "export_results_as_markdown",
]