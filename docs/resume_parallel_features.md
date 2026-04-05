# 恢复和并行执行功能实现文档

本文档详细介绍了项目中实现的三个核心功能：

1. **默认AI模型配置**：将默认模型设置为本地Ollama的gemma4:26b-a4b-it-q4_K_M
2. **任务恢复机制**：支持从失败或中断的任务继续执行
3. **并行处理机制**：区分AI和非AI任务的并行执行控制

## 1. 默认AI模型配置 (gemma4:26b-a4b-it-q4_K_M)

### 实现文件
- `configs/config.yaml`：更新了默认模型配置
- `src/utils/config.py`：更新了AIConfig类的默认值
- `src/ai/providers/ollama_provider.py`：更新了OllamaProvider的默认模型

### 配置变化
```yaml
# 之前的配置
ai:
  provider: "ollama"
  model: "llama3.2:latest"

# 现在的配置  
ai:
  provider: "ollama"
  model: "gemma4:26b-a4b-it-q4_K_M"
```

### 使用方式
```bash
# 使用默认模型（gemma4:26b-a4b-it-q4_K_M）
python src/main.py --query "web framework"

# 手动指定其他模型
python src/main.py --query "web framework" --model "llama3.2:latest"
```

## 2. 任务恢复机制

### 核心组件
- `src/utils/resume_manager.py`：恢复管理器主模块
- `src/pipeline/orchestrator_resume.py`：支持恢复的流水线协调器

### 主要功能
1. **任务检查点**：每个任务执行时保存状态到JSON文件
2. **依赖关系管理**：确保任务按正确顺序执行
3. **恢复点检测**：自动检测可以从哪里继续执行
4. **结果缓存**：已完成任务的结果会被缓存和重用

### 类结构
```python
# 检查点类
class TaskCheckpoint:
    task_id: str
    task_name: str
    task_type: TaskType  # AI_DEPENDENT 或 NON_AI
    status: TaskStatus   # PENDING, RUNNING, COMPLETED, FAILED
    # ... 其他字段

# 恢复状态类  
class ResumeState:
    session_id: str
    query: str
    tasks: List[TaskCheckpoint]
    # ... 其他字段

# 恢复管理器
class ResumeManager:
    def initialize_new_session()
    def load_resume_state()
    def can_resume()
    def get_resume_point()
    def execute_pipeline()
```

### 使用方式
```bash
# 启动新会话
python src/main.py --query "web framework" --session-id "my-session-001"

# 如果会话中断，可以恢复执行
python src/main.py --query "web framework" --session-id "my-session-001" --resume

# 强制重新开始（忽略检查点）
python src/main.py --query "web framework" --session-id "my-session-001" --no-resume
```

### 检查点存储位置
检查点文件保存在：`./data/checkpoints/{session_id}.json`

## 3. 并行处理机制

### 核心组件
- `src/utils/config.py`：新增ParallelConfig配置类
- `src/analysis/pipeline_parallel.py`：增强的分析流水线
- `src/pipeline/orchestrator_resume.py`：集成了并行控制的协调器

### 默认配置
```yaml
parallel:
  # AI依赖任务（默认：串行执行）
  ai_concurrent_limit: 1      # AI依赖任务的最大并发数
  enable_parallel_ai: false   # 默认禁用AI并行
  
  # 非AI任务（默认：5个并行任务）
  non_ai_concurrent_limit: 5  # 非AI任务的最大并发数
  enable_parallel_non_ai: true # 默认启用非AI并行
  
  # 超时和自适应设置
  ai_semaphore_timeout: 300   # 等待AI资源的秒数
  adaptive_scaling: false     # 默认禁用自适应缩放
  
  # 总体限制
  min_concurrent_tasks: 1    # 最小并发任务数
  max_concurrent_tasks: 10   # 最大并发任务数
```

### 任务分类
| 任务类型 | 任务名称 | 默认并发数 | 说明 |
|---------|---------|-----------|------|
| AI_DEPENDENT | Keyword Generation | 1 | AI关键词生成 |
| AI_DEPENDENT | Project Filtering | 1 | AI项目过滤 |
| AI_DEPENDENT | AI Recommendation | 1 | AI推荐生成 |
| AI_DEPENDENT | AI Explanation | 1 | AI解释生成 |
| NON_AI | GitHub Search | 5 | GitHub API搜索 |
| NON_AI | Code Analysis | 5 | 代码分析 |
| NON_AI | Community Analysis | 5 | 社区分析 |
| NON_AI | Maturity Analysis | 5 | 成熟度分析 |
| NON_AI | Score Calculation | 5 | 分数计算 |
| NON_AI | Ranking | 5 | 项目排名 |
| NON_AI | Report Generation | 5 | 报告生成 |

### 使用方式
```bash
# 使用默认并行设置（AI:1个，非AI:5个）
python src/main.py --query "web framework"

# 禁用AI并行（强制串行）
python src/main.py --query "web framework" --disable-parallel-ai

# 自定义并发设置
python src/main.py --query "web framework" \
  --max-concurrent-ai 2 \
  --max-concurrent-non-ai 10

# 完全禁用并行
python src/main.py --query "web framework" \
  --max-concurrent-ai 1 \
  --max-concurrent-non-ai 1 \
  --disable-parallel-ai
```

### 技术实现
```python
# 使用信号量控制并发
self.ai_semaphore = asyncio.Semaphore(ai_concurrent_limit)
self.non_ai_semaphore = asyncio.Semaphore(non_ai_concurrent_limit)

# AI任务执行示例
async with self.ai_semaphore:
    result = await ai_task_function()

# 非AI任务执行示例  
async with self.non_ai_semaphore:
    result = await non_ai_task_function()
```

## 命令行参数汇总

### 恢复相关参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--resume` | `false` | 启用会话恢复 |
| `--no-resume` | `false` | 禁用会话恢复 |
| `--session-id` | `自动生成` | 会话标识符 |

### 并行相关参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-concurrent-ai` | `1` | AI依赖任务的最大并发数 |
| `--max-concurrent-non-ai` | `5` | 非AI任务的最大并发数 |
| `--disable-parallel-ai` | `false` | 禁用AI任务并行 |

### AI模型相关参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-m, --model` | `gemma4:26b-a4b-it-q4_K_M` | AI模型名称 |
| `-p, --provider` | `ollama` | AI提供商 |

## 完整使用示例

```bash
# 示例1：完整的恢复和并行控制
python src/main.py \
  --query "Python web framework" \
  --session-id "web-framework-analysis" \
  --resume \
  --max-concurrent-ai 1 \
  --max-concurrent-non-ai 8 \
  --auto-commit

# 示例2：性能优化（允许更多并行）
python src/main.py \
  --query "machine learning library" \
  --max-concurrent-non-ai 12 \
  --max-projects 30

# 示例3：保守执行（最小化资源使用）
python src/main.py \
  --query "small utility" \
  --max-concurrent-ai 1 \
  --max-concurrent-non-ai 2 \
  --max-projects 10
```

## 测试脚本

运行测试脚本验证功能：
```bash
python test_resume_parallel.py
```

测试脚本将验证：
1. 默认AI模型是否正确配置
2. 恢复机制是否能正常工作
3. 并行配置是否正确设置
4. 所有功能是否已正确集成

## 故障排除

### 常见问题
1. **恢复失败**：检查`./data/checkpoints/`目录是否存在正确的检查点文件
2. **并行设置无效**：确保配置文件`configs/config.yaml`中的parallel部分正确
3. **AI模型不可用**：确认Ollama已安装且gemma4:26b-a4b-it-q4_K_M模型已下载

### 日志查看
```bash
# 查看恢复相关日志
grep -r "resume\|checkpoint\|ResumeManager" ./logs/

# 查看并行执行日志  
grep -r "concurrent\|semaphore\|parallel" ./logs/

# 查看AI调用日志
grep -r "gemma\|model\|Ollama" ./logs/
```

## 性能建议

1. **AI任务**：保持低并发（1-2），避免LLM API过载
2. **非AI任务**：可提高并发（5-10），特别是IO密集型任务
3. **内存考虑**：高并发时注意内存使用，可调整`--max-projects`限制
4. **网络考虑**：API密集型任务（GitHub搜索）建议中等并发（3-5）

## 总结

本项目已成功实现以下三个核心功能：

1. ✅ **默认AI模型**：使用本地Ollama的gemma4:26b-a4b-it-q4_K_M模型
2. ✅ **任务恢复**：支持从检查点恢复执行，提高可靠性
3. ✅ **并行控制**：区分AI/非AI任务的并发限制，优化资源使用

这些功能共同提供了更稳定、高效和灵活的项目分析体验。