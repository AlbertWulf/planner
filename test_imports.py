"""
测试模块导入是否正常

运行此脚本检查所有 planner 模块是否可以正确导入。
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("="*70)
print("测试 Planner 模块导入")
print("="*70)
print(f"\n项目根目录: {project_root}")
print(f"Python 路径: {sys.path[:3]}")

# 测试导入
print("\n开始测试导入...")

try:
    print("1. 导入 core 模块...")
    from planner.core.pipeline import Pipeline, Operation
    from planner.core.executor import PipelineExecutor, ExecutionMetrics
    from planner.core.node import Node
    print("   ✓ core 模块导入成功")
except Exception as e:
    print(f"   ✗ core 模块导入失败: {e}")

try:
    print("2. 导入 optimizer 模块...")
    from planner.optimizer.optimizer import PipelineOptimizer
    from planner.optimizer.actions import ActionGenerator
    from planner.optimizer.mcts import MCTSSearchEngine
    print("   ✓ optimizer 模块导入成功")
except Exception as e:
    print(f"   ✗ optimizer 模块导入失败: {e}")

try:
    print("3. 导入 operators 模块...")
    from planner.operators.programmatic import ReadJsonOperator, KeywordFilterOperator
    from planner.operators.llm_operators import VLLMClient, LLMExtractOperator
    print("   ✓ operators 模块导入成功")
except Exception as e:
    print(f"   ✗ operators 模块导入失败: {e}")

try:
    print("4. 导入 real_executor...")
    from planner.core.real_executor import RealExecutor
    print("   ✓ real_executor 导入成功")
except Exception as e:
    print(f"   ✗ real_executor 导入失败: {e}")

try:
    print("5. 导入 optuna_optimizer 模块...")
    from planner.optimizer.optuna_optimizer import OptunaOptimizer
    print("   ✓ optuna_optimizer 模块导入成功")
except Exception as e:
    print(f"   ✗ optuna_optimizer 模块导入失败: {e}")
    print(f"   提示: 确保已安装 optuna (pip install optuna)")

print("\n" + "="*70)
print("✨ 导入测试完成!")
print("="*70)
print("\n如果所有模块都成功导入，说明路径配置正确。")
print("现在可以运行示例程序了。")
