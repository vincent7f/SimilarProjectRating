"""
Prompt-Based Code Analyzer / 基于Prompt的代码分析器

Analyzes code quality based on GitReverse.com textual project prompts instead of
downloading and examining actual code. This analyzer uses AI to assess code quality
dimensions from the textual description of the project.

基于GitReverse.com文本化项目prompt而非下载和检查实际代码来分析代码质量.
该分析器使用AI从项目的文本描述中评估代码质量维度.

Primary benefit: No need to download and parse repositories, faster analysis.
主要优势:无需下载和解析仓库,分析速度更快.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from src.ai.provider import AIProvider, AIProviderFactory
from src.models.metrics import CodeQualityMetrics
from src.models.repository import Repository
from src.search.gitreverse_client import GitReverseClient
from src.utils.config import AIConfig, GitReverseConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PromptAnalyzer:
    """AI-powered code quality analyzer using GitReverse.com project prompts.

    Instead of downloading and parsing code, this analyzer fetches the textual
    project description from GitReverse.com and uses AI models to assess code
    quality across multiple dimensions based on the description.

    使用GitReverse.com项目prompt的AI驱动代码质量分析器.
    该分析器不是下载和解析代码,而是从GitReverse.com获取文本化项目描述,
    并使用AI模型基于描述评估多个维度的代码质量.

    Attributes:
        gitreverse_client: GitReverse.com API client.
                          GitReverse.com API客户端.
        ai_provider: AI provider for analyzing prompts.
                    用于分析prompt的AI提供商.
        config: GitReverse configuration.
                GitReverse配置.
        ai_config: AI configuration.
                   AI配置.
    """

    def __init__(
        self,
        gitreverse_client: Optional[GitReverseClient] = None,
        ai_provider: Optional[AIProvider] = None,
        config: Optional[GitReverseConfig] = None,
        ai_config: Optional[AIConfig] = None,
    ) -> None:
        self.gitreverse_client = gitreverse_client or GitReverseClient(config)
        self.config = config or GitReverseConfig()
        self.ai_config = ai_config or AIConfig()
        self.ai_provider = ai_provider or AIProviderFactory.create_provider(self.ai_config)

    async def analyze(self, repository: Repository) -> CodeQualityMetrics:
        """Analyze code quality using GitReverse.com project prompt.

        使用GitReverse.com项目prompt分析代码质量.

        Args:
            repository: Repository metadata to analyze.
                       要分析的仓库元数据.

        Returns:
            Complete CodeQualityMetrics assessment.
            完整的CodeQualityMetrics评估.
        """
        start_time = time.time()

        logger.info(
            "module=analysis", operation="prompt_analysis_start",
            params={"repo": repository.full_name},
        )

        try:
            # Step 1: Fetch project prompt from GitReverse.com / 步骤1:从GitReverse.com获取项目prompt
            prompt_text = await self.gitreverse_client.get_project_prompt(repository)
            
            if not prompt_text:
                if self.config.fallback_to_code:
                    logger.info(
                        "module=analysis", operation="prompt_fallback_to_code",
                        params={"repo": repository.full_name},
                    )
                    return await self._fallback_to_code_analysis(repository)
                else:
                    return CodeQualityMetrics(
                        overall_score=0.0,
                        errors=["GitReverse prompt not available and fallback disabled"],
                        analysis_duration_ms=int((time.time() - start_time) * 1000),
                    )

            logger.debug(
                "module=analysis", operation="prompt_received",
                params={
                    "repo": repository.full_name,
                    "prompt_length": len(prompt_text),
                },
            )

            # Step 2: Use AI to analyze prompt and extract metrics / 步骤2:使用AI分析prompt并提取指标
            metrics = await self._analyze_prompt_with_ai(prompt_text, repository)
            metrics.analysis_duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "module=analysis", operation="prompt_analysis_complete",
                params={
                    "repo": repository.full_name,
                    "overall_score": metrics.overall_score,
                    "duration_ms": metrics.analysis_duration_ms,
                },
            )
            return metrics

        except Exception as e:
            logger.error(
                "module=analysis", operation="prompt_analysis_error",
                params={"repo": repository.full_name, "error": str(e)},
            )
            if self.config.fallback_to_code:
                logger.info(
                    "module=analysis", operation="prompt_fallback_due_to_error",
                    params={"repo": repository.full_name, "error": str(e)},
                )
                return await self._fallback_to_code_analysis(repository)
            else:
                return CodeQualityMetrics(
                    overall_score=0.0,
                    errors=[str(e)],
                    analysis_duration_ms=int((time.time() - start_time) * 1000),
                )

    async def _analyze_prompt_with_ai(
        self, 
        prompt_text: str, 
        repository: Repository
    ) -> CodeQualityMetrics:
        """Analyze GitReverse prompt using AI to extract quality metrics.

        使用AI分析GitReverse prompt以提取质量指标.

        Args:
            prompt_text: Project prompt from GitReverse.com.
                        来自GitReverse.com的项目prompt.
            repository: Repository metadata.
                        仓库元数据.

        Returns:
            CodeQualityMetrics object with assessed scores.
            包含评估分数的CodeQualityMetrics对象.
        """
        # Prepare analysis prompt for AI
        ai_prompt = self._create_analysis_prompt(prompt_text, repository)
        
        try:
            # Get AI analysis / 获取AI分析
            response = await self.ai_provider.generate_text(
                prompt=ai_prompt,
                max_tokens=2048,
                temperature=0.3,  # Lower temperature for more consistent analysis / 更低温度以获得更一致的分析
            )
            
            # Parse AI response / 解析AI响应
            metrics = self._parse_ai_response(response, repository)
            return metrics
            
        except Exception as e:
            logger.error(
                "module=analysis", operation="ai_analysis_failed",
                params={"repo": repository.full_name, "error": str(e)},
            )
            # Return default metrics on failure / 失败时返回默认指标
            return CodeQualityMetrics(
                overall_score=50.0,  # Moderate default score / 中等默认分数
                errors=[f"AI analysis failed: {str(e)}"],
            )

    def _create_analysis_prompt(self, prompt_text: str, repository: Repository) -> str:
        """Create prompt for AI analysis of project description.

        为AI分析项目描述创建prompt.

        Args:
            prompt_text: Project description from GitReverse.
                        来自GitReverse的项目描述.
            repository: Repository metadata.
                        仓库元数据.

        Returns:
            Formatted prompt for AI.
            AI的格式化prompt.
        """
        # Truncate prompt text if too long / 如果prompt文本过长则截断
        truncated_prompt = prompt_text
        if len(prompt_text) > 6000:
            truncated_prompt = prompt_text[:6000] + "... [truncated]"
        
        system_prompt = """You are a code quality assessment expert. Analyze the provided project description 
and assign scores for code quality metrics on a scale of 0-100. Provide your assessment 
as a JSON object with specific numerical scores and brief justifications.

你是一个代码质量评估专家.分析提供的项目描述,并为代码质量指标分配0-100的分数.
请将你的评估以JSON对象形式提供,包含具体的分数和简要的理由.

Metrics to assess:
评估的指标:

1. code_style_score: Quality of coding style and conventions (formatting, linting tools, type hints, etc.)
   代码风格分:代码风格和约定的质量(格式化,linting工具,类型提示等)

2. test_coverage: Estimated test coverage and testing practices
   测试覆盖率:估计的测试覆盖率和测试实践

3. has_tests: Boolean indicating if tests are mentioned or implied
   是否有测试:布尔值,表示是否提到或暗示了测试

4. dependency_count: Approximate number of dependencies mentioned
   依赖数量:提到的依赖的近似数量

5. security_issues: List of potential security concerns mentioned
   安全问题:提到的潜在安全问题列表

6. doc_completeness: Documentation quality and completeness
   文档完整性:文档质量和完整性

7. has_readme: Boolean indicating if README/documentation is mentioned
   是否有README:布尔值,表示是否提到README/文档

8. has_api_docs: Boolean for API/documentation mentions
   是否有API文档:布尔值,表示是否提到API/文档

9. has_examples: Boolean for examples/demos mentioned
   是否有示例:布尔值,表示是否提到示例/演示

10. architecture_score: Architectural quality and modularity mentioned
    架构分数:提到的架构质量和模块化

11. overall_score: Overall code quality score (weighted average or overall impression)
    整体分数:整体代码质量分数(加权平均或整体印象)

Return JSON format:
返回的JSON格式:
{
  "code_style_score": float (0-100),
  "test_coverage": float (0-100),
  "has_tests": bool,
  "dependency_count": int,
  "security_issues": [str, ...],
  "doc_completeness": float (0-100),
  "has_readme": bool,
  "has_api_docs": bool,
  "has_examples": bool,
  "architecture_score": float (0-100),
  "overall_score": float (0-100),
  "justification": "Brief explanation of your assessment..."
}
"""
        
        user_prompt = f"""Analyze the following GitHub project description from GitReverse.com:

Project: {repository.full_name}
Description: {truncated_prompt}

Please provide a comprehensive code quality assessment based solely on this description.
If information is not mentioned in the description, make a reasonable assumption based on typical open-source project patterns.

分析以下来自GitReverse.com的GitHub项目描述:

项目: {repository.full_name}
描述: {truncated_prompt}

请仅基于此描述提供全面的代码质量评估.
如果描述中未提及某些信息,请根据典型的开源项目模式进行合理的假设.
"""
        
        return f"{system_prompt}\n\n{user_prompt}"

    def _parse_ai_response(self, ai_response: str, repository: Repository) -> CodeQualityMetrics:
        """Parse AI JSON response into CodeQualityMetrics.

        将AI JSON响应解析为CodeQualityMetrics.

        Args:
            ai_response: AI-generated analysis response.
                         AI生成的分析响应.
            repository: Repository metadata.
                        仓库元数据.

        Returns:
            Populated CodeQualityMetrics object.
            填充的CodeQualityMetrics对象.
        """
        try:
            # Extract JSON from response (handles cases where AI adds extra text)
            # 从响应中提取JSON(处理AI添加额外文本的情况)
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                data = json.loads(json_str)
                
                # Create CodeQualityMetrics from parsed data
                # 从解析的数据创建CodeQualityMetrics
                return CodeQualityMetrics(
                    code_style_score=data.get("code_style_score", 50.0),
                    test_coverage=data.get("test_coverage", 0.0),
                    has_tests=data.get("has_tests", False),
                    dependency_count=data.get("dependency_count", 0),
                    outdated_dependencies=0,  # Cannot determine from prompt / 无法从prompt确定
                    security_issues=data.get("security_issues", []),
                    doc_completeness=data.get("doc_completeness", 50.0),
                    has_readme=data.get("has_readme", False),
                    has_api_docs=data.get("has_api_docs", False),
                    has_examples=data.get("has_examples", False),
                    architecture_score=data.get("architecture_score", 50.0),
                    overall_score=data.get("overall_score", 50.0),
                    test_framework=None,  # Cannot determine from prompt / 无法从prompt确定
                    analysis_duration_ms=0,  # Will be set by caller / 将由调用者设置
                )
            else:
                raise ValueError("JSON not found in AI response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "module=analysis", operation="ai_response_parse_error",
                params={"repo": repository.full_name, "error": str(e), "response": ai_response[:200]},
            )
            # Fallback to heuristic scoring based on repository metadata
            # 基于仓库元数据回退到启发式评分
            return self._heuristic_score_from_metadata(repository)

    def _heuristic_score_from_metadata(self, repository: Repository) -> CodeQualityMetrics:
        """Generate heuristic code quality scores from repository metadata.

        从仓库元数据生成启发式代码质量分数.

        Args:
            repository: Repository metadata.
                        仓库元数据.

        Returns:
            Heuristic CodeQualityMetrics.
            启发式CodeQualityMetrics.
        """
        # Simple heuristic scoring based on repository stars and other metadata
        # 基于仓库stars和其他元数据的简单启发式评分
        base_score = 50.0
        adjustments = []
        
        # Adjust based on stars / 根据stars调整
        if repository.stars > 1000:
            base_score += 15.0
            adjustments.append("High star count")
        elif repository.stars > 100:
            base_score += 5.0
            adjustments.append("Moderate star count")
        
        # Adjust based on recent activity / 根据最近活动调整
        if repository.days_since_last_push <= 30:
            base_score += 10.0
            adjustments.append("Recently active")
        elif repository.days_since_last_push > 365:
            base_score -= 10.0
            adjustments.append("Inactive for over a year")
        
        # Adjust based on has topics / 根据是否有主题调整
        if repository.topics and len(repository.topics) >= 3:
            base_score += 5.0
            adjustments.append("Well-tagged with topics")
        
        # Adjust based on has description / 根据是否有描述调整
        if repository.description and len(repository.description) > 30:
            base_score += 5.0
            adjustments.append("Has descriptive details")
        
        # Ensure score stays within bounds / 确保分数在范围内
        final_score = max(0.0, min(100.0, base_score))
        
        return CodeQualityMetrics(
            code_style_score=max(0.0, min(100.0, final_score - 5.0)),
            test_coverage=max(0.0, min(100.0, final_score - 10.0)),
            has_tests=repository.stars > 100,  # Assume popular repos have tests / 假设流行的仓库有测试
            dependency_count=5,  # Reasonable default / 合理的默认值
            outdated_dependencies=0,
            security_issues=[],
            doc_completeness=max(0.0, min(100.0, final_score + 5.0)),
            has_readme=True,  # Assume most repos have README / 假设大多数仓库有README
            has_api_docs=repository.stars > 500,  # Assume popular repos have API docs / 假设流行的仓库有API文档
            has_examples=repository.stars > 100,  # Assume popular repos have examples / 假设流行的仓库有示例
            architecture_score=max(0.0, min(100.0, final_score)),
            overall_score=final_score,
            test_framework=None,
            analysis_duration_ms=0,
            errors=[f"Heuristic fallback: {', '.join(adjustments)}"] if adjustments else [],
        )

    async def _fallback_to_code_analysis(self, repository: Repository) -> CodeQualityMetrics:
        """Fall back to traditional code analysis when GitReverse is not available.

        当GitReverse不可用时回退到传统代码分析.

        Args:
            repository: Repository metadata.
                        仓库元数据.

        Returns:
            CodeQualityMetrics from traditional analysis.
            来自传统分析的CodeQualityMetrics.
        """
        logger.info(
            "module=analysis", operation="prompt_analysis_fallback",
            params={"repo": repository.full_name},
        )
        
        try:
            # Import here to avoid circular imports / 在此处导入以避免循环导入
            from src.analysis.code_analyzer import CodeAnalyzer
            
            # Use traditional code analyzer / 使用传统代码分析器
            code_analyzer = CodeAnalyzer()
            return await code_analyzer.analyze(repository)
            
        except ImportError as e:
            logger.error(
                "module=analysis", operation="traditional_code_analysis_failed",
                params={"repo": repository.full_name, "error": str(e)},
            )
            # Return basic scores if traditional analysis also fails / 如果传统分析也失败,返回基本分数
            return CodeQualityMetrics(
                overall_score=30.0,
                errors=[f"Fallback analysis failed: {str(e)}"],
            )

    async def close(self) -> None:
        """Close underlying clients.

        关闭底层客户端."""
        await self.gitreverse_client.close()
        if self.ai_provider:
            await self.ai_provider.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


__all__ = ["PromptAnalyzer"]