# Pipeline Optimizer Framework

基于 DocETL MOAR 优化器设计的线性 pipeline 优化框架。

## 核心特性

- **三目标优化**：同时优化精度、tokens 使用量、执行时间
- **MCTS 搜索**：使用蒙特卡洛树搜索探索配置空间
- **Pareto 前沿**：返回多个最优权衡方案
- **灵活的算子选择**：为每个操作选择最优算子

## 架构设计

```
planner/
├── core/
│   ├── pipeline.py      # Pipeline 和 Operator 定义
│   ├── node.py          # 搜索树节点
│   ├── executor.py      # Pipeline 执行器
│   └── evaluator.py     # 精度评估接口
├── optimizer/
│   ├── mcts.py          # MCTS 搜索引擎
│   ├── pareto.py        # Pareto 前沿管理
│   └── actions.py       # 优化动作定义
├── examples/
│   └── medical_summary_example.py
└── README.md
```

## 快速开始

### 1. 定义 Pipeline

```python
from planner import Pipeline, Operation, create_llm_operation, create_transform_operation

# 创建 pipeline
pipeline = Pipeline([
    create_transform_operation(
        name="read_files",
        candidates=["read_json", "read_csv"]
    ),
    create_transform_operation(
        name="chunk",
        candidates=["fixed_chunk", "semantic_chunk"]
    ),
    create_llm_operation(
        name="summarize",
        prompt="总结段落，提取关键信息",
        candidates=["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022"]
    ),
    create_llm_operation(
        name="filter",
        prompt="过滤无关段落",
        candidates=["gpt-4o-mini", "rule_based"]
    ),
])
```

### 2. 运行优化

```python
from planner import PipelineOptimizer
from planner.core.executor import MockExecutor

# 创建优化器
optimizer = PipelineOptimizer(
    pipeline=pipeline,
    executor=MockExecutor(),  # 使用模拟执行器
    max_iterations=50,
    save_dir="results/optimization"
)

# 运行优化
pareto_frontier = optimizer.optimize()

# 打印结果
optimizer.print_summary()
```

### 3. 查看结果

优化完成后，会生成以下文件：

- `pareto_frontier.json`: 所有 Pareto 最优解
- `recommendations.json`: 推荐方案（最佳精度、最低成本、最快、平衡）
- `search_stats.json`: 搜索统计信息

## 运行示例

```bash
# 从项目根目录运行
python -m planner.examples.medical_summary_example
```

## 核心概念

### Pipeline 定义

Pipeline 是一个线性的操作序列：

```python
pipeline = Pipeline([
    Operation("op1", op_type="map", candidates=[...]),
    Operation("op2", op_type="filter", candidates=[...]),
    Operation("op3", op_type="map", candidates=[...]),
])
```

### 优化动作

框架支持以下优化动作：

1. **切换算子** (`SwitchOperatorAction`)
   - 为操作选择不同的算子（如更换 LLM 模型）
   - 例如：`gpt-4o-mini` → `gpt-4o`

2. **操作重排** (`ReorderOperationsAction`)
   - 交换相邻操作的顺序
   - 例如：将 filter 移到 map 之前（谓词下推）

### MCTS 搜索流程

1. **Selection**: 使用 UCB 选择最有希望的节点
2. **Expansion**: 应用优化动作生成子节点
3. **Simulation**: 执行 pipeline 并评估指标
4. **Backpropagation**: 回溯更新节点统计信息

### Pareto 前沿

Pareto 前沿包含所有非支配解，每个解在三个目标间取得不同权衡：

- 📈 **精度** (Accuracy): 越高越好
- 💰 **成本** (Tokens/Cost): 越低越好
- ⚡ **速度** (Time): 越快越好

## 自定义执行器

如果要使用真实的 LLM 执行，需要实现自定义执行器：

```python
from planner.core.executor import PipelineExecutor, ExecutionMetrics

class MyExecutor(PipelineExecutor):
    def execute(self, pipeline, input_data):
        # 实现真实的 pipeline 执行逻辑
        result = ...
        
        # 记录指标
        self.last_metrics = ExecutionMetrics(
            accuracy=0.0,  # 需要评估器计算
            tokens=total_tokens,
            execution_time=elapsed_time,
            cost=total_cost
        )
        
        return result
    
    def get_metrics(self):
        return self.last_metrics
```

## 自定义评估器

提供自定义的精度评估函数：

```python
from planner.core.executor import Evaluator

def my_eval_func(ground_truth, predictions):
    # 计算精度
    correct = sum(1 for gt, pred in zip(ground_truth, predictions) if gt == pred)
    return correct / len(ground_truth)

evaluator = Evaluator(my_eval_func)

optimizer = PipelineOptimizer(
    pipeline=pipeline,
    executor=my_executor,
    evaluator=evaluator,
    ground_truth=my_ground_truth
)
```

## 设计原则

1. **借鉴 DocETL MOAR**：继承 MCTS + Pareto + 多目标优化的核心设计
2. **简化依赖关系**：仅支持线性 pipeline，简化搜索空间
3. **三目标平衡**：同时优化精度、成本、延迟
4. **可扩展性**：易于添加新算子和优化动作
5. **模块化**：核心组件解耦，易于测试和扩展

## 与 DocETL MOAR 的对比

| 特性 | Pipeline Optimizer | DocETL MOAR |
|------|-------------------|-------------|
| 支持的结构 | 线性 pipeline | DAG（有向无环图）|
| 优化目标 | 精度 + Tokens + 时间 | 精度 + 成本 |
| 搜索算法 | MCTS | MCTS |
| Pareto 前沿 | ✅ | ✅ |
| 操作类型 | 自定义 | DocETL 预定义 |
| 优化动作 | 算子切换 + 操作重排 | 26 种 Directives |
| Agent 决策 | ❌ | ✅ |

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可

本项目遵循与 DocETL 相同的许可协议。
