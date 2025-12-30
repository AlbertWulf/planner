"""
医疗文档总结示例

展示如何使用 Pipeline Optimizer 优化一个医疗文档处理 pipeline。
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from planner.core.pipeline import Pipeline, Operation, create_llm_operation, create_transform_operation
from planner.optimizer.optimizer import PipelineOptimizer
from planner.core.executor import MockExecutor


def create_medical_summary_pipeline() -> Pipeline:
    """
    创建医疗文档总结 pipeline。
    
    Pipeline 流程:
    1. read_files: 读取医疗文档
    2. chunk: 将文档分块
    3. map: 总结每个段落
    4. filter: 过滤与药物无关的段落
    5. reduce: 聚合结果
    """
    operations = [
        # 1. 读取文件（数据源操作）
        create_transform_operation(
            name="read_files",
            candidates=["read_json", "read_csv", "read_txt"]
        ),
        
        # 2. 分块操作
        create_transform_operation(
            name="chunk",
            candidates=["fixed_chunk_500", "fixed_chunk_1000", "semantic_chunk"],
            params={"chunk_size": 500}
        ),
        
        # 3. 总结段落（Map 操作）
        create_llm_operation(
            name="summarize",
            prompt="把输入的段落进行总结，提取关键医疗信息",
            candidates=["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-20241022"],
            op_type="map"
        ),
        
        # 4. 过滤无关段落（Filter 操作）
        create_llm_operation(
            name="filter_relevant",
            prompt="过滤掉和药物无关的段落",
            candidates=["gpt-4o-mini", "gpt-3.5-turbo", "rule_based"],
            op_type="filter"
        ),
        
        # 5. 聚合结果（Reduce 操作）
        create_llm_operation(
            name="aggregate",
            prompt="将所有相关段落的信息聚合成最终报告",
            candidates=["gpt-4o", "gpt-4o-mini"],
            op_type="map"
        ),
    ]
    
    return Pipeline(
        operations=operations,
        name="medical_summary_pipeline"
    )


def run_optimization_example():
    """运行优化示例"""
    
    print("="*70)
    print("🏥 医疗文档处理 Pipeline 优化示例")
    print("="*70)
    
    # 1. 创建初始 pipeline
    print("\n📝 创建初始 pipeline...")
    pipeline = create_medical_summary_pipeline()
    print(f"初始配置: {pipeline}")
    
    # 2. 创建优化器
    print("\n⚙️  初始化优化器...")
    optimizer = PipelineOptimizer(
        pipeline=pipeline,
        executor=MockExecutor(),  # 使用模拟执行器
        max_iterations=30,  # 搜索 30 轮
        exploration_weight=1.414,
        max_children_per_node=3,
        save_dir="planner/results/medical_summary",
        verbose=True
    )
    
    # 3. 运行优化
    print("\n🚀 开始优化...")
    pareto_frontier = optimizer.optimize()
    
    # 4. 打印结果摘要
    optimizer.print_summary()
    
    # 5. 保存结果
    print("\n💾 保存优化结果...")
    print(f"   - Pareto 前沿: planner/results/medical_summary/pareto_frontier.json")
    print(f"   - 推荐方案: planner/results/medical_summary/recommendations.json")
    print(f"   - 搜索统计: planner/results/medical_summary/search_stats.json")


def demonstrate_pareto_tradeoffs():
    """演示 Pareto 前沿的权衡"""
    
    print("\n" + "="*70)
    print("📊 Pareto 前沿权衡分析")
    print("="*70)
    
    print("""
在医疗文档处理场景中，我们需要在三个目标之间权衡：

1. 📈 精度 (Accuracy)
   - 更好的模型（如 gpt-4o）提供更高精度
   - 但成本和时间会增加

2. 💰 成本 (Tokens/Cost)
   - 使用更小的模型（如 gpt-4o-mini）降低成本
   - 但可能牺牲一些精度

3. ⚡ 速度 (Time)
   - 更快的模型或更少的操作减少延迟
   - 但可能影响精度

Pareto 前沿返回的方案类型：

🏆 最佳精度方案:
   - 所有操作都用最好的模型（gpt-4o）
   - 适合：准确性要求极高的场景

💰 最低成本方案:
   - 尽可能使用便宜的模型（gpt-4o-mini, rule_based）
   - 适合：成本敏感的批量处理

⚡ 最快执行方案:
   - 使用快速模型 + 操作重排优化
   - 适合：实时响应场景

⚖️  平衡方案:
   - 在三个目标间取得最佳平衡
   - 适合：大多数生产场景
    """)


if __name__ == "__main__":
    # 运行优化示例
    run_optimization_example()
    
    # 演示权衡分析
    demonstrate_pareto_tradeoffs()
