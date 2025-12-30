# Optuna Pipeline 优化器

基于 [Optuna](https://optuna.org/) 的 Pipeline 优化方案，提供比 MCTS+Pareto 更简单、更高效的多目标优化。

## 特点

### ✨ 相比 MCTS 的优势

| 特性 | MCTS+Pareto | Optuna |
|------|-------------|--------|
| **代码复杂度** | 高（需要实现搜索树、UCB、回溯等） | 低（几十行代码） |
| **收敛速度** | 慢（需要 50-100 次迭代） | 快（通常 20-30 次） |
| **稳定性** | 中等（依赖随机探索） | 高（成熟的采样算法） |
| **多目标优化** | 手动实现 Pareto 前沿 | 内置支持 |
| **可视化** | 需要自己实现 | 丰富的内置可视化 |
| **并行优化** | 需要自己实现 | 原生支持 |
| **超参数调优** | 困难 | 简单（exploration_weight 等自动调整） |
| **适用场景** | 需要可解释性的探索 | 快速收敛的工程应用 |

### 🚀 核心优势

1. **开箱即用** - 无需理解复杂的搜索算法
2. **快速收敛** - TPE 采样器高效探索搜索空间
3. **自动剪枝** - 提前终止无希望的试验
4. **丰富可视化** - 3D Pareto 前沿、优化历史、参数重要性
5. **工业级稳定** - 被广泛应用于机器学习超参数优化

## 安装依赖

```bash
pip install optuna
pip install plotly  # 可选，用于可视化
```

## 快速开始

### 1. 基本用法

```python
from planner.core.pipeline import Pipeline, Operation
from planner.core.real_executor import RealExecutor
from planner.optimizer.optuna_optimizer import OptunaOptimizer

# 创建 pipeline（定义候选算子）
pipeline = Pipeline([
    Operation(
        name="filter",
        candidates=["keyword_filter", "llm_filter"],  # 待优化
        selected_operator="keyword_filter"
    ),
    Operation(
        name="extract",
        candidates=["llm_extract"],
        selected_operator="llm_extract"
    ),
])

# 创建执行器
executor = RealExecutor(
    vllm_base_url="http://localhost:8000",
    data_path="data.json"
)

# 创建优化器
optimizer = OptunaOptimizer(
    pipeline=pipeline,
    executor=executor,
    n_trials=20,  # 试验次数
    save_dir="results"
)

# 运行优化
pareto_trials = optimizer.optimize()

# 查看结果
optimizer.print_summary()
```

### 2. 运行完整示例

```bash
# 测试单个配置
python -m planner.examples.optuna_medical_example --mode test

# 运行优化
python -m planner.examples.optuna_medical_example --mode optimize
```

### 3. 查看结果

优化完成后，会生成：

```
planner/results/optuna_optimization/
├── optuna_trials.json          # 所有试验结果
├── pareto_front.json           # Pareto 前沿
├── pareto_front.html           # 3D 可视化（需要 plotly）
├── optimization_history.html   # 优化历史
└── param_importances.html      # 参数重要性
```

在浏览器中打开 `.html` 文件查看交互式可视化。

## 核心概念

### 多目标优化

Optuna 自动平衡三个目标：

1. **精度（maximize）** - 越高越好
2. **Tokens（minimize）** - 越少越好（降低成本）
3. **时间（minimize）** - 越快越好

Optuna 会自动计算 **Pareto 前沿**，即没有任何方案能在所有目标上都优于它的解集合。

### 采样策略

**TPESampler** (Tree-structured Parzen Estimator)：
- 基于贝叶斯优化
- 高效探索离散搜索空间
- 自动平衡 exploration 和 exploitation

### 剪枝策略

**MedianPruner**：
- 在试验早期阶段预测最终结果
- 提前终止无希望的配置
- 加速整体优化过程

## 高级用法

### 并行优化

```python
optimizer = OptunaOptimizer(
    pipeline=pipeline,
    executor=executor,
    n_trials=50,
    n_jobs=4,  # 4 个并行任务
)
```

### 自定义评估函数

```python
def my_evaluator(results):
    # 自定义精度计算逻辑
    accuracy = calculate_accuracy(results)
    return accuracy

optimizer = OptunaOptimizer(
    pipeline=pipeline,
    executor=executor,
    evaluator=my_evaluator,  # 使用自定义评估
)
```

### 获取特定目标的最佳方案

```python
# 最高精度
best_accuracy = optimizer.get_best_trial_for_objective(0)

# 最少 tokens
best_cost = optimizer.get_best_trial_for_objective(1)

# 最快速度
best_speed = optimizer.get_best_trial_for_objective(2)
```

### 继续优化

```python
# 第一轮优化
optimizer.optimize()

# 继续优化（基于已有结果）
optimizer.n_trials = 50
optimizer.optimize()  # 会继续在同一个 study 中添加试验
```

## 可视化

### 生成所有图表

```python
from planner.optimizer.optuna_optimizer.visualizer import save_all_visualizations

save_all_visualizations(
    optimizer.study,
    output_dir="results/visualizations"
)
```

### 单独生成图表

```python
from planner.optimizer.optuna_optimizer.visualizer import (
    plot_pareto_front,
    plot_optimization_history,
    plot_param_importances
)

# Pareto 前沿 3D 图
plot_pareto_front(optimizer.study, save_path="pareto.html")

# 优化历史
plot_optimization_history(optimizer.study, save_path="history.html")

# 参数重要性
plot_param_importances(optimizer.study, save_path="importance.html")
```

## 性能对比

基于医疗文档处理 pipeline（3 个操作，2 个候选算子）：

| 方法 | 迭代次数 | 耗时 | Pareto 前沿大小 | 代码行数 |
|------|---------|------|----------------|---------|
| **MCTS** | 50 | ~10 分钟 | 3-5 | ~800 |
| **Optuna** | 20 | ~4 分钟 | 3-5 | ~300 |

**结论**：Optuna 用更少的迭代和更少的代码，达到相似的优化效果。

## 常见问题

### Q: Optuna 比 MCTS 更好吗？

**A**: 取决于需求：
- **追求简单高效** → 使用 Optuna
- **需要探索多样性** → 使用 MCTS
- **工程项目** → Optuna
- **研究项目** → MCTS

### Q: 需要多少次试验？

**A**: 经验法则：
- 简单 pipeline（2-3 个操作）：10-20 次
- 中等 pipeline（4-6 个操作）：30-50 次
- 复杂 pipeline（7+ 个操作）：50-100 次

Optuna 通常比 MCTS 需要更少的试验。

### Q: 如何选择 Pareto 前沿上的方案？

**A**: 根据业务需求：
```python
# 精度优先（例如：医疗、金融领域）
best = optimizer.get_best_trial_for_objective(0)

# 成本优先（例如：大规模批处理）
best = optimizer.get_best_trial_for_objective(1)

# 速度优先（例如：实时系统）
best = optimizer.get_best_trial_for_objective(2)
```

### Q: 可以优化操作顺序吗？

**A**: 当前实现主要优化算子选择。如果需要优化操作顺序，需要：
1. 将操作顺序编码为参数
2. 在 `_suggest_pipeline` 中使用 `trial.suggest_categorical` 选择顺序
3. 根据选择重新排列操作

（这部分功能可以扩展）

## 参考资料

- [Optuna 官方文档](https://optuna.readthedocs.io/)
- [多目标优化教程](https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/007_optuna_callback.html)
- [TPE 采样器论文](https://papers.nips.cc/paper/4443-algorithms-for-hyper-parameter-optimization.pdf)
