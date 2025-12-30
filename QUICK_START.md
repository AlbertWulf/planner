# Pipeline Optimizer - 快速开始指南

## 🚀 5分钟快速开始

### 步骤 1: 验证环境

```bash
cd e:\projects\sourcecode\docetl-main\docetl-main
python planner\verify_setup.py
```

如果看到 "🎉 所有验证通过！"，说明环境配置正确。

### 步骤 2: 启动 vLLM 服务

在另一个终端窗口中：

```bash
python -m vllm.entrypoints.openai.api_server \
    --model /home/richardlin/projects/llm/vllm_test/model/Qwen3-0.6B \
    --host 0.0.0.0 \
    --port 8000
```

等待看到 "Application startup complete" 消息。

### 步骤 3: 运行测试示例

```bash
# 方式 1: 使用 Python 直接运行
python -m planner.examples.real_medical_example --mode test

# 方式 2: 使用快捷脚本（Windows）
planner\run_example.bat
# 然后选择 1 (测试模式)
```

### 步骤 4: 运行完整优化

```bash
python -m planner.examples.real_medical_example --mode optimize
```

查看优化结果：
```
planner/results/real_optimization/
├── pareto_frontier.json      # 所有 Pareto 最优解
├── recommendations.json      # 推荐方案
└── search_stats.json         # 搜索统计
```

## 📁 项目结构

```
planner/
├── data/
│   └── medical_documents.json          # 测试数据（10条医疗文档）
│
├── operators/                          # 算子实现
│   ├── programmatic.py                 # 预编程算子（5个）
│   └── llm_operators.py                # LLM 算子（3个 + 客户端）
│
├── core/                               # 核心组件
│   ├── pipeline.py                     # Pipeline 定义
│   ├── node.py                         # 搜索树节点
│   ├── executor.py                     # 执行器接口
│   └── real_executor.py                # 真实执行器
│
├── optimizer/                          # 优化器
│   ├── mcts.py                         # MCTS 搜索引擎
│   ├── pareto.py                       # Pareto 前沿管理
│   ├── actions.py                      # 优化动作
│   └── optimizer.py                    # 主优化器
│
├── examples/                           # 示例
│   ├── medical_summary_example.py      # Mock 示例
│   └── real_medical_example.py         # 真实示例
│
├── verify_setup.py                     # 环境验证脚本
├── run_example.bat                     # 快捷运行脚本
│
└── 文档/
    ├── README.md                       # 主文档
    ├── REAL_EXECUTION_GUIDE.md         # 真实执行指南
    ├── REAL_IMPLEMENTATION_SUMMARY.md  # 实现总结
    └── QUICK_START.md                  # 本文档
```

## 🔧 自定义你的 Pipeline

### 1. 修改数据

编辑 `planner/data/medical_documents.json`，或创建新的数据文件。

### 2. 定义 Pipeline

```python
from planner.core.pipeline import Pipeline, Operation

my_pipeline = Pipeline([
    Operation(
        name="load_data",
        op_type="transform",
        candidates=["read_json"],
        selected_operator="read_json"
    ),
    Operation(
        name="filter_step",
        op_type="filter",
        candidates=["keyword_filter", "llm_filter"],  # 多个候选
        params={"keywords": ["关键词1", "关键词2"]}
    ),
    Operation(
        name="extract_step",
        op_type="map",
        candidates=["llm_extract"],
        params={"target": "提取目标"}
    ),
])
```

### 3. 运行优化

```python
from planner.core.real_executor import RealExecutor
from planner.optimizer.optimizer import PipelineOptimizer

executor = RealExecutor(
    vllm_base_url="http://localhost:8000",
    data_path="your_data.json"
)

optimizer = PipelineOptimizer(
    pipeline=my_pipeline,
    executor=executor,
    max_iterations=20
)

pareto_frontier = optimizer.optimize()
optimizer.print_summary()
```

## 📊 查看结果

### Pareto 前沿可视化（概念）

```
精度
 ^
 |     B (最佳精度)
 |    /
 |   /
 |  /  C (平衡)
 | /
 |/
 A (最低成本) -----> 成本
```

### 推荐方案

```json
{
  "best_accuracy": {
    "pipeline": "read_json -> llm_filter -> llm_extract",
    "accuracy": 0.95,
    "tokens": 4800,
    "cost": 0.0048
  },
  "lowest_cost": {
    "pipeline": "read_json -> keyword_filter -> llm_extract",
    "accuracy": 0.85,
    "tokens": 2500,
    "cost": 0.0025
  },
  "balanced": {
    "pipeline": "...",
    "accuracy": 0.90,
    "tokens": 3200,
    "cost": 0.0032
  }
}
```

## 🛠️ 常见任务

### 添加新算子

1. 在 `planner/operators/` 创建算子类
2. 在 `real_executor.py` 注册算子
3. 在 Pipeline 中使用

示例：
```python
# 1. 创建算子
class MyCustomOperator:
    def execute(self, input_data):
        # 你的逻辑
        return processed_data

# 2. 注册（在 RealExecutor._build_operator_registry）
"my_operator": MyCustomOperator

# 3. 使用
Operation(
    name="custom_step",
    candidates=["my_operator"]
)
```

### 调整优化参数

```python
optimizer = PipelineOptimizer(
    max_iterations=50,          # 搜索迭代次数 ↑ = 更好结果，更长时间
    exploration_weight=1.414,   # UCB 探索权重 ↑ = 更多探索
    max_children_per_node=5,    # 每次扩展的子节点数 ↑ = 更全面搜索
)
```

### 自定义评估函数

```python
def my_evaluation_func(ground_truth, predictions):
    # 计算你的精度指标
    correct = 0
    for pred, gt in zip(predictions, ground_truth):
        if compare(pred, gt):
            correct += 1
    return correct / len(predictions)

evaluator = Evaluator(my_evaluation_func)
optimizer = PipelineOptimizer(..., evaluator=evaluator)
```

## ❓ 常见问题

### Q: vLLM 连接失败
**A**: 
1. 检查服务是否启动：`curl http://localhost:8000/health`
2. 检查端口是否正确
3. 检查防火墙设置

### Q: 优化太慢
**A**: 
1. 减少 `max_iterations`
2. 使用更小的数据集
3. 减少 `max_children_per_node`

### Q: 没有 vLLM 服务
**A**: 使用 MockExecutor 进行测试：
```python
from planner.core.executor import MockExecutor
executor = MockExecutor()
```

### Q: 想要保存中间结果
**A**: 设置 `save_dir`：
```python
optimizer = PipelineOptimizer(
    ...,
    save_dir="planner/results/my_experiment"
)
```

## 📚 进一步学习

- 详细使用指南：[REAL_EXECUTION_GUIDE.md](REAL_EXECUTION_GUIDE.md)
- 实现细节：[REAL_IMPLEMENTATION_SUMMARY.md](REAL_IMPLEMENTATION_SUMMARY.md)
- 完整文档：[README.md](README.md)

## 🎯 下一步

1. ✅ 运行验证脚本
2. ✅ 启动 vLLM 服务
3. ✅ 运行测试示例
4. ✅ 运行完整优化
5. ⭐ 自定义你的 Pipeline
6. ⭐ 添加新算子
7. ⭐ 应用到真实项目

祝你使用愉快！🚀
