"""
Prompt Template Definitions.

Centralized collection of all prompt templates used by the AI layer.
Each template defines the system instructions, user input format, and
expected output schema for specific tasks like keyword generation,
relevance judgment, recommendation, and explanation generation.

提示模板集中定义。
AI层使用的所有提示模板的集中集合。
每个模板为特定任务定义系统指令、用户输入格式和预期输出架构，
如关键词生成、相关性判断、推荐和解释生成。
"""

from typing import Dict, List, Optional

# ===========================================================================
# Prompt Constants / 提示常量
# ===========================================================================

SYSTEM_PROMPT_BASE = """\
You are an expert GitHub project analyst and software engineer assistant. \
Your role is to help users find, compare, and evaluate open-source projects on \
GitHub based on their requirements.

You always respond in valid JSON format when structured output is requested.
You are precise, factual, and base your analysis on observable data.
When uncertain, you express confidence levels explicitly.

你是GitHub项目分析师和软件工程师助手专家。你的角色是帮助用户根据需求查找、比较和评估GitHub上的开源项目。
当需要结构化输出时，你始终以有效的JSON格式回应。你精确、基于事实，基于可观察数据进行分析。不确定时，明确表达置信度。
"""


KEYWORD_GENERATION_PROMPT = """\
{system_instruction}

## Task: Generate GitHub Search Keywords

Given the user's query below, generate {num_groups} groups of optimized \
GitHub search keyword sets. Each group should target different aspects:
function names, tech stacks, use cases, and implementation approaches.

### User Query
```
{user_query}
```

### Output Format
Respond with a JSON array where each element has:
- `primary`: Main search keyword (required)
- `extensions`: Array of 2-4 related/supplementary keywords
- `language`: Programming language filter (optional, omit if generic)
- `category`: One of 'functionality', 'tech_stack', 'use_case', 'implementation'
- `rationale`: Brief explanation why these keywords match the user's need

Example output format:
```json
[
  {{
    "primary": "project management tool",
    "extensions": ["kanban", "task tracker", "todo", "gantt"],
    "language": null,
    "category": "functionality",
    "rationale": "Targets core project management functionality"
  }}
]
```"""


RELEVANCE_JUDGMENT_PROMPT = """\
{system_instruction}

## Task: Judge Project Relevance

Evaluate whether a GitHub project is relevant to the user's search intent.

### User Query
```
{user_query}
```

### Project Information
- **Name**: {project_name}
- **Description**: {project_description}
- **Language**: {project_language}
- **Topics**: {project_topics}
- **Stars**: {stars}
- **URL**: {url}

### Output Format
Respond with a JSON object:
```json
{{
  "is_relevant": true/false,
  "relevance_score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of your judgment",
  "suggested_use_case": "What this project might be good for (if relevant)"
}}
```"""


RECOMMENDATION_PROMPT = """\
{system_instruction}

## Task: Generate Project Recommendations

Given analysis results of multiple similar GitHub projects, provide \
ranked recommendations tailored to the user's needs.

### User Query
```
{user_query}
```

### Analyzed Projects Data
{projects_data}

### Scoring Summary Table
{scoring_table}

### Output Format
Respond with a JSON array where each element represents one recommended \
project:
```json
[
  {{
    "project_name": "owner/repo",
    "recommended_tier": "S|A|B|C|D",
    "primary_strengths": ["strength1", "strength2"],
    "potential_concerns": ["concern1"],
    "best_for": ["specific use cases this excels at"],
    "not_recommend_for": ["cases where alternatives may be better"],
    "verdict": "2-3 sentence summary verdict"
  }}
]
```"""


EXPLANATION_PROMPT = """\
{system_instruction}

## Task: Generate Detailed Comparison Explanation

Create a comprehensive bilingual (Chinese + English) comparison explanation \
for the analyzed projects.

### User Query
```
{user_query}
```

### Project Comparison Context
{comparison_context}

### Output Format (Markdown)
```markdown
# Project Comparison Report: {query_summary}

## Overall Recommendation
[English paragraph recommending the top choice(s)]

## 整体推荐
[对应的中文段落]

## Project Details

### 1. {project_1_name} ({score}/100)
**Strengths**:
- [English point 1]
- [English point 2]

**优势**:
- [中文对应点1]
- [中文对应点2]

**Concerns**:
- [English concern if any]

**注意事项**:
- [中文对应注意事项]

---

(Repeat for each project)

## Side-by-Side Comparison Table
[Markdown table comparing key metrics]
```"""


FUNCTIONALITY_ASSESSMENT_PROMPT = """\
{system_instruction}

## Task: Assess Project Functionality Completeness

Evaluate how complete and capable a project's feature set is based on \
available information (README, topics, structure).

### Project Info
- **Name**: {project_name}
- **Description**: {description}
- **Topics**: {topics}
- **README excerpt**: {readme_excerpt}

### Output Format
```json
{{
  "core_features_detected": ["feature1", "feature2"],
  "missing_common_features": ["feature that seems absent"],
  "extensibility_score": 0.0-1.0,
  "documentation_quality": 0.0-1.0,
  "examples_available": true/false,
  "api_coverage_assessment": "brief note on API surface",
  "overall_functionality_score": 0.0-100.0,
  "assessment_notes": "Key observations about capability scope"
}}
```"""


SESSION_SUMMARY_PROMPT = """\
{system_instruction}

## Task: Analyze Session Execution Results

Review the execution log and produce a structured summary of what went well, \
what failed, and actionable recommendations for improvement.

### Session Overview
- **Query**: {query}
- **Total candidates found**: {total_found}
- **Projects analyzed**: {analyzed_count}
- **Success rate**: {success_rate}
- **Total duration**: {duration}s
- **Errors encountered**: {errors}

### Key Events Log
{event_log}

### Output Format
```json
{{
  "executive_summary": "2-sentence overall outcome",
  "successful_aspects": ["what worked well"],
  "failed_aspects": [
    {{"issue": "what went wrong", "cause": "why", "fix": "how to resolve"}}
  ],
  "optimization_suggestions": ["actionable improvements for next run"],
  "next_run_recommendations": ["specific tips for better results next time"],
  "lessons_learned": ["general insights worth recording"]
}}
```"""


def build_keyword_prompt(
    user_query: str,
    num_groups: int = 5,
    system_instruction: str = SYSTEM_PROMPT_BASE,
) -> str:
    """Build the full keyword generation prompt.

    构建完整的关键词生成提示。

    Args:
        user_query: User's natural language search query.
                   用户自然语言搜索查询。
        num_groups: Number of keyword groups to generate.
                   要生成关键词组的数量。
        system_instruction: System-level instruction override.
                           系统级指令覆盖。

    Returns:
        Fully formatted prompt string ready for LLM.
         准备好发送给LLM的完整格式化提示字符串。
    """
    return KEYWORD_GENERATION_PROMPT.format(
        system_instruction=system_instruction,
        user_query=user_query,
        num_groups=num_groups,
    )


def build_relevance_prompt(
    user_query: str,
    project_name: str,
    project_description: str,
    project_language: Optional[str],
    project_topics: List[str],
    stars: int,
    url: str,
    system_instruction: str = SYSTEM_PROMPT_BASE,
) -> str:
    """Build the relevance judgment prompt.

    构建相关性判断提示。
    """
    return RELEVANCE_JUDGMENT_PROMPT.format(
        system_instruction=system_instruction,
        user_query=user_query,
        project_name=project_name,
        project_description=project_description or "No description available",
        project_language=project_language or "Unknown",
        project_topics=", ".join(project_topics) if project_topics else "None",
        stars=stars,
        url=url,
    )


def build_recommendation_prompt(
    user_query: str,
    projects_data: str,
    scoring_table: str,
    system_instruction: str = SYSTEM_PROMPT_BASE,
) -> str:
    """Build the recommendation generation prompt.

    构建推荐生成提示。
    """
    return RECOMMENDATION_PROMPT.format(
        system_instruction=system_instruction,
        user_query=user_query,
        projects_data=projects_data,
        scoring_table=scoring_table,
    )


__all__ = [
    "SYSTEM_PROMPT_BASE",
    "KEYWORD_GENERATION_PROMPT",
    "RELEVANCE_JUDGMENT_PROMPT",
    "RECOMMENDATION_PROMPT",
    "EXPLANATION_PROMPT",
    "FUNCTIONALITY_ASSESSMENT_PROMPT",
    "SESSION_SUMMARY_PROMPT",
    "build_keyword_prompt",
    "build_relevance_prompt",
    "build_recommendation_prompt",
]
