"""
Explainer - Bilingual Natural Language Explanation Generator.

Produces human-readable explanations comparing analyzed projects, including
strengths, weaknesses, use case recommendations, and actionable advice.
Outputs are generated in both Chinese and English for accessibility.

解释生成器 - 双语自然语言解释生成器.
生成比较分析项目的可读性解释,包括优势,弱点,用例建议
和可行建议.输出同时以中文和英文生成以提高可访问性.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.ai.llm_client import LLMClient
from src.models.analysis import ComparisonTable, RankedProject
from src.models.repository import Repository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Explainer:
    """Bilingual explanation generator for project analysis results.

    Transforms structured comparison data into natural language narratives
    that explain why certain projects are recommended over others, what their
    trade-offs are, and how users should make their final decision.

    用于项目分析结果的双语解释生成器.
将结构化比较数据转换为自然语言叙述,
解释为什么推荐某些项目而非其他项目,它们的权衡是什么,
以及用户应如何做出最终决定.

    Attributes:
        llm_client: LLM client for generating explanations.
                   用于生成解释的LLM客户端.
        language: Primary output language ('bilingual', 'english', 'chinese').
                 主要输出语言('bilingual','english','chinese').
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        language: str = "bilingual",
    ) -> None:
        """Initialize explainer with configuration.

        使用配置初始化解释生成器.

        Args:
            llm_client: LLM client for AI-generated explanations (optional).
                      用于AI生成解释的LLM客户端(可选).
            language: Output language mode.
                     输出语言模式.
        """
        self.llm_client = llm_client
        self.language = language

    async def explain_comparison(
        self,
        ranked_projects: List[RankedProject],
        query: str,
        include_comparison_table: bool = True,
    ) -> Dict[str, Any]:
        """Generate a full bilingual comparison report.

        生成完整的双语比较报告.

        Args:
            ranked_projects: Sorted list of ranked projects to compare.
                           要比较的已排序列表.
            query: The user's original search intent.
                  用户原始搜索意图.
            include_comparison_table: Whether to embed a metrics table.
                                    是否嵌入指标表格.

        Returns:
            Dictionary with report sections: overview, details, conclusion.
             包含报告章节的字典:overview,details,conclusion.
        """
        if not ranked_projects:
            return {
                "overview_en": "No projects were found for comparison.",
                "overview_zh": "未找到可供比较的项目.",
                "details": [],
                "conclusion_en": "",
                "conclusion_zh": "",
            }

        # Build structured comparison data / 构建结构化比较数据
        report: Dict[str, Any] = {
            "query": query,
            "total_projects": len(ranked_projects),
            "top_pick": ranked_projects[0].project.full_name if ranked_projects else "",
            "overview_en": self._build_overview_en(ranked_projects),
            "overview_zh": self._build_overview_zh(ranked_projects),
            "details": self._build_project_details(ranked_projects),
            "comparison_table": (
                self._build_comparison_table(ranked_projects)
                if include_comparison_table
                else None
            ),
            "conclusion_en": "",
            "conclusion_zh": "",
        }

        # Use AI for enhanced conclusions / 使用AI增强结论
        if self.llm_client and len(ranked_projects) <= 10:
            report.update(await self._generate_ai_conclusion(ranked_projects, query))
        else:
            report["conclusion_en"] = self._template_conclusion_en(ranked_projects)
            report["conclusion_zh"] = self._template_conclusion_zh(ranked_projects)

        logger.info(
            "module=ai", operation="explain_complete",
            params={"projects_analyzed": len(ranked_projects), "query": query},
        )
        return report

    async def explain_single_project(
        self,
        ranked: RankedProject,
        alternatives: Optional[List[RankedProject]] = None,
    ) -> Dict[str, str]:
        """Generate a focused explanation for a single recommended project.

        为单个推荐项目生成聚焦的解释.

        Args:
            ranked: The project to explain.
                  要解释的项目.
            alternatives: Other projects for context (optional).
                        其他上下文项目(可选).

        Returns:
            Dictionary with 'english' and 'chinese' text entries.
             包含'english'和'chinese'文本条目的字典.
        """
        en_text = (
            f"## {ranked.project.full_name} (Tier {ranked.tier.value}, "
            f"Score: {ranked.score.comprehensive:.1f}/100)\n\n"
        )
        zh_text = (
            f"## {ranked.project.full_name} "
            f"(等级{ranked.tier.value},得分:{ranked.score.comprehensive:.1f}/100)\n\n"
        )

        if ranked.highlights:
            en_text += "**Strengths:**\n"
            zh_text += "**优势:**\n"
            for h in ranked.highlights:
                en_text += f"- {h}\n"
                zh_text += f"- {h}\n"

        if ranked.concerns:
            en_text += "\n**Considerations:**\n"
            zh_text += "\n**注意事项:**\n"
            for c in ranked.concerns:
                en_text += f"- {c}\n"
                zh_text += f"- {c}\n"

        if ranked.recommendation_reason:
            en_text += f"\n> **Verdict:** {ranked.recommendation_reason}\n"
            zh_text += f"\n> **结论:** {ranked.recommendation_reason}\n"

        return {"english": en_text, "chinese": zh_text}

    # ------------------------------------------------------------------
    # Template-based Explanations (no AI needed) / 基于模板的解释(无需AI)
    # ------------------------------------------------------------------

    def _build_overview_en(
        self, ranked: List[RankedProject]
    ) -> str:
        """Build English overview section.

        构建英文概览部分."""
        lines: List[str] = []

        top = ranked[0]
        lines.append(
            f"We analyzed **{len(ranked)}** GitHub projects related to your query."
        )
        lines.append(
            f"The top recommendation is **{top.project.full_name}** "
            f"(Score: **{top.score.comprehensive:.1f}**, Tier **{top.tier.value}**) "
            f"with **{top.project.stars:,}** stars.\n"
        )

        if len(ranked) > 1:
            second = ranked[1]
            lines.append(
                f"A strong alternative is **{second.project.full_name}** "
                f"(Score: {second.score.comprehensive:.1f})."
            )

        tiers = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        for r in ranked:
            tiers[r.tier.value] = tiers.get(r.tier.value, 0) + 1
        tier_summary = ", ".join(f"{k}: {v}" for k, v in tiers.items() if v > 0)
        lines.append(f"\n**Tier distribution:** {tier_summary}")

        return "\n".join(lines)

    def _build_overview_zh(
        self, ranked: List[RankedProject]
    ) -> str:
        """Build Chinese overview section.

        构建中文概览部分."""
        lines: List[str] = []

        top = ranked[0]
        lines.append(
            f"我们分析了与您的查询相关的 **{len(ranked)}** 个GitHub项目."
        )
        lines.append(
            f"首选推荐是 **{top.project.full_name}** "
            f"(得分:**{top.score.comprehensive:.1f}**,等级:**{top.tier.value}**),"
            f"拥有 **{top.project.stars:,}** 个Star.\n"
        )

        if len(ranked) > 1:
            second = ranked[1]
            lines.append(
                f"一个强有力的备选方案是 **{second.project.full_name}** "
                f"(得分:{second.score.comprehensive:.1f})."
            )

        return "\n".join(lines)

    def _build_project_details(
        self, ranked: List[RankedProject]
    ) -> List[Dict[str, Any]]:
        """Build per-project detail entries.

        构建每个项目的详细条目."""
        details: List[Dict[str, Any]] = []

        for rp in ranked:
            entry: Dict[str, Any] = {
                "rank": rp.rank,
                "full_name": rp.project.full_name,
                "description": rp.project.description or "No description available",
                "stars": rp.project.stars,
                "language": rp.project.primary_language or "Unknown",
                "score": round(rp.score.comprehensive, 1),
                "tier": rp.tier.value,
                "highlights_en": rp.highlights,
                "concerns_en": rp.concerns,
                "use_cases": rp.use_cases,
                "url": rp.project.html_url or rp.project.url,
            }
            details.append(entry)

        return details

    def _build_comparison_table(
        self, ranked: List[RankedProject]
    ) -> ComparisonTable:
        """Build a cross-project metrics comparison table.

        构建跨项目指标比较表格."""
        headers = ["Rank", "Project", "Stars", "Score", "Tier", "Language"]

        rows: List[Dict[str, Any]] = []
        for rp in ranked[:15]:  # Limit table size / 限制表格大小
            rows.append({
                "Rank": rp.rank,
                "Project": rp.project.full_name,
                "Stars": rp.project.stars,
                "Score": f"{rp.score.comprehensive:.1f}",
                "Tier": rp.tier.value,
                "Language": rp.project.primary_language or "-",
            })

        return ComparisonTable(
            headers=headers,
            rows=rows,
            project_names=[rp.project.full_name for rp in ranked[:15]],
        )

    def _template_conclusion_en(
        self, ranked: List[RankedProject]
    ) -> str:
        """Template-based English conclusion fallback.

        基于模板的英文结论后备."""
        if not ranked:
            return "No sufficient data for a conclusion."

        top = ranked[0]

        conclusion_parts: List[str] = [
            f"### Recommendation Summary\n",
            f"Based on our multi-dimensional analysis of {len(ranked)} projects, ",
            f"we recommend **{top.project.full_name}** as the best fit.\n",
            f"\n#### Why this choice?\n",
        ]

        if top.highlights:
            for h in top.highlights[:3]:
                conclusion_parts.append(f"- {h}")

        if top.concerns:
            conclusion_parts.append("\n#### Keep in mind:\n")
            for c in top.concerns[:2]:
                conclusion_parts.append(f"- {c}")

        if len(ranked) > 1:
            alt = ranked[1]
            conclusion_parts.append(
                f"\nIf you need an alternative, consider **{alt.project.full_name}** "
                f"(Score: {alt.score.comprehensive:.1f})."
            )

        return "".join(conclusion_parts)

    def _template_conclusion_zh(
        self, ranked: List[RankedProject]
    ) -> str:
        """Template-based Chinese conclusion fallback.

        基于模板的中文结论后备."""
        if not ranked:
            return "没有足够的数据来得出结论."

        top = ranked[0]

        parts: List[str] = [
            f"### 推荐总结\n",
            f"基于对{len(ranked)}个项目的多维度分析,",
            f"我们推荐 **{top.project.full_name}** 作为最佳选择.\n",
            f"\n#### 为什么选择它?\n",
        ]

        if top.highlights:
            for h in top.highlights[:3]:
                parts.append(f"- {h}")

        if top.concerns:
            parts.append("\n#### 注意事项:\n")
            for c in top.concerns[:2]:
                parts.append(f"- {c}")

        if len(ranked) > 1:
            alt = ranked[1]
            parts.append(
                f"\n如需备选方案,可考虑 **{alt.project.full_name}** "
                f"(得分:{alt.score.comprehensive:.1f})."
            )

        return "".join(parts)

    # ------------------------------------------------------------------
    # AI-Enhanced Explanations / AI增强的解释
    # ------------------------------------------------------------------

    async def _generate_ai_conclusion(
        self,
        ranked: List[RankedProject],
        query: str,
    ) -> Dict[str, str]:
        """Use LLM to generate richer bilingual conclusions.

        使用LLM生成更丰富的双语结论.

        Args:
            ranked: Ranked projects.
                 已排名项目.
            query: User's original query.
                  用户原始查询.

        Returns:
            Dictionary with 'conclusion_en' and 'conclusion_zh'.
             包含'conclusion_en'和'conclusion_zh'的字典.
        """
        try:
            from src.ai.prompts import EXPLANATION_PROMPT

            ctx_data = json.dumps(
                [
                    {
                        "name": rp.project.full_name,
                        "score": rp.score.comprehensive,
                        "tier": rp.tier.value,
                        "stars": rp.project.stars,
                        "strengths": rp.highlights,
                        "weaknesses": rp.concerns,
                    }
                    for rp in ranked[:8]
                ],
                ensure_ascii=False,
            )

            prompt = EXPLANATION_PROMPT.format(
                system_instruction="",
                user_query=query,
                comparison_context=ctx_data,
                query_summary=query,
            )

            raw = await self.llm_client.generate(prompt)
            return self._split_bilingual_output(raw)

        except Exception as e:
            logger.warning(
                "module=ai", operation="ai_conclusion_failed",
                params={"error": str(e)},
            )
            return {
                "conclusion_en": self._template_conclusion_en(ranked),
                "conclusion_zh": self._template_conclusion_zh(ranked),
            }

    @staticmethod
    def _split_bilingual_output(text: str) -> Dict[str, str]:
        """Attempt to split mixed bilingual output into separate EN/ZH sections.

        尝试将混合的双语输出拆分为单独的英文/中文部分.

        Args:
            text: Raw output possibly containing both languages.
                  可能包含两种语言的原始输出.

        Returns:
            Dictionary with 'conclusion_en' and 'conclusion_zh'.
             包含'conclusion_en'和'conclusion_zh'的字典.
        """
        # Simple heuristic: split on Chinese section markers / 简单启发式:按中文部分标记分割
        en_parts: List[str] = []
        zh_parts: List[str] = []
        current_section: str = "en"

        for line in text.split("\n"):
            stripped = line.strip()
            if any(marker in stripped for marker in ("## ", "### ")) and any(
                c in stripped for c in ("中文", "总结", "说明", "对比", "建议")
            ):
                current_section = "zh"
            if current_section == "en":
                en_parts.append(line)
            else:
                zh_parts.append(line)

        return {
            "conclusion_en": "\n".join(en_parts).strip() or text,
            "conclusion_zh": "\n".join(zh_parts).strip() or "",
        }


__all__ = ["Explainer"]
