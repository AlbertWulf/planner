"""
真实的医疗文档处理 Pipeline 示例

使用真实的算子和 vLLM 服务进行优化。

运行前请确保：
1. vLLM 服务已启动（http://localhost:8000）
2. 数据文件存在（planner/data/medical_documents.json）
"""

import os
import sys

# 添加项目根目录到路径
# __file__ -> examples/real_medical_example.py
# parent -> planner/
# parent.parent -> docetl-main/
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from planner.core.pipeline import Pipeline, Operation
from planner.core.real_executor import RealExecutor
from planner.core.executor import Evaluator, create_executor_func
from planner.optimizer.optimizer import PipelineOptimizer
import json


def create_medical_pipeline() -> Pipeline:
    """
    创建医疗文档处理 pipeline。
    
    流程：
    1. read_json: 读取医疗文档
    2. filter: 过滤医疗相关文档
    3. extract: 提取药物信息
    """
    operations = [
        # 1. 读取数据（只有一个候选）
        Operation(
            name="read_data",
            op_type="transform",
            candidates=["read_json"],
            selected_operator="read_json"
        ),
        
        # 2. 过滤文档（规则 vs LLM）
        Operation(
            name="filter_medical",
            op_type="filter",
            prompt="是否为医疗相关文档（包含患者、诊断、药物等信息）",
            candidates=["keyword_filter", "llm_filter"],
            selected_operator="keyword_filter",  # 默认使用规则
            params={"keywords": ["患者", "药", "诊断", "治疗"]}
        ),
        
        # 3. 提取药物信息（LLM）
        Operation(
            name="extract_medications",
            op_type="map",
            prompt="提取药物名称和用法",
            candidates=["llm_extract"],
            selected_operator="llm_extract",
            params={"target": "药物名称及用法"}
        ),
    ]
    
    return Pipeline(
        operations=operations,
        name="medical_document_pipeline"
    )


def evaluate_results(ground_truth, predictions):
    """
    评估函数：计算提取准确性。
    
    简化实现：检查是否提取到药物信息。
    """
    if not predictions or len(predictions) == 0:
        return 0.0
    
    # 计算有多少文档成功提取了药物信息
    success_count = 0
    for pred in predictions:
        if "medications" in pred and len(pred["medications"]) > 0:
            success_count += 1
    
    accuracy = success_count / len(predictions)
    return accuracy


def run_single_pipeline():
    """运行单个 pipeline（测试）"""
    print("="*70)
    print("测试单个 Pipeline 执行")
    print("="*70)
    
    # 创建 pipeline
    pipeline = create_medical_pipeline()
    print(f"\n初始 Pipeline: {pipeline}\n")
    
    # 创建执行器
    executor = RealExecutor(
        vllm_base_url="http://localhost:8000",
        vllm_model="default",
        data_path="planner/data/medical_documents.json"
    )
    
    # 执行 pipeline
    try:
        result = executor.execute(pipeline)
        
        # 显示部分结果
        print("\n前3条结果示例：")
        for i, doc in enumerate(result[:3]):
            print(f"\n文档 {i+1}:")
            print(f"  ID: {doc.get('id')}")
            print(f"  原文: {doc.get('text', '')[:50]}...")
            if 'medications' in doc:
                print(f"  提取的药物: {doc['medications']}")
        
        # 评估
        accuracy = evaluate_results(None, result)
        print(f"\n提取成功率: {accuracy:.2%}")
        
        # 获取指标
        metrics = executor.get_metrics()
        print(f"\n执行指标:")
        print(f"  Tokens: {metrics.tokens}")
        print(f"  时间: {metrics.execution_time:.2f}s")
        print(f"  成本: ${metrics.cost:.6f}")
        
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()


def run_optimization():
    """运行完整的优化过程"""
    print("\n" + "="*70)
    print("🚀 开始 Pipeline 优化")
    print("="*70)
    
    # 创建初始 pipeline
    pipeline = create_medical_pipeline()
    print(f"\n📝 初始配置: {pipeline}\n")
    
    # 创建执行器
    executor = RealExecutor(
        vllm_base_url="http://localhost:8000",
        vllm_model="default",
        data_path="planner/data/medical_documents.json"
    )
    
    # 创建评估器
    evaluator = Evaluator(evaluate_results)
    
    # 创建优化器
    optimizer = PipelineOptimizer(
        pipeline=pipeline,
        executor=executor,
        evaluator=evaluator,
        max_iterations=10,  # 减少迭代次数以加快测试
        exploration_weight=1.414,
        max_children_per_node=2,
        save_dir="planner/results/real_optimization",
        verbose=True
    )
    
    # 运行优化
    try:
        pareto_frontier = optimizer.optimize()
        
        # 打印结果摘要
        optimizer.print_summary()
        
        # 保存详细结果
        print(f"\n💾 结果已保存到: planner/results/real_optimization/")
        
    except Exception as e:
        print(f"\n❌ 优化失败: {e}")
        import traceback
        traceback.print_exc()


def check_vllm_service():
    """检查 vLLM 服务是否可用"""
    import requests
    
    print("检查 vLLM 服务...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ vLLM 服务正常运行")
            return True
        else:
            print(f"⚠️  vLLM 服务响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到 vLLM 服务: {e}")
        print("\n请先启动 vLLM 服务：")
        print("  python -m vllm.entrypoints.openai.api_server \\")
        print("    --model <你的模型路径> \\")
        print("    --host 0.0.0.0 \\")
        print("    --port 8000")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="真实 Pipeline 优化示例")
    parser.add_argument(
        "--mode",
        choices=["test", "optimize"],
        default="test",
        help="运行模式：test（测试单个pipeline）或 optimize（完整优化）"
    )
    
    args = parser.parse_args()
    
    # 检查 vLLM 服务
    if not check_vllm_service():
        print("\n提示：如果没有 vLLM 服务，可以修改代码使用 MockExecutor 进行测试")
        return
    
    # 检查数据文件
    data_path = "planner/data/medical_documents.json"
    if not os.path.exists(data_path):
        print(f"\n❌ 数据文件不存在: {data_path}")
        return
    
    print(f"\n✅ 数据文件已找到: {data_path}")
    
    # 运行
    if args.mode == "test":
        run_single_pipeline()
    else:
        run_optimization()


if __name__ == "__main__":
    main()
