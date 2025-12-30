# 真实 Pipeline 执行指南

本指南说明如何使用真实的算子和 vLLM 服务运行 Pipeline 优化。

## 目录结构

```
planner/
├── data/
│   └── medical_documents.json          # 测试数据（10条医疗文档）
├── operators/
│   ├── programmatic.py                 # 预编程算子
│   └── llm_operators.py                # LLM 算子
├── core/
│   └── real_executor.py                # 真实执行器
├── examples/
│   └── real_medical_example.py         # 完整示例
└── REAL_EXECUTION_GUIDE.md             # 本文档
```

## 准备工作

### 1. 启动 vLLM 服务

确保你已经安装了 vLLM 并下载了模型，然后启动服务：

```bash
python -m vllm.entrypoints.openai.api_server \
    --model /path/to/your/model \
    --host 0.0.0.0 \
    --port 8000
```

例如，如果使用 Qwen 模型：
```bash
python -m vllm.entrypoints.openai.api_server \
    --model /home/richardlin/projects/llm/vllm_test/model/Qwen3-0.6B \
    --host 0.0.0.0 \
    --port 8000
```

### 2. 验证服务

检查 vLLM 服务是否正常：
```bash
curl http://localhost:8000/health
```

应该返回状态码 200。

### 3. 测试数据

数据文件已经生成在 `planner/data/medical_documents.json`，包含 10 条医疗文档：
- 8 条真实的医疗记录（包含患者、诊断、药物等）
- 2 条非医疗文档（用于测试过滤）

## 运行示例

### 测试模式（推荐先运行）

测试单个 pipeline 执行，验证所有组件是否正常工作：

```bash
cd e:\projects\sourcecode\docetl-main\docetl-main
python -m planner.examples.real_medical_example --mode test
```

这会：
1. 读取医疗文档
2. 使用关键词过滤医疗相关文档
3. 使用 LLM 提取药物信息
4. 显示执行结果和指标

### 优化模式

运行完整的 MCTS 优化过程：

```bash
python -m planner.examples.real_medical_example --mode optimize
```

这会：
1. 从初始 pipeline 开始
2. 探索不同的算子组合（规则过滤 vs LLM 过滤）
3. 评估每个配置的精度、成本、时间
4. 生成 Pareto 前沿
5. 保存优化结果到 `planner/results/real_optimization/`

## 算子说明

### 预编程算子（programmatic.py）

不使用 LLM，基于规则或代码逻辑：

1. **ReadJsonOperator**: 读取 JSON 文件
   - 候选名称: `read_json`
   
2. **KeywordFilterOperator**: 关键词过滤
   - 候选名称: `keyword_filter`
   - 参数: `keywords` (关键词列表)
   - 示例: 过滤包含 "患者"、"药物" 的文档

3. **CountTokensOperator**: 统计 token 数量
   - 候选名称: `count_tokens`
   
4. **RegexExtractOperator**: 正则表达式提取
   - 候选名称: `regex_extract`

### LLM 算子（llm_operators.py）

使用 vLLM 服务进行推理：

1. **LLMSummarizeOperator**: 文档摘要
   - 候选名称: `llm_summarize`
   - 参数: `max_tokens`, `temperature`
   
2. **LLMFilterOperator**: 智能过滤
   - 候选名称: `llm_filter`
   - 参数: `filter_criteria` (过滤标准)
   - 示例: "是否为医疗相关文档"

3. **LLMExtractOperator**: 信息提取
   - 候选名称: `llm_extract`
   - 参数: `target` (提取目标)
   - 示例: 提取 "药物名称及用法"

## Pipeline 定义示例

```python
from planner.core.pipeline import Pipeline, Operation

pipeline = Pipeline([
    # 操作 1: 读取数据
    Operation(
        name="read_data",
        op_type="transform",
        candidates=["read_json"],
        selected_operator="read_json"
    ),
    
    # 操作 2: 过滤文档（多个候选算子）
    Operation(
        name="filter_medical",
        op_type="filter",
        prompt="是否为医疗相关文档",
        candidates=["keyword_filter", "llm_filter"],  # 规则 vs LLM
        selected_operator="keyword_filter",  # 默认使用规则
        params={"keywords": ["患者", "药", "诊断"]}
    ),
    
    # 操作 3: 提取药物信息
    Operation(
        name="extract_medications",
        op_type="map",
        candidates=["llm_extract"],
        selected_operator="llm_extract",
        params={"target": "药物名称及用法"}
    ),
])
```

## 优化过程

优化器会探索以下变体：

1. **算子切换**:
   - `keyword_filter` → `llm_filter`
   - 权衡：规则快但可能不准确 vs LLM 慢但更智能

2. **操作重排**:
   - 将 filter 移到前面（谓词下推）
   - 减少需要处理的数据量

## 输出结果

### 执行日志示例

```
======================================================================
开始执行 Pipeline: medical_document_pipeline
======================================================================

[1/3] 执行操作: read_data (read_json)
   ✓ 完成，耗时 0.01s，输出 10 条

[2/3] 执行操作: filter_medical (keyword_filter)
   ✓ 完成，耗时 0.00s，输出 8 条

[3/3] 执行操作: extract_medications (llm_extract)
   ✓ 完成，耗时 12.50s，使用 3200 tokens，输出 8 条

======================================================================
Pipeline 执行完成
   总耗时: 12.51s
   总 tokens: 3200
   总成本: $0.003200
   最终输出: 8 条数据
======================================================================
```

### 保存的文件

优化完成后，在 `planner/results/real_optimization/` 目录下：

1. **pareto_frontier.json**: 所有 Pareto 最优解
2. **recommendations.json**: 推荐方案
   - `best_accuracy`: 精度最高
   - `lowest_cost`: 成本最低
   - `fastest`: 执行最快
   - `balanced`: 综合最优
3. **search_stats.json**: 搜索统计信息

## 性能调优

### 加快测试速度

1. 减少数据量：
   ```python
   # 在 real_executor.py 中修改
   data = data[:5]  # 只处理前5条
   ```

2. 减少迭代次数：
   ```python
   optimizer = PipelineOptimizer(
       max_iterations=5,  # 从 50 减到 5
       ...
   )
   ```

3. 减少子节点数：
   ```python
   max_children_per_node=1  # 从 5 减到 1
   ```

### 优化 vLLM 性能

```bash
# 使用更多 GPU
--tensor-parallel-size 2

# 增加批处理大小
--max-num-seqs 256

# 启用 Flash Attention
--enable-flash-attn
```

## 常见问题

### Q: vLLM 连接失败

**A**: 检查：
1. vLLM 服务是否启动：`curl http://localhost:8000/health`
2. 端口是否正确（默认 8000）
3. 防火墙是否阻止连接

### Q: 生成的文本格式不对

**A**: 调整提示词：
```python
# 在 llm_operators.py 中修改 prompt
prompt = f"""严格按照以下格式输出...

示例输出：
- 阿司匹林 100mg 每日一次
- 氨氯地平 5mg 每日一次

实际提取：
"""
```

### Q: Token 统计不准确

**A**: vLLM 的 `usage` 字段可能为空，可以：
```python
# 使用 tiktoken 手动计算
import tiktoken
encoding = tiktoken.get_encoding("cl100k_base")
tokens = len(encoding.encode(text))
```

### Q: 想要使用 Mock 执行器测试

**A**: 修改示例代码：
```python
from planner.core.executor import MockExecutor

# 替换 RealExecutor
executor = MockExecutor()
```

## 扩展方向

1. **添加新算子**:
   - 在 `operators/` 目录创建新文件
   - 在 `real_executor.py` 注册算子

2. **自定义评估函数**:
   - 根据任务定义准确性
   - 可以加载 ground truth 进行对比

3. **集成其他 LLM**:
   - 修改 `VLLMClient` 支持其他 API
   - 例如 OpenAI、Anthropic

4. **添加缓存**:
   - 缓存 LLM 调用结果
   - 避免重复计算

## 下一步

1. ✅ 运行测试模式验证功能
2. ✅ 运行优化模式探索最优配置
3. ⭐ 根据实际需求调整算子和 pipeline
4. ⭐ 扩展更多优化动作和策略
