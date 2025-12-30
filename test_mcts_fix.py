"""
测试 MCTS 搜索修复

验证节点扩展逻辑是否正确工作。
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from planner.core.pipeline import Pipeline, Operation
from planner.core.node import Node, ExecutionMetrics
from planner.optimizer.actions import ActionGenerator


def test_node_expansion():
    """测试节点扩展逻辑"""
    print("="*70)
    print("测试节点扩展逻辑")
    print("="*70)
    
    # 创建一个简单的 pipeline
    pipeline = Pipeline([
        Operation(
            name="filter",
            op_type="filter",
            candidates=["keyword_filter", "llm_filter"],
            selected_operator="keyword_filter"
        ),
        Operation(
            name="extract",
            op_type="map",
            candidates=["llm_extract"],
            selected_operator="llm_extract"
        ),
    ])
    
    print(f"\n初始 Pipeline: {pipeline}")
    
    # 创建根节点
    root = Node(pipeline, action_description="root")
    
    # 创建动作生成器
    action_gen = ActionGenerator()
    
    # 第一次扩展
    print("\n--- 第1次扩展 ---")
    children1 = action_gen.generate_children(root, max_children=3)
    print(f"生成 {len(children1)} 个子节点")
    for i, child in enumerate(children1):
        print(f"  子节点 {i+1}: {child.pipeline}")
    
    # 添加子节点
    for child in children1:
        root.add_child(child)
    
    print(f"\nRoot 节点状态: visits={root.visits}, children={len(root.children)}")
    print(f"is_leaf: {root.is_leaf()}")
    print(f"is_fully_expanded: {root.is_fully_expanded()}")
    
    # 第二次扩展
    print("\n--- 第2次扩展 ---")
    root.visits = 1  # 模拟访问
    print(f"Root 节点状态: visits={root.visits}, children={len(root.children)}")
    print(f"is_fully_expanded: {root.is_fully_expanded()}")
    
    children2 = action_gen.generate_children(root, max_children=3)
    print(f"生成 {len(children2)} 个子节点")
    for i, child in enumerate(children2):
        print(f"  子节点 {i+1}: {child.pipeline}")
    
    # 第三次扩展
    print("\n--- 第3次扩展 ---")
    root.visits = 2  # 模拟访问
    children3 = action_gen.generate_children(root, max_children=3)
    print(f"生成 {len(children3)} 个子节点")
    for i, child in enumerate(children3):
        print(f"  子节点 {i+1}: {child.pipeline}")
    
    print("\n✓ 测试完成")
    print("\n说明：")
    print("  - 第1次扩展：尝试 switch_operator 动作")
    print("  - 第2次扩展：尝试 reorder_operations 动作")
    print("  - 第3次扩展：所有动作都已尝试，重新选择")


def test_applicable_actions():
    """测试可用动作检测"""
    print("\n" + "="*70)
    print("测试可用动作检测")
    print("="*70)
    
    action_gen = ActionGenerator()
    
    # 测试1: 有多个候选算子的 pipeline
    pipeline1 = Pipeline([
        Operation("op1", "filter", ["a", "b"], selected_operator="a"),
    ])
    actions1 = action_gen.get_applicable_actions(pipeline1)
    print(f"\nPipeline 1: {pipeline1}")
    print(f"可用动作: {[a.name for a in actions1]}")
    
    # 测试2: 有可重排操作的 pipeline
    pipeline2 = Pipeline([
        Operation("map1", "map", ["a"], selected_operator="a"),
        Operation("filter1", "filter", ["b"], selected_operator="b"),
    ])
    actions2 = action_gen.get_applicable_actions(pipeline2)
    print(f"\nPipeline 2: {pipeline2}")
    print(f"可用动作: {[a.name for a in actions2]}")
    
    # 测试3: 只有一个操作
    pipeline3 = Pipeline([
        Operation("op1", "map", ["a"], selected_operator="a"),
    ])
    actions3 = action_gen.get_applicable_actions(pipeline3)
    print(f"\nPipeline 3: {pipeline3}")
    print(f"可用动作: {[a.name for a in actions3]}")
    
    print("\n✓ 测试完成")


if __name__ == "__main__":
    test_node_expansion()
    test_applicable_actions()
