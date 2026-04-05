# Similar Project Rating System

## 相似项目评分系统 / GitHub开源项目智能分析与比较工具

An AI-powered system that analyzes, scores, ranks, and recommends similar
GitHub open-source projects across multiple dimensions. Users input a natural language
query, and the system provides comprehensive comparisons with AI-generated insights.

一个AI驱动的系统，用于在多个维度上分析、评分、排名和推荐相似的GitHub开源项目。
用户输入自然语言查询，系统提供带有AI生成洞察的综合比较。

### Features / 功能特性

- **AI-Powered Search**: LLM generates optimized GitHub search keyword groups
  **AI智能搜索**：LLM生成优化的GitHub搜索关键词组
- **Multi-Dimensional Scoring**: Code quality (25%), Community (20%), Functionality (18%),
  Maturity (15%), Reputation (12%), Sustainability (10%)
  **多维评分**：代码质量(25%)、社区(20%)、功能完整性(18%)、成熟度(15%)、用户评价(12%)、维护可持续性(10%)
- **Smart Filtering**: AI relevance check removes irrelevant projects, keeps top-N by stars
  **智能过滤**：AI相关性检查移除不相关项目，保留按stars排序的前N个
- **Bilingual Reports**: Chinese + English output for all recommendations and explanations
  **双语报告**：所有推荐和解释的中英文输出
- **Structured Logging**: Every step logged in JSON format with session summaries
  **结构化日志**：每步以JSON格式记录，附带会话总结
- **Auto Git Commit**: Results automatically committed after each run (optional)
  **自动Git提交**：每次运行后结果自动提交（可选）

### Quick Start / 快速开始

```bash
# Install dependencies / 安装依赖
pip install -r requirements/base.txt -r requirements/ai.txt

# Run environment check first (recommended) / 先运行环境检查(推荐)
python -m src.utils.environment_checker
# or / 或
python scripts/env_check.py

# Run analysis / 运行分析 (requires Ollama running locally)
# （需要本地运行Ollama）
python -m src.main "project management tool"

# With options / 带选项
python -m src.main "react component library" --max-projects 15 --verbose
python -m src.main "database orm" --provider openai --model gpt-4 --dry-run
python -m src.main "OpenClaw AI agent" --env-check-only --strict-check
```

### Prerequisites / 前置条件

- Python 3.9+
- Ollama (local) or OpenAI API key (for AI features) / Ollama（本地）或OpenAI API密钥（AI功能）
- GitHub Personal Access Token (for higher rate limits) / GitHub个人访问令牌（更高速率限制）

```bash
# Install & run Ollama / 安装并运行Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve

# Set environment variables / 设置环境变量
export GITHUB_TOKEN="your_github_token"
export OLLAMA_HOST="http://localhost:11434"
```

### Project Structure / 项目结构

```
similar_project_rating/
├── src/                      # Main source code / 主源码
│   ├── main.py               # CLI entry point / CLI入口
│   ├── search/                # GitHub search & filter / GitHub搜索与过滤
│   ├── analysis/              # Multi-dimension analyzers / 多维分析器
│   ├── scoring/               # Weighted scoring engine / 加权评分引擎
│   ├── ai/                     # LLM integration / LLM集成
│   ├── pipeline/               # Orchestration / 编排层
│   ├── report/                 # Report generation / 报告生成
│   ├── models/                 # Data models / 数据模型
│   ├── utils/                  # Config, logging, cache / 配置、日志、缓存
│   └── storage/               # Database & file ops / 数据库与文件操作
├── tests/                    # Test suite / 测试套件
├── configs/                  # Configuration files / 配置文件
├── .github/workflows/        # CI/CD pipelines / CI/CD流水线
└── requirements/             # Python dependencies / Python依赖
```

### Development / 开发指南

1. Clone the repository / 克隆仓库
2. Create virtual environment: `python -m venv .venv && source .venv/bin/activate`
3. Install dev deps: `pip install -r requirements/dev.txt`
4. Run tests: `pytest tests/unit -v`
5. Follow conventional commits: `feat: add X`, `fix: resolve Y`
6. Each PR/change should modify ≤5 files (per project rules)

### Environment Check / 环境检查

The system includes a comprehensive environment checker that verifies all dependencies before running analysis.

系统包含全面的环境检查器,在运行分析前验证所有依赖项.

```bash
# Run standalone environment check / 运行独立环境检查
python -m src.utils.environment_checker
python scripts/env_check.py

# Check with custom configuration / 使用自定义配置检查
python -m src.utils.environment_checker --config configs/custom_config.yaml

# Check with strict mode (treat warnings as failures) / 使用严格模式检查(将警告视为失败)
python scripts/env_check.py --strict

# Save detailed report / 保存详细报告
python scripts/env_check.py --report check_report.json
```

**CLI Options for Environment Check / 环境检查的CLI选项:**
- `--env-check-only` - Run checks and exit (don't analyze) / 运行检查并退出(不进行分析)
- `--skip-env-check` - Skip environment checks (debug) / 跳过环境检查(调试)
- `--strict-check` - Treat warnings as failures / 将警告视为失败
- `--check-report-file FILE` - Save check report to JSON file / 保存检查报告到JSON文件

**What's checked / 检查内容:**
1. ✅ Python 3.9+ version / Python 3.9+版本
2. ✅ Required Python packages / 必需的Python包
3. ✅ Internet connectivity / 互联网连接性
4. ✅ GitHub API access and rate limits / GitHub API访问和速率限制
5. ✅ Ollama service (if using Ollama) / Ollama服务(如使用Ollama)
6. ✅ GitReverse.com connectivity (if enabled) / GitReverse.com连接性(如启用)
7. ✅ File permissions for output directories / 输出目录的文件权限

### Configuration / 配置

Edit `configs/config.yaml` to customize:
- GitHub API token and rate limits / GitHub API令牌和速率限制
- AI provider (Ollama/OpenAI/LiteLLM) and model selection / AI提供商和模型选择
- Analysis thresholds and limits / 分析阈值和限制
- Scoring dimension weights / 评分维度权重
- Logging verbosity and format / 日志详细程度和格式
- Environment check settings / 环境检查设置

### License / 许可证

MIT License. See [LICENSE](LICENSE) for details.
