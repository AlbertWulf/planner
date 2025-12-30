# Pipeline Optimizer Framework - 实现总结

## 概述

基于 DocETL MOAR 优化器设计，实现了一个针对线性 pipeline 的三目标优化框架。

## 已完成的组件

### 1. 核心数据结构 (`planner/core/`)

#### `pipeline.py` - Pipeline 和 Operation 定义
- **Operation**: 表示单个操作（map、filter、transform等）
  - 支持多个候选算子
  - 包含 prompt、参数等配置
  - 提供 clone、hash 等方法
  
- **Pipeline**: 线性操作序列
  - 支持操作替换、交换
  - 提供 hash、序列化等方法
  
- **便捷函数**:
  - `create_llm_operation()`: 创建 LLM 操作
  - `create_transform_operation()`: 创建数据转换操作

#### `node.py` - 搜索树节点
- **ExecutionMetrics**: 执行指标（accuracy, tokens, time, cost）
- **Node**: MCTS 搜索树节点
  - 维护 visits、rewards 等 MCTS 统计信息
  - 实现 UCB 分数计算
  - 支持回溯更新（backpropagation）
  - 记录父子关系和执行指标

#### `executor.py` - 执行器和评估器
- **PipelineExecutor**: 执行器基类
- **MockExecutor**: 模拟执行器（用于测试）
  - 模拟不同模型的成本和精度
  - 生成执行指标
  
- **Evaluator**: 精度评估器
  - 接收自定义评估函数
  - 计算 pipeline 输出的精度

### 2. 优化器模块 (`planner/optimizer/`)

#### `pareto.py` - Pareto 前沿管理
- **ParetoPoint**: Pareto 前沿上的点
  - 实现支配关系判断
  
- **ParetoFrontier**: Pareto 前沿管理器
  - 维护非支配解集合
  - 提供按精度、成本、时间排序
  - 返回最佳精度、最低成本、最快、平衡等推荐方案

#### `actions.py` - 优化动作
- **SwitchOperatorAction**: 切换操作的算子
  - 为每个操作尝试其候选算子
  
- **ReorderOperationsAction**: 重排相邻操作
  - 实现谓词下推等优化
  - 仅在有意义时交换（如 filter 移到 map 前）
  
- **ActionGenerator**: 动作生成器
  - 根据 pipeline 选择可用动作
  - 生成子节点

#### `mcts.py` - MCTS 搜索引擎
- **MCTSSearchEngine**: 核心搜索引擎
  - **Selection**: 使用 UCB 选择最有希望的节点
  - **Expansion**: 应用优化动作生成子节点
  - **Simulation**: 执行 pipeline 并评估
  - **Backpropagation**: 回溯更新节点统计
  - 支持去重、日志输出
  - 自动更新 Pareto 前沿

#### `optimizer.py` - 主优化器接口
- **PipelineOptimizer**: 统一优化接口
  - 整合执行器、评估器、MCTS 搜索
  - 提供简单的 API
  - 支持结果保存和摘要输出

### 3. 示例 (`planner/examples/`)

#### `medical_summary_example.py`
- 完整的医疗文档处理示例
- 展示如何定义 pipeline
- 演示优化流程和结果分析
- 说明 Pareto 前沿的权衡

### 4. 测试 (`planner/`)

#### `test_framework.py`
- 单元测试各个组件
- 验证 Pipeline、Node、Pareto、Actions 功能
- 快速验证框架正确性

## 设计特点

### 1. 借鉴 DocETL MOAR 的核心设计
- ✅ MCTS 搜索算法
- ✅ Pareto 前沿管理
- ✅ 多目标优化（精度 + 成本 + 时间）
- ✅ 节点去重
- ✅ UCB 选择策略

### 2. 简化实现
- ✅ 仅支持线性 pipeline（无 DAG）
- ✅ 预定义的优化动作（切换算子、重排操作）
- ✅ 无需 Agent 智能决策（简化）
- ✅ 模拟执行器（便于测试）

### 3. 可扩展性
- ✅ 清晰的模块划分
- ✅ 易于添加新的优化动作
- ✅ 支持自定义执行器和评估器
- ✅ 插件式设计

## 使用流程

```python
# 1. 定义 pipeline
pipeline = Pipeline([
    create_llm_operation("map", "总结", ["gpt-4o-mini", "gpt-4o"]),
    create_llm_operation("filter", "过滤", ["gpt-4o-mini", "rule_based"], "filter"),
])

# 2. 创建优化器
optimizer = PipelineOptimizer(
    pipeline=pipeline,
    executor=MockExecutor(),
    max_iterations=50
)

# 3. 运行优化
pareto_frontier = optimizer.optimize()

# 4. 查看结果
optimizer.print_summary()
```

## 输出结果

优化完成后生成：
- `pareto_frontier.json`: 所有 Pareto 最优解
- `recommendations.json`: 推荐方案（最佳精度、最低成本、最快、平衡）
- `search_stats.json`: 搜索统计信息

## 与 DocETL MOAR 的对比

| 特性 | Pipeline Optimizer | DocETL MOAR |
|------|-------------------|-------------|
| 支持的结构 | 线性 pipeline | DAG（有向无环图）|
| 优化目标 | 精度 + Tokens + 时间 | 精度 + 成本 |
| 搜索算法 | MCTS | MCTS |
| Pareto 前沿 | ✅ 三维 | ✅ 二维 |
| 操作类型 | 自定义 | DocETL 预定义 |
| 优化动作 | 算子切换 + 操作重排 | 26 种 Directives |
| Agent 决策 | ❌ | ✅ LLM Agent |
| 实现复杂度 | 简化 | 完整 |

## 扩展方向

1. **添加更多优化动作**
   - Gleaning 优化
   - Chunking 策略调整
   - 并行化优化

2. **实现真实执行器**
   - 集成 LiteLLM
   - 支持实际 LLM 调用
   - 准确的成本和延迟计量

3. **增强评估功能**
   - 支持多种评估指标
   - 集成标准数据集
   - 自动化精度计算

4. **可视化**
   - 搜索树可视化
   - Pareto 前沿可视化
   - 优化过程追踪

5. **Agent 决策**
   - 引入 LLM Agent 选择优化动作
   - 智能权衡三个目标

## 文件清单

```
planner/
├── __init__.py                 # 包入口
├── README.md                   # 使用文档
├── test_framework.py           # 单元测试
├── core/
│   ├── __init__.py
│   ├── pipeline.py             # Pipeline 和 Operation 定义
│   ├── node.py                 # 搜索树节点
│   └── executor.py             # 执行器和评估器
├── optimizer/
│   ├── __init__.py
│   ├── mcts.py                 # MCTS 搜索引擎
│   ├── pareto.py               # Pareto 前沿管理
│   ├── actions.py              # 优化动作
│   └── optimizer.py            # 主优化器接口
└── examples/
    ├── __init__.py
    └── medical_summary_example.py  # 完整示例
```

## 总结

成功实现了一个基于 DocETL MOAR 设计的轻量级 pipeline 优化框架：

✅ **核心功能完整**: MCTS + Pareto + 三目标优化  
✅ **设计清晰**: 模块化、易扩展  
✅ **开箱即用**: 提供示例和测试  
✅ **文档完善**: README + 代码注释  

框架已准备就绪，可以：
1. 运行测试验证功能
2. 运行示例体验优化过程
3. 实现自定义执行器接入真实系统
4. 根据需求扩展新功能
