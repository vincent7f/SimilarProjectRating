# Similar Project Rating System - 设计与需求文档

## 1. 项目概述

### 1.1 核心目标
开发一个智能的GitHub开源项目分析与比较系统。该系统能够：
1. 根据用户输入的关键词，自动搜索GitHub上功能相似的开源项目
2. 多维度分析这些项目的质量指标（代码质量、社区活跃度、功能完整性等）
3. 提供综合评分和AI推荐建议
4. 自动化执行和持续优化

### 1.2 项目优势
- **智能搜索**：AI生成优化的搜索关键词组合
- **精确过滤**：AI驱动的相关性分析和自动过滤
- **多维评估**：基于数据驱动的量化评分体系
- **持续学习**：每次运行的反馈循环优化后续分析

## 2. 功能需求规格

### 2.1 核心功能模块

#### 2.1.1 智能搜索模块 (Intelligent Search Module)
**输入**：用户查询关键词（自然语言）
**输出**：优化的GitHub搜索关键词组
**技术要求**：
1. 使用AI模型生成3-5组相关搜索关键词组合
2. 每组关键词包含主关键词和相关扩展词
3. 关键词组合需考虑：功能名称、技术栈、应用场景、实现方式

**处理流程**：
```
用户输入 → AI关键词生成 → 搜索关键词组 → GitHub API搜索
```

#### 2.1.2 项目收集与过滤模块 (Project Collection & Filtering)
**输入**：搜索关键词组
**输出**：相关且高质量的项目列表
**技术要求**：
1. 通过GitHub Search API搜索项目
2. 初始搜索结果最大数量：每个关键词组50个项目
3. 相关性过滤：AI分析项目描述和README，过滤不相关项目
4. 数量控制：
   - 如过滤后项目>20，保留star数最高的前20个
   - 如过滤后项目≤20，全部保留
   - 最小保留项目数：5个（如不足则提示用户调整关键词）

**数据源**：
- GitHub API v4 (GraphQL) 或 v3 (REST)
- 项目元数据：star数、fork数、issues数、最近更新时间
- 项目内容：README、项目描述、语言分布

#### 2.1.3 代码分析模块 (Code Analysis Module)
**输入**：筛选后的项目列表
**输出**：各项目的代码质量评估报告
**技术要求**：
1. 代码获取策略：
   - 优先下载最新release版本的代码
   - 如无release，下载main/master分支最新提交
   - 下载方式：GitHub API或git clone
   - 大小限制：如项目过大（>50MB），仅分析核心目录

2. 代码质量指标：
   - **代码规范性**：PEP8/Google Style等编码规范检查
   - **测试覆盖率**：单元测试存在性和覆盖率（如可获取）
   - **依赖管理**：requirements.txt/setup.py等依赖文件质量
   - **文档完整性**：README、API文档、示例代码的完整性
   - **架构清晰度**：目录结构、模块化程度评估

3. 分析工具：
   - **静态分析**：pylint, flake8, black（检查）
   - **依赖分析**：safety, pip-audit（安全检查）
   - **复杂度分析**：radon（代码复杂度评估）

#### 2.1.4 社区与成熟度评估模块 (Community & Maturity Assessment)
**输入**：项目元数据和历史记录
**输出**：社区活跃度和项目成熟度评分
**评估维度**：

1. **社区活跃度指标**：
   - Star增长趋势（最近30天、90天、180天）
   - Commit频率（每周平均提交数）
   - Issue处理速度（平均解决时间）
   - 贡献者数量及增长
   - 最近更新时间（距今天数）

2. **项目成熟度指标**：
   - 版本发布历史（语义化版本使用）
   - CI/CD配置完整性
   - 文档质量（API文档、用户指南、FAQ）
   - 社区支持（Discord/Slack链接、邮件列表）

3. **网络评价数据**（需外部整合）：
   - Hacker News/B站/知乎等平台提及次数
   - 技术博客教程数量
   - 相关会议/演讲提及

#### 2.1.5 综合评分与排名模块 (Comprehensive Scoring & Ranking)
**输入**：各模块的分析结果
**输出**：多维评分和综合排名
**评分体系**：

| 维度 | 权重 | 子维度 | 评分方法 |
|------|------|--------|----------|
| 代码质量 | 25% | 规范合规、测试覆盖、依赖安全 | 静态分析工具 + 人工规则 |
| 社区活跃 | 20% | Star增长、提交频率、问题解决 | 时间序列分析 + 增长率计算 |
| 功能完整性 | 18% | 核心功能、扩展功能、文档示例 | AI评估 + 功能清单对比 |
| 项目成熟度 | 15% | 版本历史、CI/CD、生产就绪 | 发布历史分析 + 工具链检查 |
| 用户评价 | 12% | 网络声音、教程数量、社区认可 | 外部数据聚合（如有） |
| 维护可预期 | 10% | 维护团队、路线图、可持续发展 | 贡献者分析 + 项目声明 |

**评分公式**：
```
综合得分 = Σ(维度i权重 × 维度i标准化得分)
标准化得分 = (原始得分 - 最小值) / (最大值 - 最小值)
```

#### 2.1.6 AI推荐与解释模块 (AI Recommendation & Explanation)
**输入**：项目评分数据和用户上下文
**输出**：个性化推荐和详细解释
**技术要求**：
1. 推荐算法：
   - **基于评分**：综合得分排序
   - **基于偏好**：用户权重调整（如更重视社区或代码质量）
   - **基于场景**：不同使用场景推荐不同项目

2. 解释生成：
   - 每个推荐项目的原因说明
   - 项目的优缺点分析
   - 使用建议和注意事项
   - 替代方案比较

3. 输出格式：
   - 表格对比：关键指标横向对比
   - 雷达图：多维表现可视化
   - 总结报告：文字分析和建议

### 2.2 辅助功能

#### 2.2.1 日志与监控系统
**需求**：
1. 详细记录每一步操作：
   - 时间戳、操作类型、输入参数、输出结果
   - 执行耗时、资源消耗
   - 成功/失败状态、错误信息

2. 日志存储结构：
   - **运行日志**：每次执行的完整记录
   - **分析日志**：具体分析步骤的中间结果
   - **性能日志**：系统性能指标
   - **错误日志**：异常和错误信息

3. 日志格式：
   ```json
   {
     "timestamp": "2024-01-01T12:00:00Z",
     "level": "INFO",
     "module": "search",
     "operation": "github_search",
     "params": {"keywords": ["project management"]},
     "results": {"total_found": 150, "filtered": 25},
     "duration_ms": 1234,
     "success": true
   }
   ```

#### 2.2.2 反馈学习系统
**需求**：
1. 每次运行后生成总结报告：
   - 执行结果统计（成功数、失败数、用时等）
   - 遇到的问题和解决方案
   - 性能瓶颈和改进建议

2. 经验积累：
   - 保存成功的分析模式
   - 记录失败的案例和原因
   - 优化关键词生成策略
   - 调整阈值和参数

3. 报告模板：
   ```
   # 执行总结报告
   - 执行时间: [timestamp]
   - 搜索关键词: [keywords]
   - 发现项目总数: [total]
   - 分析项目数: [analyzed]
   - 平均分析时间: [avg_time]
   
   ## 成功经验
   1. [成功点1]
   2. [成功点2]
   
   ## 失败教训
   1. [失败点1 - 原因 - 解决方案]
   2. [失败点2 - 原因 - 解决方案]
   
   ## 下次优化建议
   1. [建议1]
   2. [建议2]
   ```

#### 2.2.3 自动化部署与CI/CD
**需求**：
1. GitHub Actions配置：
   - 自动测试：单元测试、集成测试
   - 代码质量检查：linting、静态分析
   - 部署流水线：测试环境部署

2. 触发机制：
   - **push事件**：代码提交时运行测试
   - **schedule事件**：定期运行完整分析（如每天）
   - **workflow_dispatch**：手动触发

3. 环境配置：
   - Python版本：3.9+ 
   - 依赖缓存：pip依赖缓存加速
   - 密钥管理：GitHub Secrets存储API密钥

## 3. 技术架构设计

### 3.1 系统架构概述
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  用户接口层     │    │  业务逻辑层     │    │  数据存储层     │
│  - CLI/GUI      │───▶│  - 搜索引擎     │───▶│  - 本地缓存     │
│  - API端点      │    │  - 分析引擎     │    │  - 数据库       │
│  - Web界面      │    │  - 评分引擎     │    │  - 文件系统     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  外部服务层     │    │  AI集成层       │    │  工具链层       │
│  - GitHub API   │    │  - Ollama       │    │  - 静态分析工具 │
│  - 网络爬虫     │    │  - OpenAI兼容   │    │  - 代码度量工具 │
│  - 数据聚合     │    │  - LiteLLM      │    │  - 可视化工具   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 3.2 模块详细设计

#### 3.2.1 核心模块清单
1. **main.py** - 主程序入口
2. **search/__init__.py** - 搜索模块
   - keyword_generator.py - 关键词生成
   - github_client.py - GitHub API客户端
   - project_filter.py - 项目过滤
   
3. **analysis/__init__.py** - 分析模块
   - code_analyzer.py - 代码分析
   - community_analyzer.py - 社区分析
   - maturity_analyzer.py - 成熟度分析
   
4. **scoring/__init__.py** - 评分模块
   - score_calculator.py - 分数计算
   - ranking_engine.py - 排名引擎
   
5. **ai/__init__.py** - AI集成模块
   - recommender.py - 推荐生成
   - explanation_generator.py - 解释生成
   
6. **utils/__init__.py** - 工具模块
   - logger.py - 日志系统
   - config.py - 配置管理
   - cache.py - 缓存系统
   
7. **storage/__init__.py** - 存储模块
   - database.py - 数据库操作
   - file_manager.py - 文件管理

#### 3.2.2 数据模型设计
```python
# 核心数据类
class Project:
    id: str  # GitHub项目ID: owner/repo
    name: str
    description: str
    stars: int
    forks: int
    issues: int
    last_updated: datetime
    primary_language: str
    topics: List[str]
    
class CodeQualityMetrics:
    pylint_score: float
    test_coverage: Optional[float]
    dependency_count: int
    security_issues: List[str]
    code_complexity: Dict[str, float]
    
class CommunityMetrics:
    star_growth_rate: float
    commit_frequency: float
    issue_resolution_time: Optional[float]
    contributor_count: int
    recent_activity_score: float
    
class AnalysisResult:
    project: Project
    code_metrics: CodeQualityMetrics
    community_metrics: CommunityMetrics
    maturity_score: float
    overall_score: float
    recommendations: List[str]
    
class AnalysisSession:
    session_id: str
    query: str
    start_time: datetime
    end_time: Optional[datetime]
    results: List[AnalysisResult]
    logs: List[LogEntry]
    summary: Optional[SessionSummary]
```

### 3.3 AI模型集成策略

#### 3.3.1 模型选择与优先级
1. **第一优先级**：本地Ollama模型
   - 优势：隐私保护、无网络依赖、成本可控
   - 模型推荐：llama3.2、mistral、codellama
   - 配置要求：最低8GB显存，推荐16GB+

2. **备选方案**：OpenAI兼容API
   - 配置：通过环境变量切换
   - 支持：ChatGPT、Claude、DeepSeek等
   - 回退机制：本地模型失败时自动切换

3. **统一接口**：LiteLLM抽象层
   - 目的：提供一致的API调用接口
   - 功能：自动路由、请求重试、失败降级

#### 3.3.2 AI应用场景
1. **关键词扩展**：
   ```
   输入: "项目管理工具"
   输出: [
     "project management tool python django",
     "task management software react",
     "kanban board github api",
     "敏捷开发工具 中文界面"
   ]
   ```

2. **相关性判断**：
   ```
   输入: 项目描述 + 用户查询
   输出: 相关性分数 (0-1) + 判断理由
   ```

3. **推荐解释生成**：
   ```
   输入: 项目数据 + 对比结果
   输出: 自然语言解释 + 优缺点分析
   ```

### 3.4 配置管理

#### 3.4.1 配置文件结构
```yaml
# config.yaml
github:
  api_token: ${GITHUB_TOKEN}
  rate_limit: 5000
  timeout_seconds: 30
  
ai:
  provider: "ollama"  # ollama, openai, anthropic
  model: "llama3.2:latest"
  api_base: "http://localhost:11434"
  api_key: ${AI_API_KEY}
  fallback_enabled: true
  
analysis:
  max_projects: 20
  min_similarity_score: 0.6
  download_timeout: 300
  max_code_size_mb: 50
  
scoring:
  weights:
    code_quality: 0.25
    community: 0.20
    functionality: 0.18
    maturity: 0.15
    reputation: 0.12
    sustainability: 0.10
  
logging:
  level: "INFO"
  file_path: "./logs"
  max_size_mb: 100
  backup_count: 5
```

#### 3.4.2 环境变量要求
```bash
# 必需的环境变量
export GITHUB_TOKEN="your_github_personal_token"
export AI_MODEL="llama3.2:latest"  # 或使用其他模型

# 可选的环境变量
export OPENAI_API_KEY=""  # 如需使用OpenAI
export ANTHROPIC_API_KEY=""  # 如需使用Claude
export LITELLM_MODEL=""  # LiteLLM配置
```

## 4. 开发规范与流程

### 4.1 代码规范
1. **语言要求**：
   - 代码注释：英文（符合国际协作标准）
   - 提交信息：英文（Git commit messages）
   - 文档：中英双语（中文段落 + 对应英文段落）

2. **代码风格**：
   - **Python**：PEP 8 + Black格式化
   - **类型提示**：全面使用type hints
   - **文档字符串**：Google风格docstring
   - **测试覆盖率**：≥80%的单元测试覆盖率

3. **目录结构**：
   ```
   similar_project_rating/
   ├── src/
   │   ├── search/
   │   ├── analysis/
   │   ├── scoring/
   │   ├── ai/
   │   ├── utils/
   │   └── storage/
   ├── tests/
   │   ├── unit/
   │   └── integration/
   ├── logs/
   ├── data/
   │   ├── cache/
   │   └── results/
   ├── docs/
   ├── configs/
   ├── scripts/
   └── requirements/
   ```

### 4.2 Git工作流
1. **分支策略**：
   ```
   main (protected) - 生产就绪代码
   ├── develop - 开发集成分支
   ├── feature/* - 功能分支
   ├── bugfix/* - 缺陷修复
   └── release/* - 发布准备
   ```

2. **Git Worktree使用**：
   - 为并行开发任务创建独立工作树
   - 避免分支切换导致的上下文丢失
   - 支持多环境同时测试

3. **提交规范**：
   ```
   类型(范围): 简明描述
    
   详细说明（可选）
    
   - 变更点1
   - 变更点2
   
   关联Issue: #123
   
   # 类型标签
   feat: 新功能
   fix: 错误修复
   docs: 文档更新
   style: 代码样式调整
   refactor: 代码重构
   test: 测试相关
   chore: 构建/工具更新
   ```

### 4.3 质量保障

#### 4.3.1 测试策略
1. **单元测试**：
   - 覆盖所有核心业务逻辑
   - 使用pytest框架
   - Mock外部依赖（GitHub API、AI服务）

2. **集成测试**：
   - 测试模块间协作
   - 包含真实API调用（使用测试token）
   - 验证端到端流程

3. **性能测试**：
   - 单次分析时间目标：<5分钟（20个项目）
   - 内存使用峰值：<2GB
   - 并发处理能力测试

4. **回归测试**：
   - 保存分析案例作为测试基准
   - 确保评分一致性
   - 监控准确率变化

#### 4.3.2 代码审查
1. **自动检查**：
   - GitHub Actions自动运行linter和测试
   - 代码覆盖率报告
   - 安全漏洞扫描

2. **人工审查**：
   - 至少1名团队成员review
   - 关注：逻辑正确性、性能影响、安全性
   - 文档更新同步

## 5. 部署与运维

### 5.1 部署架构
1. **本地开发环境**：
   - Python 3.9+
   - Ollama本地运行
   - GitHub CLI工具

2. **CI/CD环境**：
   - GitHub Actions Runner
   - Docker容器化执行
   - 自动化测试流水线

3. **生产环境（可选）**：
   - 云服务器部署
   - Docker Compose编排
   - 监控和告警

### 5.2 监控与维护
1. **健康检查**：
   - API可用性监控
   - 分析任务成功率
   - 资源使用情况

2. **日志分析**：
   - 错误率统计
   - 性能趋势分析
   - 用户行为分析

3. **数据维护**：
   - 定期清理缓存
   - 备份重要分析结果
   - 更新评估基准

### 5.3 灾难恢复
1. **数据备份**：
   - 配置文件备份
   - 评分模型备份
   - 用户偏好备份

2. **故障转移**：
   - AI服务降级策略
   - GitHub API限速处理
   - 网络异常恢复

## 6. 成功指标与评估

### 6.1 功能性指标
1. **搜索准确率**：相关项目检索准确率 ≥85%
2. **分析完整性**：完整分析成功率 ≥90%
3. **响应时间**：单次完整分析 <10分钟
4. **推荐有用性**：用户满意度评分 ≥4.0/5.0

### 6.2 技术性指标
1. **代码质量**：pylint评分 ≥8.0/10
2. **测试覆盖率**：≥80%行覆盖率
3. **API稳定性**：99%正常运行时间
4. **资源效率**：内存使用 <2GB，CPU使用 <80%

### 6.3 用户价值指标
1. **决策辅助效果**：减少用户调研时间 ≥50%
2. **发现新项目能力**：至少推荐1个用户未知但相关的优质项目
3. **解释满意度**：推荐理由清晰度评分 ≥4.0/5.0

## 7. 版本规划

### 7.1 MVP版本 (v0.1.0)
**核心功能**：
1. 基础GitHub搜索和过滤
2. 简单的代码质量分析
3. 基本评分算法
4. 本地Ollama集成

**时间预估**：2-3周

### 7.2 完整版本 (v1.0.0)
**新增功能**：
1. 完整的多维评估体系
2. 智能推荐和解释
3. 丰富的可视化和报告
4. 完整的CI/CD流水线

**时间预估**：4-6周（从MVP开始）

### 7.3 增强版本 (v2.0.0)
**路线图功能**：
1. 多数据源整合（GitLab、Bitbucket等）
2. 深度学习模型优化
3. 实时监控和告警
4. 团队协作功能

**时间预估**：8-12周（从v1.0开始）

## 8. 风险评估与缓解

### 8.1 技术风险
1. **GitHub API限制**：
   - 风险：API调用频率限制
   - 缓解：实现请求队列和限速控制

2. **AI模型质量**：
   - 风险：本地模型效果不佳
   - 缓解：多模型支持 + 人工规则补充

3. **代码分析准确性**：
   - 风险：静态分析工具误判
   - 缓解：多工具交叉验证 + 人工审核机制

### 8.2 项目风险
1. **需求变更**：
   - 风险：功能范围扩大
   - 缓解：明确MVP范围 + 增量开发

2. **时间延误**：
   - 风险：复杂功能开发超时
   - 缓解：优先级排序 + 定期进度评估

3. **技术债务**：
   - 风险：快速开发积累技术债务
   - 缓解：代码审查 + 重构计划

## 9. 附录

### 9.1 术语表
- **STAR**：GitHub上的收藏数量，代表项目受欢迎程度
- **FORK**：项目复制到用户自己账户的数量
- **ISSUE**：项目的任务、缺陷或功能请求
- **PR/Pull Request**：贡献者提交的代码合并请求
- **CI/CD**：持续集成/持续部署
- **Ollama**：本地运行的LLM框架
- **LiteLLM**：统一的大模型调用接口

### 9.2 参考资源
1. [GitHub REST API文档](https://docs.github.com/en/rest)
2. [GitHub GraphQL API文档](https://docs.github.com/en/graphql)
3. [Ollama官方文档](https://ollama.ai/)
4. [LiteLLM官方文档](https://docs.litellm.ai/)
5. [Python代码质量工具](https://realpython.com/python-code-quality/)

### 9.3 维护联系人
- **项目负责人**：[待指定]
- **技术支持**：[待指定]
- **文档维护**：[待指定]

---

*文档版本：v1.0*
*最后更新：2026-04-04*
*状态：草案，待评审*