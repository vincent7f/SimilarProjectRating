# Similar Project Rating System - 实施计划

## Project Implementation Plan: GitHub开源项目智能分析与比较系统

### 0. 工程约束 (Engineering Constraints)

> **核心规则：每次修改/提交最多涉及5个文件**
> 
> This is a mandatory engineering rule to ensure:
> - 每次变更范围可控、可审查
> - 减少合并冲突风险
> - 便于code review和问题定位
> - 支持git worktree并行开发
>
> **执行策略**：
> - 如果一个功能需要修改>5个文件 → 必须拆分为多个子任务
> - 每个"步骤"(Step) = 一次原子性修改，涉及≤5个文件
> - 下面的实施计划已按此原则预拆分为原子化步骤

### 1. 项目初始化与基础架构搭建

#### 1.1 创建项目目录结构
```
similar_project_rating/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI入口
│   ├── search/                    # 搜索模块
│   │   ├── __init__.py
│   │   ├── keyword_generator.py   # AI关键词生成
│   │   ├── github_client.py       # GitHub API客户端
│   │   └── project_filter.py      # 项目相关性过滤
│   ├── analysis/                  # 分析模块
│   │   ├── __init__.py
│   │   ├── code_analyzer.py       # 代码质量分析
│   │   ├── community_analyzer.py  # 社区活跃度分析
│   │   └── maturity_analyzer.py   # 项目成熟度分析
│   ├── scoring/                   # 评分模块
│   │   ├── __init__.py
│   │   ├── score_calculator.py    # 多维评分计算
│   │   └── ranking_engine.py      # 排名引擎
│   ├── ai/                        # AI集成模块
│   │   ├── __init__.py
│   │   ├── llm_client.py          # LLM统一接口(Ollama/OpenAI/LiteLLM)
│   │   ├── recommender.py         # 推荐生成
│   │   └── explainer.py           # 解释生成
│   ├── utils/                     # 工具模块
│   │   ├── __init__.py
│   │   ├── logger.py              # 日志系统
│   │   ├── config.py              # 配置管理
│   │   └── cache.py               # 缓存系统
│   └── storage/                   # 存储模块
│       ├── __init__.py
│       ├── database.py            # SQLite数据库操作
│       └── file_manager.py        # 文件管理
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures
│   ├── unit/                      # 单元测试
│   │   ├── test_keyword_generator.py
│   │   ├── test_github_client.py
│   │   ├── test_project_filter.py
│   │   ├── test_code_analyzer.py
│   │   ├── test_score_calculator.py
│   │   └── test_llm_client.py
│   └── integration/               # 集成测试
│       ├── test_analysis_pipeline.py
│       └── test_full_workflow.py
├── configs/
│   ├── config.yaml                # 主配置文件
│   └── scoring_weights.yaml       # 评分权重配置
├── logs/                          # 日志目录
├── data/
│   ├── cache/                     # 缓存数据
│   └── results/                   # 分析结果
├── scripts/                       # 辅助脚本
│   └── setup_env.sh
├── requirements/                  # 依赖管理
│   ├── base.txt                   # 基础依赖
│   ├── dev.txt                    # 开发依赖
│   └── ai.txt                     # AI相关依赖
├── .github/
│   └── workflows/
│       ├── ci.yml                 # CI流水线
│       └── analysis.yml           # 定期分析任务
├── pyproject.toml                 # 项目配置
├── README.md                      # 项目说明(中英双语)
└── LICENSE
```

#### 1.2 创建核心配置文件
- `pyproject.toml`: 项目元数据、构建配置、工具配置(black, pylint, pytest等)
- `requirements/base.txt`: 核心依赖(httpx, PyYAML, rich, etc.)
- `requirements/dev.txt`: 开发依赖(pytest, pytest-cov, black, pylint, mypy)
- `requirements/ai.txt`: AI依赖(litellm, openai可选)
- `configs/config.yaml`: 完整的YAML配置(GitHub/AI/Analysis/Scoring/Logging)

### 2. 基础设施层实现 (utils/, storage/)

#### 2.1 配置管理模块 (utils/config.py)
```python
# 功能:
# - 从config.yaml加载配置
# - 支持环境变量覆盖(${VAR}语法)
# - 类型安全的配置访问(Config dataclass)
# - 配置验证和默认值
```

#### 2.2 日志系统 (utils/logger.py)
```python
# 功能:
# - 结构化JSON日志输出
# - 多级别日志(DEBUG/INFO/WARNING/ERROR)
# - 文件+控制台双输出
# - 日志轮转(按大小和时间)
# - 每次运行独立日志文件
# - CodeBuddy对话记录保存
```

**日志格式规范**:
```json
{
  "timestamp": "ISO8601",
  "level": "INFO|DEBUG|WARNING|ERROR",
  "module": "search|analysis|scoring|ai",
  "operation": "具体操作名",
  "params": {},
  "results": {},
  "duration_ms": 1234,
  "success": true|false,
  "error": null|"error message"
}
```

#### 2.3 缓存系统 (utils/cache.py)
```python
# 功能:
# - 基于文件系统的缓存(TTL过期)
# - GitHub API响应缓存(避免重复请求)
# - 分析结果缓存
# - LRU淘汰策略
# - 缓存命中率统计
```

#### 2.4 存储模块 (storage/)
- **database.py**: SQLite操作
  - 项目信息表(projects)
  - 分析结果表(analysis_results)
  - 运行记录表(sessions)
  - 日志索引表(log_index)
  
- **file_manager.py**: 文件管理
  - 代码下载临时目录管理
  - 结果报告文件生成(JSON/Markdown)
  - 数据清理和归档

### 3. AI集成层实现 (ai/)

#### 3.1 LLM统一客户端 (ai/llm_client.py)
```python
# 核心类: LLMClient
# 
# 功能:
# - 统一的LLM调用接口
# - Provider优先级: Ollama > OpenAI > 其他(通过LiteLLM)
# - 自动重试和降级机制
# - Prompt模板管理
# - Token使用统计
# - 流式响应支持(可选)
#
# 接口设计:
class LLMClient:
    def __init__(self, config: Config): ...
    async def generate(self, prompt: str, system_prompt: str = None) -> str: ...
    async def generate_structured(self, prompt: str, schema: dict) -> dict: ...
    def get_provider_status(self) -> ProviderStatus: ...
    
# Provider适配器:
class OllamaProvider(BaseProvider): ...
class OpenAIProvider(BaseProvider): ...
class LiteLLMProvider(BaseProvider): ...
```

**Prompt模板**:
1. 关键词生成Prompt: 输入用户查询，输出3-5组GitHub搜索关键词
2. 相关性判断Prompt: 输入项目描述+用户查询，输出相关性分数0-1+理由
3. 推荐解释Prompt: 输入项目对比数据，输出自然语言推荐理由

#### 3.2 推荐引擎 (ai/recommender.py)
```python
# 功能:
# - 基于评分的排序推荐
# - 用户偏好加权调整
# - 场景化推荐(学习/生产/实验)
# - 推荐多样性保证(避免只推荐同类项目)
```

#### 3.3 解释生成器 (ai/explainer.py)
```python
# 功能:
# - 为每个推荐项目生成原因说明
# - 优缺点分析
# - 使用建议和注意事项
# - 替代方案比较
# - 中英双语输出
```

### 4. 搜索模块实现 (search/)

#### 4.1 关键词生成器 (search/keyword_generator.py)
```python
# 类: KeywordGenerator
# 
# 输入: 用户自然语言查询 (如"项目管理工具")
# 处理: 调用LLM生成多组搜索关键词
# 输出: List[KeywordGroup]
#
# KeywordGroup数据结构:
@dataclass
class KeywordGroup:
    primary: str           # 主关键词
    extensions: List[str]  # 扩展词
    language: str          # 编程语言过滤(可选)
    category: str          # 分类标签
```

**LLM Prompt示例**:
```
You are a GitHub search expert. Given the user's query, generate 3-5 groups of 
optimized GitHub search keywords. Each group should target different aspects:
function names, tech stacks, use cases, implementation approaches.

Query: {user_query}

Output format (JSON array):
[{
  "primary": "main keyword",
  "extensions": ["related term1", "related term2"],
  "language": "optional language filter",
  "rationale": "why this keyword group"
}]
```

#### 4.2 GitHub API客户端 (search/github_client.py)
```python
# 类: GitHubClient
#
# 功能:
# - REST API v3搜索(repositories, code, issues)
# - GraphQL API v4(复杂查询)
# - 认证token管理
# - Rate limit处理(剩余次数检测、等待、排队)
# - 分页处理
# - Release信息获取
# - 代码下载(archive download URL)
#
# 主要方法:
class GitHubClient:
    def search_repositories(self, query: str, per_page=30, max_results=50) -> List[Repository]: ...
    def get_repository(self, owner: str, repo: str) -> Repository: ...
    def get_latest_release(self, owner: str, repo: str) -> Optional[Release]: ...
    def get_repo_archive_url(self, owner: str, repo: str, ref: str = None) -> str: ...
    def get_community_metrics(self, owner: str, repo: str) -> CommunityMetrics: ...
    def check_rate_limit(self) -> RateLimitStatus: ...

# 数据模型:
@dataclass
class Repository:
    id: int
    name: str
    full_name: str           # owner/repo
    description: str
    url: str
    stars: int
    forks: int
    open_issues: int
    language: Optional[str]
    topics: List[str]
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    default_branch: str
    license: Optional[str]
    
@dataclass  
class Release:
    tag_name: str
    name: str
    published_at: datetime
    archive_url: str         # zipball下载链接
    assets: List[Asset]
```

#### 4.3 项目过滤器 (search/project_filter.py)
```python
# 类: ProjectFilter
#
# 功能:
# - AI驱动的相关性判断
# - 批量过滤不相关项目
# - 数量控制(最多保留top 20 by stars)
# - 最小数量保底(至少5个项目)
# - 过滤结果日志
#
# 过滤流程:
# 1. 收集所有搜索结果的并集
# 2. 去重(by full_name)
# 3. 对每个项目调用LLM判断相关性
# 4. 过滤低于阈值的项目(default threshold=0.6)
# 5. 如>20个，按stars取前20
# 6. 如<5个，提示用户调整关键词
```

### 5. 分析模块实现 (analysis/)

#### 5.1 代码分析器 (analysis/code_analyzer.py)
```python
# 类: CodeAnalyzer
#
# 功能:
# - 下载项目代码(优先release archive)
# - 静态代码质量分析
# - 多语言支持(Python优先，其他语言基础分析)
#
# 分析维度:
@dataclass
class CodeQualityMetrics:
    # 代码规范性
    has_style_guide: bool          # 是否有代码风格配置
    follows_conventions: float     # 约定遵循度 0-1
    
    # 测试覆盖
    has_tests: bool                # 是否有测试目录/文件
    test_framework: Optional[str]  # 测试框架类型
    estimated_coverage: float      # 估计覆盖率 0-1
    
    # 依赖管理
    dependency_file: Optional[str] # 依赖文件路径
    dependency_count: int          # 依赖数量
    outdated_deps: int             # 过期依赖数
    security_issues: List[str]     # 安全问题列表
    
    # 文档完整性
    has_readme: bool
    has_api_doc: bool
    has_examples: bool
    has_changelog: bool
    doc_score: float               # 文档完整度 0-1
    
    # 架构质量
    directory_structure_score: float  # 目录结构合理性
    modularity_score: float          # 模块化程度
    complexity_indicators: Dict      # 复杂度指标
    
    # 综合得分
    overall_score: float             # 加权综合分 0-100
    
# 实现策略:
# - 使用radon进行Python复杂度分析(如有)
# - 正则表达式检测常见模式(tests/, docs/, examples/)
# - AST解析提取import语句分析依赖
# - 基于规则的评分(可配置权重)
```

**代码下载策略**:
```
1. 调用GitHub API获取最新release
2. 如有release → 下载release archive (zipball)
3. 如无release → 下载default branch archive
4. 解压到临时目录
5. 分析完成后清理(或缓存)
6. 大小限制: >50MB时仅分析核心目录(src/, lib/, 根目录.py文件)
```

#### 5.2 社区分析器 (analysis/community_analyzer.py)
```python
# 类: CommunityAnalyzer
#
# 功能:
# - 通过GitHub API获取社区活跃度数据
# - 计算各维度得分
#
# 分析维度:
@dataclass
class CommunityMetrics:
    # Star相关
    total_stars: int
    star_growth_30d: float         # 近30天star增长率
    star_growth_90d: float         # 近90天star增长率  
    stars_per_day: float           # 平均每日新增star
    
    # Commit活动
    commit_frequency_weekly: float # 周均提交数
    recent_commits_30d: int        # 近30天提交数
    active_contributors_30d: int   # 近30天活跃贡献者数
    total_contributors: int        # 总贡献者数
    
    # Issue活动
    open_issues: int
    closed_issues_total: int
    issue_resolution_rate: float   # issue关闭率
    avg_resolution_days: float     # 平均解决时间(天)
    issues_created_30d: int        # 近30天新issue数
    
    # PR活动
    open_prs: int
    merged_prs_total: int
    pr_merge_rate: float           # PR合并率
    avg_review_time_hours: float   # 平均review时间
    
    # 时间维度
    days_since_last_commit: int    # 距上次提交天数
    days_since_last_release: int   # 距上次发布天数
    project_age_days: int          # 项目年龄(天)
    
    # 综合得分
    activity_score: float          # 活跃度 0-100
    health_score: float            # 健康度 0-100
    overall_score: float           # 综合分 0-100
    
# API端点使用:
# GET /repos/{owner}/{repo} - 基本信息
# GET /repos/{owner}/{repo}/commits?since={date} - 提交历史
# GET /repos/{owner}/{repo}/issues?state=closed&since={date} - 已关闭issue
# GET /repos/{owner}/{repo}/contributors - 贡献者列表
# GET /repos/{owner}/{repo}/releases - 发布历史
# Stargazers with timestamps (需要GraphQL) - star历史
```

#### 5.3 成熟度分析器 (analysis/maturity_analyzer.py)
```python
# 类: MaturityAnalyzer
#
# 功能:
# - 评估项目的生产就绪程度
# - 版本规范性检查
# - 工具链完善度评估
#
# 分析维度:
@dataclass
class MaturityMetrics:
    # 版本管理
    release_count: int             # 发布总数
    uses_semver: bool              # 是否语义化版本
    latest_version: Optional[str]  # 最新版本号
    days_since_last_release: int
    release_frequency_days: float  # 平均发布间隔
    
    # CI/CD
    has_ci_config: bool            # 是否有CI配置(.github/workflows等)
    ci_platform: Optional[str]     # CI平台
    has_cd_pipeline: bool          # 是否有CD流水线
    has automated_tests: bool      # 是否有自动化测试
    has_code_quality_check: bool   # 是否有代码质量检查
    
    # 项目治理
    has_license: bool
    license_type: Optional[str]
    has_code_of_conduct: bool
    has_contributing_guide: bool
    has_security_policy: bool
    has_issue_template: bool
    has_pr_template: bool
    
    # 社区基础设施
    has_discussion_forum: bool     # Discussions/Discord/Slack等
    has_website: bool
    has_roadmap: bool
    has_changelog: bool
    
    # 综合得分
    maturity_level: str            # experimental/beta/stable/mature
    overall_score: float           # 0-100
    
# 成熟度等级定义:
# experimental (<30): 早期项目，API不稳定
# beta (30-50): Beta阶段，基本功能可用
# stable (50-75): 稳定版，可用于生产
# mature (>75): 成熟项目，完善的生态和支持
```

### 6. 评分模块实现 (scoring/)

#### 6.1 评分计算器 (scoring/score calculator.py)
```python
# 类: ScoreCalculator
#
# 评分体系(6维度):
DIMENSION_WEIGHTS = {
    'code_quality': 0.25,      # 代码质量 25%
    'community': 0.20,         # 社区活跃 20%
    'functionality': 0.18,     # 功能完整性 18%
    'maturity': 0.15,          # 项目成熟度 15%
    'reputation': 0.12,        # 用户评价 12%
    'sustainability': 0.10,    # 维护可持续性 10%
}
#
# 功能:
# - 各维度标准化(min-max normalization)
# - 加权求和计算综合分
# - 可配置权重调整
# - 评分分布可视化数据准备
#
# 标准化公式:
# normalized_score = (raw_score - min_score) / (max_score - min_score + epsilon)
# comprehensive_score = sum(dim_weight * dim_normalized for each dimension)
#
# 方法:
class ScoreCalculator:
    def __init__(self, weights: Dict[str, float] = None): ...
    def calculate_project_score(self, project: AnalyzedProject) -> ProjectScore: ...
    def calculate_batch_scores(self, projects: List[AnalyzedProject]) -> List[ProjectScore]: ...
    def normalize_dimensions(self, scores: List[ProjectScore]) -> List[ProjectScore]: ...
    def get_dimension_breakdown(self, score: ProjectScore) -> Dict[str, float]: ...

@dataclass
class ProjectScore:
    project_full_name: str
    dimensions: Dict[str, float]   # 各维度原始分
    normalized: Dict[str, float]   # 各维度标准化分
    comprehensive: float           # 综合分
    rank: int                      # 排名
    confidence: float              # 评分置信度
```

#### 6.2 排名引擎 (scoring/ranking_engine.py)
```python
# 类: RankingEngine
#
# 功能:
# - 综合排名生成
# - 单维度排行榜
# - 用户偏好定制排名
# - 相似项目聚类分组
#
# 方法:
class RankingEngine:
    def rank_by_comprehensive(self, scores: List[ProjectScore]) -> List[RankedProject]: ...
    def rank_by_dimension(self, scores: List[ProjectScore], dimension: str) -> List[RankedProject]: ...
    def rank_with_preferences(self, scores: List[ProjectScore], user_prefs: UserPreferences) -> List[RankedProject]: ...
    def group_by_category(self, ranked: List[RankedProject]) -> Dict[str, List[RankedProject]]: ...
    
@dataclass  
class RankedProject:
    project: Repository
    score: ProjectScore
    rank: int
    tier: str  # S/A/B/C/D 分档
    highlights: List[str]  # 亮点标签
    concerns: List[str]    # 注意事项

@dataclass
class UserPreferences:
    prioritize_code_quality: float   # 0-1, 默认0.5
    prioritize_community: float
    prioritize_stability: float
    use_case: str  # learning/production/experimentation/contribution
```

### 7. 主程序入口 (main.py)

#### 7.1 CLI接口设计
```bash
# 使用方式
python -m similar_project_rating "项目管理工具"
python -m similar_project_rating "react component library" --max-projects 15
python -m similar_project_rating "database orm" --provider openai --model gpt-4
python -m similar_project_rating --config custom_config.yaml "web scraping"

# 命令行参数:
--query, -q          用户查询关键词(必需)
--config, -c         自定义配置文件路径
--max-projects, -n   最大分析项目数(默认20)
--output, -o         输出目录(默认./data/results/)
--provider, -p       AI provider(ollama/openai/litellm)
--model, -m          AI模型名称
--verbose, -v        详细输出模式
--no-cache           禁用缓存
--dry-run            仅搜索不分析(预览模式)
```

#### 7.2 主流程编排
```python
async def main():
    """主执行流程"""
    # 1. 初始化(加载配置、初始化日志、连接服务)
    init()
    
    # 2. 关键词生成(AI生成搜索词组)
    keywords = await generate_keywords(user_query)
    
    # 3. 项目搜索(GitHub API搜索)
    candidates = await search_projects(keywords)
    
    # 4. 相关性过滤(AI判断+规则过滤)
    filtered = await filter_projects(candidates, user_query)
    
    # 5. 并行分析(代码/社区/成熟度)
    analyzed = await analyze_projects_parallel(filtered)
    
    # 6. 评分计算(多维加权评分)
    scored = calculate_scores(analyzed)
    
    # 7. 排名生成(综合排名+单维度排行)
    ranked = rank_projects(scored)
    
    # 8. 推荐生成(AI推荐+解释)
    recommendations = await generate_recommendations(ranked, user_query)
    
    # 9. 报告输出(Markdown/JSON/终端表格)
    report = generate_report(recommendations)
    
    # 10. 运行总结(成功/失败/建议)
    summary = generate_session_summary()
    
    # 11. 数据持久化(数据库+文件)
    save_results(report, summary)
    
    # 12. Git自动提交(可选)
    if auto_commit:
        git_commit_results()
```

### 8. 测试策略

#### 8.1 单元测试 (tests/unit/)
- `test_keyword_generator.py`: Mock LLM客户端测试关键词生成逻辑
- `test_github_client.py`: Mock HTTP响应测试API解析和错误处理
- `test_project_filter.py`: 测试相关性过滤逻辑和阈值
- `test_code_analyzer.py`: 测试静态分析的规则和评分
- `test_score_calculator.py`: 测试评分算法正确性和边界条件
- `test_llm_client.py`: 测试provider选择和降级逻辑

#### 8.2 集成测试 (tests/integration/)
- `test_analysis_pipeline.py`: 端到端分析流程(使用真实小型仓库)
- `test_full_workflow.py`: 完整工作流测试(从搜索到报告)

#### 8.3 Fixtures (tests/conftest.py)
- mock_github_client: 预设API响应的Mock客户端
- mock_llm_client: 预设LLM回复的Mock客户端
- sample_repository: 测试用的示例仓库数据
- sample_analysis_result: 测试用的示例分析结果

#### 8.4 覆盖率目标
- 总体行覆盖率 >= 80%
- 核心业务逻辑覆盖率 >= 90%

### 9. GitHub Actions CI/CD

#### 9.1 CI流水线 (.github/workflows/ci.yml)
```yaml
name: CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install black pylint mypy
      - run: black --check .
      - run: pylint src/
      - run: mypy src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements/dev.txt
      - run: pytest tests/unit --cov=src --cov-report=xml
      
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install safety bandit
      - run: safety check -r requirements/base.txt
      - run: bandit -r src/
```

### 10. 文档要求

#### 10.1 README.md (中英双语)
- 项目介绍和目标
- 功能特性列表
- 快速开始指南
- 安装和配置说明
- 使用示例
- 开发指南
- 贡献指南
- License声明

---

## Implementation Steps (原子化实施步骤)

> **每个Step ≤ 5个文件，可独立提交和审查**

### Phase 1: 项目骨架 (5 steps, 每步≤5文件)

#### Step 1.1 - 目录结构与包初始化 [5 files]
**涉及文件:**
1. `src/__init__.py`
2. `src/search/__init__.py`
3. `src/analysis/__init__.py`
4. `src/scoring/__init__.py`
5. `src/ai/__init__.py`

**内容:** 空的__init__.py文件，建立包结构

---

#### Step 1.2 - 工具与存储包初始化 + 主入口占位 [5 files]
**涉及文件:**
1. `src/utils/__init__.py`
2. `src/storage/__init__.py`
3. `src/main.py` (CLI骨架，argparse参数定义)
4. `tests/__init__.py`
5. `tests/unit/__init__.py`

**内容:** 剩余包初始化、main.py基础框架

---

#### Step 1.3 - 测试包初始化 + 项目配置文件 [5 files]
**涉及文件:**
1. `tests/integration/__init__.py`
2. `tests/conftest.py` (空fixture模板)
3. `pyproject.toml` (项目元数据、tool配置)
4. `.gitignore` (Python标准gitignore)
5. `.editorconfig` (编码风格统一)

**内容:** 完整目录结构就位

---

#### Step 1.4 - 依赖管理文件 [3 files]
**涉及文件:**
1. `requirements/base.txt` (httpx, pyyaml, rich, etc.)
2. `requirements/dev.txt` (pytest, pytest-cov, black, pylint, mypy)
3. `requirements/ai.txt` (litellm, openai可选依赖)

**内容:** Python依赖清单

---

#### Step 1.5 - 配置系统核心 [5 files]
**涉及文件:**
1. `src/utils/config.py` (Config dataclass, YAML加载, 环境变量解析)
2. `configs/config.yaml` (完整默认配置)
3. `configs/scoring_weights.yaml` (评分权重独立配置)
4. `src/models/__init__.py` (新建models子包)
5. `src/models/common.py` (基础数据类型别名)

**内容:** 配置管理系统可用

### Phase 2: 数据模型定义 (3 steps)

#### Step 2.1 - 核心领域模型 [5 files]
**涉及文件:**
1. `src/models/repository.py` (Repository, Release, Asset等GitHub相关模型)
2. `src/models/metrics.py` (CodeQualityMetrics, CommunityMetrics, MaturityMetrics)
3. `src/models/analysis.py` (AnalysisResult, ProjectScore, RankedProject)
4. `src/models/session.py` (AnalysisSession, SessionSummary, LogEntry)
5. `src/models/search.py` (KeywordGroup, SearchQuery, FilterResult)

**内容:** 全部dataclass数据模型定义完成

---

#### Step 2.2 - 日志系统 [3 files]
**涉及文件:**
1. `src/utils/logger.py` (JSON结构化日志、多处理器、轮转)
2. `logs/.gitkeep` (保留日志目录)
3. `configs/config.yaml` (更新logging段落，如需调整)

**内容:** 日志系统可用，支持运行日志+对话记录保存

---

#### Step 2.3 - 存储层 [5 files]
**涉及文件:**
1. `src/storage/database.py` (SQLite schema创建、CRUD操作)
2. `src/storage/file_manager.py` (临时文件管理、结果报告写入)
3. `data/cache/.gitkeep`
4. `data/results/.gitkeep`
5. `src/utils/cache.py` (基于文件的TTL缓存、LRU策略)

**内容:** 数据持久化和缓存系统可用

### Phase 3: AI集成层 (4 steps)

#### Step 3.1 - LLM客户端核心 [4 files]
**涉及文件:**
1. `src/ai/llm_client.py` (LLMClient主类, 统一接口, Provider抽象基类)
2. `src/ai/providers/__init__.py`
3. `src/ai/providers/base.py` (BaseProvider抽象类)
4. `src/ai/prompts.py` (Prompt模板常量集中定义)

**内容:** LLM调用框架搭建完成

---

#### Step 3.2 - Provider适配器 [5 files]
**涉及文件:**
1. `src/ai/providers/ollama_provider.py` (Ollama本地模型)
2. `src/ai/providers/openai_provider.py` (OpenAI兼容API)
3. `src/ai/providers/litellm_provider.py` (LiteLLM统一路由)
4. `src/ai/llm_client.py` (更新: 注册所有provider)
5. `src/ai/__init__.py` (导出LLMClient)

**内容:** 三种AI后端全部可用，自动降级逻辑就绪

---

#### Step 3.3 - 推荐与解释模块 [4 files]
**涉及文件:**
1. `src/ai/recommender.py` (Recommender类, 排序推荐, 场景化)
2. `src/ai/explainer.py` (Explainer类, 自然语言解释生成, 中英双语)
3. `src/ai/recommendation_templates.py` (输出模板)
4. `src/ai/__init__.py` (更新导出)

**内容:** AI推荐和解释功能可用

---

#### Step 3.4 - AI测试 [5 files]
**涉及文件:**
1. `tests/unit/test_llm_client.py` (Provider选择、降级、重试逻辑测试)
2. `tests/unit/test_recommender.py` (推荐算法测试)
3. `tests/unit/test_explainer.py` (解释生成测试)
4. `tests/conftest.py` (添加mock_llm_client fixture)
5. `tests/unit/test_prompts.py` (Prompt模板格式验证)

**内容**: AI层测试覆盖完成

### Phase 4: 搜索模块 (4 steps)

#### Step 4.1 - GitHub API客户端 [4 files]
**涉及文件:**
1. `src/search/github_client.py` (GitHubClient类, REST API搜索/获取/Release下载)
2. `src/models/repository.py` (补充序列化方法, 如需要)
3. `tests/unit/test_github_client.py` (API解析、分页、限速处理测试)
4. `tests/conftest.py` (添加mock_github_client fixture)

**内容**: GitHub API交互能力可用

---

#### Step 4.2 - 关键词生成器 [3 files]
**涉及文件:**
1. `src/search/keyword_generator.py` (KeywordGenerator类, 调用LLM生成搜索词组)
2. `tests/unit/test_keyword_generator.py` (关键词生成逻辑测试)
3. `src/ai/prompts.py` (确认KEYWORD_GENERATION_PROMPT存在)

**内容**: AI驱动的关键词扩展功能可用

---

#### Step 4.3 - 项目过滤器 [4 files]
**涉及文件:**
1. `src/search/project_filter.py` (ProjectFilter类, AI相关性判断+规则过滤)
2. `tests/unit/test_project_filter.py` (过滤逻辑、阈值、数量控制测试)
3. `src/ai/prompts.py` (确认RELEVANCE_JUDGMENT_PROMPT存在)
4. `src/models/search.py` (补充FilterResult方法, 如需要)

**内容**: 相关性过滤和数量控制可用

---

#### Step 4.4 - Search模块整合 [3 files]
**涉及文件:**
1. `src/search/__init__.py` (导出公开接口)
2. `tests/integration/test_search_pipeline.py` (搜索→过滤集成测试)
3. `configs/config.yaml` (确认search配置段完整)

**内容**: 搜索模块完整可用

### Phase 5: 分析模块 (4 steps)

#### Step 5.1 - 代码分析器 [5 files]
**涉及文件:**
1. `src/analysis/code_analyzer.py` (CodeAnalyzer类, 下载→解压→静态分析→评分)
2. `tests/unit/test_code_analyzer.py` (分析规则、评分计算测试)
3. `src/storage/file_manager.py` (补充代码下载/清理方法)
4. `src/utils/cache.py` (补充分析缓存逻辑, 如需要)
5. `tests/conftest.py` (添加sample_codebase fixture)

**内容**: 代码质量多维分析可用

---

#### Step 5.2 - 社区分析器 [4 files]
**涉及文件:**
1. `src/analysis/community_analyzer.py` (CommunityAnalyzer类, GitHub API获取社区指标)
2. `tests/unit/test_community_analyzer.py` (指标计算、增长率测试)
3. `src/search/github_client.py` (补充commits/issues/contributors查询方法)
4. `src/models/metrics.py` (补充CommunityMetrics计算方法, 如需要)

**内容**: 社区活跃度评估可用

---

#### Step 5.3 - 成熟度分析器 [4 files]
**涉及文件:**
1. `src/analysis/maturity_analyzer.py` (MaturityAnalyzer类, 版本/CI/治理评估)
2. `tests/unit/test_maturity_analyzer.py` (成熟度等级判定测试)
3. `src/search/github_client.py` (补充releases/contributing_guide等查询)
4. `src/analysis/__init__.py` (导出三个分析器)

**内容**: 项目成熟度评估可用

---

#### Step 5.4 - 分析模块整合与并行执行 [4 files]
**涉及文件:**
1. `src/analysis/pipeline.py` (AnalysisPipeline类, 并行调度三个分析器)
2. `tests/integration/test_analysis_pipeline.py` (端到端分析流程测试)
3. `src/analysis/__init__.py` (导出Pipeline)
4. `configs/config.yaml` (确认analysis配置段完整)

**内容**: 分析引擎完整可用，支持并行执行

### Phase 6: 评分排名模块 (3 steps)

#### Step 6.1 - 评分计算器 [4 files]
**涉及文件:**
1. `src/scoring/score_calculator.py` (ScoreCalculator类, 6维加权评分, min-max标准化)
2. `tests/unit/test_score_calculator.py` (标准化公式、加权求和、边界条件测试)
3. `configs/scoring_weights.yaml` (权重配置加载验证)
4. `src/models/analysis.py` (补充ProjectScore序列化, 如需要)

**内容**: 多维评分体系可用

---

#### Step 6.2 - 排名引擎 [4 files]
**涉及文件:**
1. `src/scoring/ranking_engine.py` (RankingEngine类, 综合/单维度/偏好排名, 分档)
2. `tests/unit/test_ranking_engine.py` (排名正确性、S/A/B/C/D分档测试)
3. `src/models/analysis.py` (补充RankedProject数据类)
4. `src/scoring/__init__.py` (导出ScoreCalculator和RankingEngine)

**内容**: 排名和分档功能可用

---

#### Step 6.3 - Scoring模块整合 [3 files]
**涉及文件:**
1. `src/scoring/pipeline.py` (ScoringPipeline, 批量评分→排名)
2. `tests/integration/test_scoring_pipeline.py` (评分排名端到端测试)
3. `configs/config.yaml` (确认scoring配置段)

**内容**: 评分排名流水线完整

### Phase 7: 主程序与报告 (3 steps)

#### Step 7.1 - CLI完善与主流程 [3 files]
**涉及文件:**
1. `src/main.py` (完整实现async main(), CLI参数处理, 流程编排)
2. `src/pipeline/orchestrator.py` (Orchestrator类, 协调search→analysis→scoring→ai全流程)
3. `src/pipeline/__init__.py`

**内容**: 端到端主流程可运行

---

#### Step 7.2 - 报告生成器 [5 files]
**涉及文件:**
1. `src/report/generator.py` (ReportGenerator类, Markdown/JSON/终端表格输出)
2. `src/report/templates/` (Jinja2报告模板: summary.md.json, detail.md.json)
3. `src/report/templates/__init__.py`
4. `src/report/__init__.py`
5. `requirements/base.txt` (添加jinja2依赖, 如尚未包含)

**内容**: 多格式报告生成可用

---

#### Step 7.3 - 运行总结与Git提交 [4 files]
**涉及文件:**
1. `src/utils/session_manager.py` (SessionManager类, 运行总结生成, 经验积累)
2. `src/main.py` (集成总结步骤和auto-commit选项)
3. `src/utils/git_helper.py` (Git操作封装, auto commit)
4. `tests/integration/test_full_workflow.py` (完整工作流集成测试)

**内容**: 运行总结、经验积累、自动提交功能可用

### Phase 8: 补充测试 (2 steps)

#### Step 8.1 - 补充单元测试至覆盖率达标 [5 files]
**涉及文件:**
1-5. 针对覆盖率不足的核心模块补充测试文件
(具体文件根据实际覆盖率决定)

**目标**: 总体行覆盖率≥80%, 核心业务逻辑≥90%

---

#### Step 8.2 - Fixtures完善与Mock数据集 [4 files]
**涉及文件:**
1. `tests/conftest.py` (完善所有fixtures)
2. `tests/fixtures/sample_repository.json` (示例仓库数据)
3. `tests/fixtures/sample_analysis_result.json` (示例分析结果)
4. `tests/fixtures/.gitkeep`

**内容**: 测试基础设施完善

### Phase 9: CI/CD与文档 (3 steps)

#### Step 9.1 - GitHub Actions CI [3 files]
**涉及文件:**
1. `.github/workflows/ci.yml` (lint + test + security检查)
2. `.github/workflows/analysis.yml` (定期分析schedule任务, 可选)
3. `requirements/dev.txt` (确认包含safety, bandit, black, pylint, mypy)

**内容**: CI流水线可用

---

#### Step 9.2 - README文档 (2 files)
**涉及文件:**
1. `README.md` (中英双语: 项目介绍/快速开始/使用示例/开发指南/贡献指南)
2. `LICENSE` (确认license内容, 如需更新)

**内容**: 项目文档完整

---

#### Step 9.3 - 最终整合验证 [3 files]
**涉及文件:**
1. `docs/design_spec.md` (如有需要, 更新为最终状态)
2. `CHANGELOG.md` (初始版本变更记录)
3. `configs/config.yaml` (最终配置审校)

**内容**: 项目发布就绪

---

## 步骤统计总览

| Phase | 描述 | Steps | 每步最大文件数 |
|-------|------|-------|--------------|
| 1 | 项目骨架 | 5 | 5 |
| 2 | 数据模型 | 3 | 5 |
| 3 | AI集成层 | 4 | 5 |
| 4 | 搜索模块 | 4 | 5 |
| 5 | 分析模块 | 4 | 5 |
| 6 | 评分排名 | 3 | 5 |
| 7 | 主程序报告 | 3 | 5 |
| 8 | 补充测试 | 2 | 5 |
| 9 | CI/CD文档 | 3 | 5 |
| **总计** | | **31 steps** | **≤5** |

---

## Key Technical Decisions (关键技术决策)

1. **异步框架**: 使用asyncio + httpx进行异步HTTP调用，提升并发性能
2. **配置格式**: YAML为主配置格式，支持环境变量注入
3. **数据库**: SQLite作为本地存储(轻量、无需额外服务)
4. **LLM抽象**: LiteLLM作为统一接口层，Ollama为默认后端
5. **代码分析**: 规则-based分析为主(正则+AST)，工具辅助(radon可选)
6. **CLI框架**: 使用argparse(标准库)或typer(更现代的选择)
7. **输出格式**: Rich库用于终端美化输出，Jinja2用于报告模板
