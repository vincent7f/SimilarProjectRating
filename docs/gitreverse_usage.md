# GitReverse.com Integration Guide

## 概述 / Overview

本系统现在集成了 [GitReverse.com](https://gitreverse.com) 功能，该服务可以将GitHub仓库转换为文本化的项目描述（prompt）。这允许系统在不下载和解析实际代码的情况下评估项目质量，从而大幅提高分析速度。

The system now integrates with [GitReverse.com](https://gitreverse.com), a service that converts GitHub repositories into textual project descriptions (prompts). This allows the system to assess project quality without downloading and parsing actual code, significantly increasing analysis speed.

## 工作原理 / How It Works

1. **URL转换** / URL Transformation
   ```
   GitHub URL: https://github.com/nearai/ironclaw
   GitReverse URL: https://gitreverse.com/nearai/ironclaw
   ```

2. **获取项目描述** / Fetching Project Description
   - 系统请求GitReverse.com获取项目的文本化描述
   - The system requests GitReverse.com for the textual description of the project
   - 描述包含了项目的功能、架构、文档等信息
   - The description includes information about the project's functionality, architecture, documentation, etc.

3. **AI分析** / AI Analysis
   - 使用本地AI模型（如Gemma）分析项目描述
   - Uses local AI models (e.g., Gemma) to analyze the project description
   - 从描述中提取代码质量指标
   - Extracts code quality metrics from the description

4. **自动回退** / Automatic Fallback
   - 如果GitReverse不可用或返回空结果，系统可以回退到传统代码分析
   - If GitReverse is unavailable or returns empty results, the system can fall back to traditional code analysis

## 配置文件设置 / Configuration File Settings

在 `configs/config.yaml` 中添加以下配置节：

Add the following configuration section to `configs/config.yaml`:

```yaml
# ---------------------------------------------------------------------------
# GitReverse Settings / GitReverse设置
# ---------------------------------------------------------------------------
gitreverse:
  base_url: "https://gitreverse.com"
  timeout_seconds: 30
  enabled: true               # 使用GitReverse而不是代码分析 / Use GitReverse instead of code analysis
  fallback_to_code: true     # GitReverse失败时回退到传统代码分析 / Fallback to traditional code analysis if GitReverse fails
  max_retries: 3
  cache_duration_seconds: 3600  # 缓存GitReverse prompts / Cache GitReverse prompts
```

## 命令行参数 / Command Line Arguments

### 启用GitReverse / Enable GitReverse
```bash
# 强制使用GitReverse（覆盖配置文件设置）
python src/main.py "web framework" --use-gitreverse

# 强制使用GitReverse且禁用回退
python src/main.py "web framework" --use-gitreverse --no-gitreverse-fallback
```

### 禁用GitReverse / Disable GitReverse
```bash
# 强制禁用GitReverse（使用传统代码分析）
python src/main.py "web framework" --disable-gitreverse

# 使用配置文件中的设置（如果已配置）
python src/main.py "web framework"
```

### 与其他功能结合使用 / Combined with Other Features
```bash
# 启用GitReverse + 恢复功能 + 并行处理
python src/main.py "web framework" \
  --use-gitreverse \
  --resume \
  --session-id "my-session" \
  --max-concurrent-non-ai 10 \
  --max-concurrent-ai 2

# 启用GitReverse + 自定义AI模型
python src/main.py "machine learning library" \
  --use-gitreverse \
  --provider ollama \
  --model "gemma4:26b-a4b-it-q4_K_M"
```

## 使用场景 / Use Cases

### 场景1：快速分析热门项目 / Scenario 1: Quick Analysis of Popular Projects
GitReverse特别适合分析热门项目（star数量多），因为这些项目通常有详细的项目描述。

GitReverse is particularly suitable for analyzing popular projects (high star count) because these projects typically have detailed descriptions.

### 场景2：批量分析 / Scenario 2: Batch Analysis
当需要分析大量项目时，GitReverse可以：
1. 避免大量代码下载
2. 减少存储空间使用
3. 显著提高分析速度

When analyzing a large number of projects, GitReverse can:
1. Avoid large code downloads
2. Reduce storage space usage
3. Significantly increase analysis speed

### 场景3：网络受限环境 / Scenario 3: Network-Restricted Environments
在下载代码受限的环境中，GitReverse提供了一种轻量级的替代方案。

In environments where code downloads are restricted, GitReverse provides a lightweight alternative.

## 技术实现 / Technical Implementation

### 自适应流水线 / Adaptive Pipeline
系统使用自适应流水线，可以根据以下因素选择分析方法：
- 仓库流行度（stars数量）
- 项目描述质量
- GitReverse可用性
- 配置设置

The system uses an adaptive pipeline that can select the analysis method based on:
- Repository popularity (number of stars)
- Project description quality
- GitReverse availability
- Configuration settings

### 混合分析模式 / Hybrid Analysis Mode
系统可以在单次分析会话中使用多种分析方法：
- 热门项目 → GitReverse分析
- 小众项目 → 传统代码分析
- 网络问题 → 自动回退

The system can use multiple analysis methods in a single analysis session:
- Popular projects → GitReverse analysis
- Niche projects → Traditional code analysis
- Network issues → Automatic fallback

### 统计指标 / Statistics
系统跟踪以下统计信息：
- 使用GitReverse分析的项目数量
- 使用传统代码分析的项目数量
- 回退发生次数
- 平均分析时间

The system tracks the following statistics:
- Number of projects analyzed using GitReverse
- Number of projects analyzed using traditional code analysis
- Number of fallbacks occurred
- Average analysis time

## 性能对比 / Performance Comparison

| 方法 / Method | 平均时间 / Average Time | 数据下载 / Data Download | 准确性 / Accuracy |
|--------------|-----------------------|-------------------------|-----------------|
| **GitReverse** | 2-5秒 | 无 / None | 中等-高 / Medium-High |
| **传统代码分析** | 30-60秒 | 完整代码库 / Full Codebase | 高 / High |
| **混合模式** | 10-30秒 | 根据需求 / On Demand | 高 / High |

## 故障排除 / Troubleshooting

### GitReverse不可用 / GitReverse Unavailable
```
[INFO] GitReverse analysis: DISABLED (fallback: ENABLED)
[WARNING] Failed to fetch GitReverse prompt for nearai/ironclaw
[INFO] Falling back to traditional code analysis
```

**解决方案 / Solution:**
1. 检查网络连接 / Check network connectivity
2. 验证GitReverse.com是否可访问 / Verify gitreverse.com is accessible
3. 使用传统分析 / Use traditional analysis: `--disable-gitreverse`
4. 增加超时时间 / Increase timeout in config: `timeout_seconds: 60`

### AI分析失败 / AI Analysis Failed
```
[ERROR] AI analysis failed: Connection timeout
```

**解决方案 / Solution:**
1. 检查本地AI服务（Ollama）是否运行 / Check if local AI service (Ollama) is running
2. 调整AI配置 / Adjust AI configuration in `config.yaml`
3. 使用更轻量的模型 / Use a lighter model

### 恢复功能与GitReverse冲突 / Resume Conflicts with GitReverse
恢复检查点可能与GitReverse分析不兼容，因为：
- GitReverse分析可能产生不同的结果
- 无法保证两次分析的一致性

Resume checkpoints may be incompatible with GitReverse analysis because:
- GitReverse analysis may produce different results
- Consistency between two analyses cannot be guaranteed

**解决方案 / Solution:**
对于需要精确恢复的场景，建议禁用GitReverse：

For scenarios requiring precise resume, it's recommended to disable GitReverse:
```bash
python src/main.py "web framework" --resume --disable-gitreverse
```

## 测试功能 / Testing Features

运行集成测试：

Run integration tests:
```bash
python test_gitreverse_integration.py
```

运行完整系统测试：

Run full system test:
```bash
python src/main.py "web framework" --use-gitreverse --max-projects 3 --dry-run
```

## 最佳实践 / Best Practices

1. **评估需求** / Assess Requirements
   - 如果需要快速概览 → 使用GitReverse
   - 如果需要详细分析 → 使用传统分析
   - If you need a quick overview → Use GitReverse
   - If you need detailed analysis → Use traditional analysis

2. **分层分析** / Tiered Analysis
   ```yaml
   gitreverse:
     enabled: true
     fallback_to_code: true  # 失败时回退 / Fallback on failure
   ```

3. **性能监控** / Performance Monitoring
   - 查看日志中的`prompt_analyses`, `code_analyses`, `fallbacks`统计
   - 调整并发设置以优化性能
   - Check `prompt_analyses`, `code_analyses`, `fallbacks` statistics in logs
   - Adjust concurrency settings to optimize performance

4. **缓存策略** / Caching Strategy
   GitReverse响应默认缓存1小时，可以在配置中调整：
   ```yaml
   cache_duration_seconds: 86400  # 24小时缓存 / 24-hour cache
   ```

## 限制 / Limitations

1. **描述质量依赖** / Description Quality Dependency
   - GitReverse分析完全依赖项目描述的完整性
   - 如果描述不完整或不准确，分析结果可能不准确
   - GitReverse analysis completely relies on the completeness of the project description
   - If the description is incomplete or inaccurate, the analysis results may be inaccurate

2. **无法检测的细节** / Undetectable Details
   - 代码复杂性
   - 安全漏洞
   - 具体的依赖版本
   - 精确的测试覆盖率
   - Code complexity
   - Security vulnerabilities
   - Specific dependency versions
   - Exact test coverage

3. **API限制** / API Limitations
   - GitReverse.com可能有访问频率限制
   - 某些私有或新项目可能没有描述
   - GitReverse.com may have rate limits
   - Some private or new projects may not have descriptions

## 更新日志 / Changelog

### v1.0.0 (初始集成 / Initial Integration)
- 添加GitReverse客户端
- 实现基于prompt的代码分析器
- 创建自适应分析流水线
- 添加命令行参数支持
- Added GitReverse client
- Implemented prompt-based code analyzer
- Created adaptive analysis pipeline
- Added command line argument support

## 贡献 / Contributing

欢迎改进GitReverse集成功能：

Improvements to the GitReverse integration are welcome:

1. 改进HTML解析逻辑 / Improve HTML parsing logic
2. 添加更多启发式规则 / Add more heuristic rules
3. 实现更好的错误处理 / Implement better error handling
4. 添加性能优化 / Add performance optimizations

请提交PR或Issue到项目仓库。

Please submit PRs or issues to the project repository.