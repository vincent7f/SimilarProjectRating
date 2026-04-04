---
name: similar-project-rating-impl
overview: 基于basic.md和design_spec.md，从零构建GitHub开源项目智能分析与比较系统（Python实现），共31个原子化步骤，每步≤5文件
design:
  styleKeywords:
    - Professional Engineering Tool
    - CLI Terminal Aesthetic
    - High Information Density
    - Rich Library Enhanced Output
    - GitHub Dark Theme Inspired
    - Bilingual Report Generation
  fontSystem:
    fontFamily: JetBrains Mono
    heading:
      size: 18px
      weight: 700
    subheading:
      size: 14px
      weight: 600
    body:
      size: 13px
      weight: 400
  colorSystem:
    primary:
      - "#0366D6"
      - "#28A745"
    background:
      - "#0D1117"
      - "#161B22"
    text:
      - "#C9D1D9"
      - "#8B949E"
    functional:
      - "#F85149"
      - "#58A6FF"
todos:
  - id: step-1-1
    content: Create core package __init__.py files for src/search, src/analysis, src/scoring, src/ai modules (5 files max per step)
    status: completed
  - id: step-1-2
    content: Create utils/storage/test package init files, main.py CLI skeleton with argparse, test init structure (5 files)
    status: completed
    dependencies:
      - step-1-1
  - id: step-1-3
    content: Add test integration init, conftest template, pyproject.toml, .gitignore, .editorconfig (5 files)
    status: completed
    dependencies:
      - step-1-2
  - id: step-1-4
    content: Create requirements/base.txt, dev.txt, ai.txt dependency declaration files (3 files)
    status: completed
    dependencies:
      - step-1-3
  - id: step-1-5
    content: Implement utils/config.py Config dataclass with YAML loading and env var support, configs/config.yaml full defaults, scoring_weights.yaml, models package init (5 files)
    status: completed
    dependencies:
      - step-1-4
  - id: step-2-1
    content: "Define all domain dataclasses: repository.py, metrics.py, analysis.py, session.py, search.py under src/models/ (5 files)"
    status: completed
    dependencies:
      - step-1-5
  - id: step-2-2
    content: Implement utils/logger.py structured JSON logging with rotation and dual output, logs/.gitkeep (3 files)
    status: completed
    dependencies:
      - step-2-1
  - id: step-2-3
    content: Implement storage/database.py SQLite CRUD, storage/file_manager.py for temp file ops, utils/cache.py TTL file cache, data dir gitkeeps (5 files)
    status: completed
    dependencies:
      - step-2-2
  - id: step-3-1
    content: Build ai/llm_client.py LLMClient unified interface, providers/base.py BaseProvider abstract class, ai/prompts.py templates, providers/__init__.py (5 files)
    status: completed
    dependencies:
      - step-2-3
  - id: step-3-2
    content: Implement Ollama/OpenAI/LiteLLM provider adapters in providers/, register in llm_client.py, update ai/__init__ exports (5 files)
    status: completed
    dependencies:
      - step-3-1
  - id: step-3-3
    content: Implement ai/recommender.py Recommender, ai/explainer.py Explainer with bilingual output, recommendation_templates.py (4 files)
    status: completed
    dependencies:
      - step-3-2
  - id: step-3-4
    content: "Write AI layer unit tests: test_llm_client.py, test_recommender.py, test_explainer.py, test_prompts.py, update conftest mock_llm_client (5 files)"
    status: completed
    dependencies:
      - step-3-3
  - id: step-4-1
    content: Implement search/github_client.py GitHubClient REST API methods for search/fetch/release/archive, unit tests, conftest fixtures (4 files)
    status: completed
    dependencies:
      - step-2-1
  - id: step-4-2
    content: Implement search/keyword_generator.py calling LLM for keyword generation, unit tests, verify prompt templates (3 files)
    status: completed
    dependencies:
      - step-4-1
      - step-3-1
  - id: step-4-3
    content: Implement search/project_filter.py with AI relevance filtering and star-based top-20 ranking, unit tests (4 files)
    status: completed
    dependencies:
      - step-4-2
  - id: step-4-4
    content: Integrate search module exports, write test_search_pipeline.py integration test, verify config section (3 files)
    status: completed
    dependencies:
      - step-4-3
  - id: step-5-1
    content: Implement analysis/code_analyzer.py download-extract-analyze-score pipeline, unit tests, extend file_manager for code downloads (5 files)
    status: completed
    dependencies:
      - step-4-4
      - step-2-3
  - id: step-5-2
    content: Implement analysis/community_analyzer.py for community metrics via GitHub API, unit tests, extend github_client queries (4 files)
    status: completed
    dependencies:
      - step-5-1
      - step-4-1
  - id: step-5-3
    content: Implement analysis/maturity_analyzer.py for version/CI/governance assessment, unit tests, extend github_client metadata (4 files)
    status: completed
    dependencies:
      - step-5-2
  - id: step-5-4
    content: Implement analysis/pipeline.py parallel orchestrator for 3 analyzers, integration test, export analyzers (4 files)
    status: completed
    dependencies:
      - step-5-3
  - id: step-6-1
    content: Implement scoring/score_calculator.py 6-dimension weighted min-max normalization, unit tests, validate weights yaml (4 files)
    status: completed
    dependencies:
      - step-5-4
  - id: step-6-2
    content: Implement scoring/ranking_engine.py with comprehensive/preference ranking and S/A/B/C/D tiering, unit tests, add RankedProject model (4 files)
    status: completed
    dependencies:
      - step-6-1
  - id: step-6-3
    content: Implement scoring/pipeline.py batch score-to-rank flow, integration test, verify scoring config (3 files)
    status: completed
    dependencies:
      - step-6-2
  - id: step-7-1
    content: Complete src/main.py async main orchestration flow, implement pipeline/orchestrator.py coordinating all modules (3 files)
    status: completed
    dependencies:
      - step-6-3
      - step-3-3
  - id: step-7-2
    content: Implement report/generator.py multi-format output with Rich terminal tables and Jinja2 templates, add jinja2 dependency (5 files)
    status: completed
    dependencies:
      - step-7-1
  - id: step-7-3
    content: Implement utils/session_manager.py run summaries, integrate auto-commit into main.py, utils/git_helper.py wrapper, full workflow test (4 files)
    status: completed
    dependencies:
      - step-7-2
  - id: step-8-1
    content: Supplement unit tests to achieve >=80% line coverage across all core modules focusing on edge cases (up to 5 test files)
    status: completed
    dependencies:
      - step-7-3
  - id: step-8-2
    content: Complete conftest.py all shared fixtures, add sample JSON fixture data under tests/fixtures/, ensure completeness (4 files)
    status: completed
    dependencies:
      - step-8-1
  - id: step-9-1
    content: Create .github/workflows/ci.yml with lint+test+security stages, optionally analysis.yml scheduled workflow (3 files)
    status: completed
    dependencies:
      - step-8-2
  - id: step-9-2
    content: Write comprehensive README.md with bilingual content covering intro/quick-start/usage/dev-guide/contributing, verify LICENSE (2 files)
    status: completed
    dependencies:
      - step-9-1
  - id: step-9-3
    content: "Final validation: review design_spec.md consistency, create CHANGELOG.md initial version, audit final configs (3 files)"
    status: completed
    dependencies:
      - step-9-2
---

## 产品概述

构建一个 GitHub 开源项目智能分析与比较系统（Similar Project Rating System）。用户输入自然语言查询关键词，系统通过 AI 生成多组优化搜索词，在 GitHub 上搜索相关开源项目，利用 AI 过滤不相关项目，然后从代码质量、社区活跃度、功能完整性、成熟度、用户评价、维护可持续性 6 个维度进行深度分析评分，最终给出综合排名和 AI 推荐建议。仅下载最新 release 版本（无 release 则下载最新版本）进行分析。

## 核心功能

- **AI 智能搜索**：用户输入查询 -> LLM 生成多组 GitHub 搜索关键词 -> GitHub API 搜索 -> AI 相关性过滤（保留 top 20 by stars）
- **多维分析引擎**：代码质量静态分析（规范/测试/依赖/文档/架构）、社区活跃度分析（star 增长/提交频率/issue 处理）、成熟度评估（版本管理/CI-CD/治理）
- **6 维加权评分**：代码质量 25% / 社区活跃 20% / 功能完整性 18% / 成熟度 15% / 用户评价 12% / 维护可持续 10%，min-max 标准化后加权求和
- **AI 推荐与解释**：基于评分的排序推荐 + S/A/B/C/D 分档 + 自然语言优缺点分析和使用建议 + 中英双语输出
- **基础设施**：结构化 JSON 日志系统（每步记录 + 独立运行日志 + CodeBuddy 对话记录保存）、SQLite 存储、文件缓存、每次运行总结报告（成功/失败经验 + 下次建议）
- **工程规范**：Python 3.9+ 实现、GitHub Actions CI/CD、git worktree 并行开发、文档中英双语、代码提交仅英文

## 工程约束

**每步修改/提交最多涉及 5 个文件**，超出必须拆分为更小子任务。

## 技术栈

- **语言**: Python 3.9+ (type hints 全覆盖, PEP 8, Google-style docstrings)
- **异步 HTTP**: asyncio + httpx (并发 API 调用)
- **配置管理**: YAML (PyYAML) + 环境变量注入 (${VAR} 语法)
- **本地存储**: SQLite (轻量级, 无额外服务依赖)
- **LLM 集成**: Ollama (优先) -> OpenAI 兼容 API (备选) -> LiteLLM (统一路由层)
- **CLI 框架**: argparse (标准库) + Rich (终端美化输出)
- **报告模板**: Jinja2 (Markdown/JSON 多格式输出)
- **测试**: pytest + pytest-cov (目标覆盖率 >=80%, 核心逻辑 >=90%)
- **代码质量**: Black (格式化) + pylint (检查) + mypy (类型)
- **安全**: safety (依赖审计) + bandit (安全扫描)

## 实现方案

采用分层架构：用户接口层(CLI) -> 业务逻辑层(search/analysis/scoring/ai) -> 数据存储层(storage/utils)。使用 dataclass 定义全部领域模型，asyncio 编排并行分析流程，Provider 模式抽象 LLM 后端。每个模块独立可测试，通过 mock 隔离外部依赖。

### 架构设计

```mermaid
graph TB
    subgraph CLI[User Interface Layer]
        Main[main.py - CLI Entry]
    end
    
    subgraph BL[Business Logic Layer]
        subgraph Search[Search Module]
            KG[keyword_generator]
            GC[github_client]
            PF[project_filter]
        end
        subgraph Analysis[Analysis Module]
            CA[code_analyzer]
            CM[community_analyzer]
            MA[maturity_analyzer]
            AP[analysis_pipeline]
        end
        subgraph Scoring[Scoring Module]
            SC[score_calculator]
            RE[ranking_engine]
        end
    end
    
    subgraph AI_Layer[AI Integration Layer]
        LC[llm_client]
        REC[recommender]
        EXP[explainer]
        subgraph Providers[Providers]
            OP[ollama_provider]
            OAP[openai_provider]
            LP[litellm_provider]
        end
    end
    
    subgraph Infra[Infrastructure Layer]
        CFG[config.py]
        LOG[logger.py]
        CACH[cache.py]
        DB[database.py]
        FM[file_manager]
    end
    
    Main --> KG --> LC
    Main --> GC
    Main --> PF --> LC
    Main --> AP --> CA and CM and MA
    AP --> SC
    SC --> RE
    RE --> REC --> EXP
    LC --> OP and OAP and LP
    AP --> DB and CACH and FM
    Main --> LOG
```

### 关键实现细节

- **数据流**: 用户查询 -> AI 关键词生成(3-5 组) -> GitHub API 搜索(每组 <=50 结果) -> AI 相关性过滤(threshold>=0.6) -> Top20 by Stars -> 并行三维度分析 -> 6 维加权评分 -> 综合排名(S/A/B/C/D) -> AI 推荐解释 -> 报告输出
- **GitHub API 限速处理**: 检测剩余配额 -> 排队等待 -> 指数退避重试 -> 缓存避免重复请求
- **代码下载策略**: 优先 Release archive -> 无 Release 则 default branch archive -> >50MB 仅分析核心目录
- **LLM 降级**: Ollama 不可用自动切换 OpenAI -> 再降级 LiteLLM -> 最终规则回退
- **日志格式**: 结构化 JSON, 包含 timestamp/level/module/operation/params/results/duration_ms/success/error

### 目录结构摘要

```
similar_project_rating/
├── src/                          # 主源码包
│   ├── main.py                   # CLI 入口和主流程编排
│   ├── models/                   # 数据模型子包
│   │   ├── repository.py         # Repository, Release, Asset 等
│   │   ├── metrics.py            # CodeQualityMetrics, CommunityMetrics...
│   │   ├── analysis.py           # AnalysisResult, ProjectScore, RankedProject
│   │   ├── session.py            # AnalysisSession, SessionSummary, LogEntry
│   │   └── search.py             # KeywordGroup, SearchQuery, FilterResult
│   ├── search/                   # 搜索模块
│   │   ├── keyword_generator.py  # AI 关键词生成器
│   │   ├── github_client.py      # GitHub REST API v3 客户端
│   │   └── project_filter.py     # AI 相关性过滤器
│   ├── analysis/                 # 分析模块
│   │   ├── code_analyzer.py      # 代码质量静态分析
│   │   ├── community_analyzer.py # 社区活跃度评估
│   │   ├── maturity_analyzer.py  # 项目成熟度评估
│   │   └── pipeline.py           # 并行分析调度管线
│   ├── scoring/                  # 评分排名模块
│   │   ├── score_calculator.py   # 6 维加权评分计算(min-max 标准化)
│   │   ├── ranking_engine.py     # 排名引擎(S/A/B/C/D 分档)
│   │   └── pipeline.py           # 批量评分流水线
│   ├── ai/                       # AI 集成模块
│   │   ├── llm_client.py         # LLM 统一调用客户端
│   │   ├── providers/            # Provider 适配器子包
│   │   ├── prompts.py            # Prompt 模板集中定义
│   │   ├── recommender.py        # 推荐排序生成器
│   │   └── explainer.py          # 自然语言解释生成器
│   ├── utils/                    # 工具模块
│   │   ├── config.py             # YAML 配置加载与环境变量解析
│   │   ├── logger.py             # 结构化 JSON 日志系统
│   │   └── cache.py              # 文件系统 TTL 缓存(LRU)
│   ├── storage/                  # 存储模块
│   │   ├── database.py           # SQLite CRUD 操作
│   │   └── file_manager.py       # 文件管理与报告写入
│   ├── pipeline/                 # 流水线编排模块
│   │   └── orchestrator.py       # 全流程编排协调器
│   └── report/                   # 报告生成模块
│       ├── generator.py          # 多格式报告生成器
│       └── templates/            # Jinja2 报告模板
├── tests/                        # 测试套件
│   ├── conftest.py               # 共享 pytest fixtures
│   ├── unit/                     # 单元测试
│   └── integration/              # 集成测试
├── configs/                      # 配置文件
│   ├── config.yaml               # 主配置
│   └── scoring_weights.yaml      # 评分权重
├── requirements/                 # Python 依赖
│   ├── base.txt                  # 运行时依赖
│   ├── dev.txt                   # 开发工具依赖
│   └── ai.txt                    # AI 可选依赖
├── .github/workflows/            # CI/CD
│   └── ci.yml
├── pyproject.toml                # 项目构建配置
├── .gitignore
├── .editorconfig
└── README.md                     # 中英双语文档
```

本项目为纯后端 Python CLI 工具，无前端 UI 界面。设计重点在于终端输出体验和报告文档的美观性。

终端输出采用 Rich 库实现：彩色表格对比项目指标、进度条显示各阶段分析进度、Panel 展示最终推荐结果、Syntax 高亮展示代码片段和关键数据。整体终端风格参考 GitHub CLI 的专业工程感。

报告输出采用 Jinja2 Markdown 模板：包含雷达图数据描述（支持后续可视化）、多项目横向对比表格、每个项目的详细文字分析和中英双语文本说明。报告追求信息密度高、层次清晰、可读性强。

整体配色采用 GitHub 风格暗色系：深色背景(#0D1117)、蓝色主调(#0366D6)、绿色成功(#28A745)、红色警告(#F85149)，营造专业的开发者工具氛围。

## Agent Extensions

### Skill: superpowers

- **Purpose**: 在整个开发过程中遵循软件工程最佳实践，包括 TDD（先写测试再写实现）、系统性调试方法、code review 工作流、结构化的计划执行和复盘
- **Expected Outcome**: 确保 31 步实施过程遵循专业工程标准，每步产出高质量代码，测试先行，持续验证

### SubAgent: code-explorer

- **Purpose**: 当需要跨多个文件搜索模式、理解代码依赖关系、或在重构时定位所有受影响的调用点时使用
- **Expected Outcome**: 在后续步骤中快速定位需要修改的目标文件和依赖关系，减少手动搜索时间，确保修改完整性