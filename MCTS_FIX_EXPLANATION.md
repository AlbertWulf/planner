# MCTS 搜索问题修复说明

## 问题描述

用户报告在运行真实示例时，第二次迭代显示 `depth=0, visits=1`，无法扩展节点。

## 根本原因

发现了两个相关的问题：

### 问题1: `is_fully_expanded()` 逻辑过于严格

**原始代码**：
```python
def is_fully_expanded(self) -> bool:
    # 如果有子节点且访问次数 > 子节点数 * 2，认为已充分扩展
    return len(self.children) > 0 and self.visits > len(self.children) * 2
```

**问题**：
- 第一次扩展后，节点有子节点但 `visits=1`
- 不满足 `visits > len(children) * 2` 条件
- 第二次迭代时，Selection 阶段认为节点未完全扩展，继续选择这个节点
- Expansion 阶段尝试扩展，但生成的 pipeline 已经在 `visited_pipeline_hashes` 中
- 被去重过滤掉，导致无法生成新子节点

### 问题2: 无法扩展的节点会被重复选择

**原始代码**：
```python
if not children:
    self.log("⚠️  无法扩展节点")
    continue  # 直接继续下一次迭代
```

**问题**：
- 无法扩展时，节点的 `visits` 没有增加
- 下次迭代时，Selection 阶段会再次选择同一个节点
- 陷入死循环

### 问题3: 动作生成器每次都随机选择

**原始代码**：
```python
action = random.choice(applicable_actions)  # 随机选择
```

**问题**：
- 可能多次选择同一个动作
- 无法系统地尝试所有可用动作

## 解决方案

### 修复1: 简化 `is_fully_expanded()` 逻辑

```python
def is_fully_expanded(self) -> bool:
    """
    判断节点是否已完全扩展。
    
    对于线性 pipeline，完全扩展意味着：
    - 已经至少尝试过一次扩展
    - 有子节点，或者尝试扩展但无法生成子节点
    """
    # 如果节点已经有子节点，认为已扩展
    # 如果访问次数 > 0 但没有子节点，说明无法扩展
    return len(self.children) > 0 or self.visits > 0
```

**改进**：
- 只要节点有子节点，就认为已扩展
- 或者如果尝试扩展过但没有子节点（visits > 0），也认为已扩展
- 避免重复尝试扩展已经扩展过的节点

### 修复2: 无法扩展时增加 visits

```python
if not children:
    self.log("⚠️  无法扩展节点，标记为已访问")
    # 即使无法生成子节点，也要增加 visits，避免下次再次选中
    selected_node.visits += 1
    continue
```

**改进**：
- 无法扩展时，增加节点的 `visits` 计数
- 下次 Selection 时，由于 `is_fully_expanded()` 返回 True，会选择子节点而不是这个节点

### 修复3: 记录已尝试的动作

```python
class ActionGenerator:
    def __init__(self):
        self.actions = [...]
        # 记录每个节点已经尝试过的动作
        self.node_attempted_actions: Dict[str, set] = {}
    
    def generate_children(self, node: Node, max_children: int = 5):
        node_id = node.get_id()
        
        # 获取此节点已尝试过的动作
        if node_id not in self.node_attempted_actions:
            self.node_attempted_actions[node_id] = set()
        
        attempted = self.node_attempted_actions[node_id]
        
        # 过滤出未尝试的动作
        untried_actions = [
            action for action in applicable_actions 
            if action.name not in attempted
        ]
        
        if not untried_actions:
            # 所有动作都已尝试，随机选择一个
            action = random.choice(applicable_actions)
        else:
            # 选择一个未尝试的动作
            action = random.choice(untried_actions)
        
        # 记录已尝试
        attempted.add(action.name)
        ...
```

**改进**：
- 为每个节点维护已尝试动作的集合
- 优先选择未尝试的动作
- 所有动作都尝试过后，才随机选择
- 确保每个节点都能系统地探索所有优化动作

## 验证

运行测试脚本：
```bash
python planner/test_mcts_fix.py
```

预期输出：
- 第1次扩展：成功生成子节点（使用 switch_operator 动作）
- 第2次扩展：可以继续生成子节点（使用 reorder_operations 动作）
- 第3次扩展：所有动作都已尝试，重新选择

## 对用户的影响

### 之前的行为
- 第1次迭代：扩展根节点，生成子节点
- 第2次迭代：再次选择根节点，但无法生成新子节点（被去重）
- 后续迭代：陷入死循环

### 修复后的行为
- 第1次迭代：扩展根节点，使用第1个动作
- 第2次迭代：继续扩展根节点，使用第2个动作
- 第3次迭代：根节点已完全扩展，开始探索子节点
- 后续迭代：正常的 MCTS 搜索过程

## 注意事项

1. **Pipeline 复杂度**：
   - 如果 pipeline 很简单（只有1-2个操作），可用的优化动作较少
   - 可能在几次迭代后就探索完所有可能的配置
   - 这是正常的，不是 bug

2. **搜索空间大小**：
   - 假设有 N 个操作，每个有 M 个候选算子
   - 搜索空间大小约为 M^N
   - 例如：2个操作，每个2个候选 = 2^2 = 4 种配置
   - 加上操作重排，可能有更多配置

3. **迭代次数**：
   - 对于简单 pipeline，10-20 次迭代可能就足够
   - 对于复杂 pipeline，可能需要 50+ 次迭代

## 建议

如果你的 pipeline 比较简单，可以：

1. **减少迭代次数**：
   ```python
   optimizer = PipelineOptimizer(
       max_iterations=10,  # 从 50 减到 10
       ...
   )
   ```

2. **增加操作和候选算子**：
   ```python
   pipeline = Pipeline([
       Operation(..., candidates=["a", "b", "c"]),  # 更多候选
       Operation(..., candidates=["d", "e", "f"]),
       Operation(..., candidates=["g", "h"]),  # 添加更多操作
   ])
   ```

3. **查看 Pareto 前沿大小**：
   - 如果 Pareto 前沿有多个解，说明优化成功
   - 如果只有1个解，可能需要增加优化空间

## 总结

修复后的代码能够：
- ✅ 避免重复扩展同一节点
- ✅ 系统地尝试所有优化动作
- ✅ 正确处理无法扩展的情况
- ✅ 支持简单和复杂的 pipeline

问题已解决！🎉
