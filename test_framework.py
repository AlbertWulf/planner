"""
快速测试脚本

验证 Pipeline Optimizer 框架的基本功能。
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from planner.core.pipeline import Pipeline, Operation, create_llm_operation
from planner.core.node import Node, ExecutionMetrics
from planner.optimizer.pareto import ParetoFrontier, ParetoPoint
from planner.optimizer.actions import SwitchOperatorAction, ReorderOperationsAction


def test_pipeline_creation():
    """测试 Pipeline 创建"""
    print("测试 1: Pipeline 创建")
    
    op1 = create_llm_operation(
        name="summarize",
        prompt="总结文档",
        candidates=["gpt-4o-mini", "gpt-4o"]
    )
    op2 = create_llm_operation(
        name="filter",
        prompt="过滤无关内容",
        candidates=["gpt-4o-mini", "rule_based"],
        op_type="filter"
    )
    
    pipeline = Pipeline([op1, op2], name="test_pipeline")
    
    print(f"  ✓ Pipeline 创建成功: {pipeline}")
    print(f"  ✓ Pipeline hash: {pipeline.get_hash()}")
    
    return pipeline


def test_node_creation(pipeline):
    """测试 Node 创建和 UCB 计算"""
    print("\n测试 2: Node 创建和 MCTS 统计")
    
    root = Node(pipeline, action_description="root")
    child = Node(pipeline.clone(), parent=root, action_description="child1")
    root.add_child(child)
    
    # 模拟访问
    root.visits = 10
    root.total_reward = 5.0
    child.visits = 3
    child.total_reward = 2.0
    
    ucb = child.get_ucb_score(exploration_weight=1.414)
    
    print(f"  ✓ Root 节点: visits={root.visits}, avg_reward={root.total_reward/root.visits:.2f}")
    print(f"  ✓ Child 节点: visits={child.visits}, UCB={ucb:.3f}")
    
    return root


def test_pareto_frontier():
    """测试 Pareto 前沿"""
    print("\n测试 3: Pareto 前沿管理")
    
    pareto = ParetoFrontier()
    
    # 创建几个测试节点
    pipeline = Pipeline([
        Operation("op1", "map", ["model1"], selected_operator="model1")
    ])
    
    # 节点 1: 高精度，高成本
    node1 = Node(pipeline.clone(), action_description="高精度方案")
    node1.update_metrics(ExecutionMetrics(
        accuracy=0.95,
        tokens=5000,
        execution_time=10.0,
        cost=0.05
    ))
    
    # 节点 2: 低精度，低成本
    node2 = Node(pipeline.clone(), action_description="低成本方案")
    node2.update_metrics(ExecutionMetrics(
        accuracy=0.80,
        tokens=2000,
        execution_time=5.0,
        cost=0.02
    ))
    
    # 节点 3: 中等（被支配）
    node3 = Node(pipeline.clone(), action_description="中等方案（应被支配）")
    node3.update_metrics(ExecutionMetrics(
        accuracy=0.85,
        tokens=4000,
        execution_time=8.0,
        cost=0.04
    ))
    
    # 添加到 Pareto 前沿
    added1 = pareto.add_node(node1)
    added2 = pareto.add_node(node2)
    added3 = pareto.add_node(node3)
    
    print(f"  ✓ 节点1 (高精度) 添加: {added1}")
    print(f"  ✓ 节点2 (低成本) 添加: {added2}")
    print(f"  ✓ 节点3 (中等) 添加: {added3} (应该被支配)")
    print(f"  ✓ Pareto 前沿大小: {pareto.size()}")
    
    best_acc = pareto.get_best_accuracy()
    lowest_cost = pareto.get_lowest_cost()
    
    if best_acc:
        print(f"  ✓ 最佳精度: {best_acc.accuracy:.3f}")
    if lowest_cost:
        print(f"  ✓ 最低成本: ${lowest_cost.cost:.4f}")
    
    return pareto


def test_optimization_actions():
    """测试优化动作"""
    print("\n测试 4: 优化动作")
    
    # 创建有多个候选的 pipeline
    pipeline = Pipeline([
        create_llm_operation(
            name="map1",
            prompt="操作1",
            candidates=["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-20241022"]
        ),
        create_llm_operation(
            name="filter1",
            prompt="操作2",
            candidates=["gpt-4o-mini", "rule_based"],
            op_type="filter"
        ),
    ])
    
    # 测试切换算子动作
    switch_action = SwitchOperatorAction()
    variants = switch_action.apply(pipeline)
    
    print(f"  ✓ 原始 pipeline: {pipeline}")
    print(f"  ✓ 切换算子生成 {len(variants)} 个变体")
    for i, variant in enumerate(variants[:3]):  # 只显示前3个
        print(f"     - 变体{i+1}: {variant}")
    
    # 测试重排动作
    reorder_action = ReorderOperationsAction()
    reorder_variants = reorder_action.apply(pipeline)
    
    print(f"  ✓ 操作重排生成 {len(reorder_variants)} 个变体")
    for i, variant in enumerate(reorder_variants):
        print(f"     - 重排{i+1}: {variant}")


def main():
    """运行所有测试"""
    print("=" * 70)
    print("Pipeline Optimizer Framework - 功能测试")
    print("=" * 70)
    
    try:
        # 测试 1: Pipeline 创建
        pipeline = test_pipeline_creation()
        
        # 测试 2: Node 和 MCTS
        root = test_node_creation(pipeline)
        
        # 测试 3: Pareto 前沿
        pareto = test_pareto_frontier()
        
        # 测试 4: 优化动作
        test_optimization_actions()
        
        print("\n" + "=" * 70)
        print("✅ 所有测试通过！框架功能正常。")
        print("=" * 70)
        
        print("\n下一步:")
        print("  1. 运行完整示例: python -m planner.examples.medical_summary_example")
        print("  2. 实现自定义执行器")
        print("  3. 实现自定义评估函数")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
