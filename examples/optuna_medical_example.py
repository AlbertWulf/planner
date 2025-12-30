"""
基于 Optuna 的医疗文档 Pipeline 优化示例

这个示例展示如何使用 Optuna 进行 pipeline 优化，相比 MCTS 方案：
- 代码更简洁（不到 200 行）
- 收敛更快
- 结果更稳定
- 可视化更丰富
"""

import sys
import os
from pathlib import Path
import argparse

# 添加项目根目录到路径
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from planner.core.pipeline import Pipeline, Operation
from planner.core.real_executor import RealExecutor
from planner.optimizer.optuna_optimizer import OptunaOptimizer
from planner.optimizer.optuna_optimizer.visualizer import save_all_visualizations
import requests


def check_vllm_service():
    """检查 vLLM 服务是否可用"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def create_medical_pipeline() -> Pipeline:
    """
    创建医疗文档处理 pipeline。
    
    Pipeline 流程:
    1. 读取医疗文档
    2. 过滤医疗相关文档（规则 vs LLM）
    3. 提取药物信息（LLM）
    
    优化目标：
    - 精度：正确识别医疗文档并提取药物
    - Tokens：减少 LLM 调用成本
    - 时间：加快处理速度
    """
    operations = [
        # 1. 读取数据（固定算子）
        Operation(
            name="read_data",
            op_type="transform",
            prompt="读取医疗文档数据",
            candidates=["read_json"],
            selected_operator="read_json",
            params={}
        ),
        
        # 2. 过滤文档（待优化：规则 vs LLM）
        Operation(
            name="filter_medical",
            op_type="filter",
            prompt="过滤出医疗相关文档",
            candidates=["keyword_filter", "llm_filter"],  # 两个候选算子
            selected_operator="keyword_filter",  # 默认使用规则
            params={"keywords": ["患者", "药", "诊断", "治疗", "医院"]}
        ),
        
        # 3. 提取药物信息（LLM 算子）
        Operation(
            name="extract_medications",
            op_type="map",
            prompt="提取药物名称和用法",
            candidates=["llm_extract"],
            selected_operator="llm_extract",
            params={"target": "药物名称及用法"}
        ),
    ]
    
    return Pipeline(operations=operations, name="medical_document_pipeline")


def evaluate_results(results: list) -> float:
    """
    评估 pipeline 执行结果的精度。
    
    评估标准：
    - 过滤阶段：应该保留所有医疗文档（8条），过滤掉非医疗文档（2条）
    - 提取阶段：每个文档应该提取到药物信息
    
    Args:
        results: Pipeline 执行结果
    
    Returns:
        精度分数 (0-1)
    """
    if not results:
        return 0.0
    
    score = 0.0
    total_weight = 0.0
    
    # 1. 检查文档数量（权重 0.4）
    # 正确的医疗文档数量应该是 8 条
    doc_count = len(results)
    expected_count = 8
    count_score = min(doc_count / expected_count, 1.0) if expected_count > 0 else 0.0
    score += count_score * 0.4
    total_weight += 0.4
    
    # 2. 检查药物提取质量（权重 0.6）
    extraction_scores = []
    for doc in results:
        if "medications" in doc and doc["medications"]:
            # 提取到药物信息，得分 1.0
            extraction_scores.append(1.0)
        else:
            # 未提取到药物信息，得分 0.0
            extraction_scores.append(0.0)
    
    if extraction_scores:
        avg_extraction_score = sum(extraction_scores) / len(extraction_scores)
        score += avg_extraction_score * 0.6
        total_weight += 0.6
    
    # 归一化
    final_score = score / total_weight if total_weight > 0 else 0.0
    
    return final_score


def run_optimization():
    """运行 Optuna 优化"""
    print("="*70)
    print("🚀 基于 Optuna 的医疗文档 Pipeline 优化")
    print("="*70)
    
    # 1. 检查 vLLM 服务
    print("\n1️⃣  检查 vLLM 服务...")
    if not check_vllm_service():
        print("❌ vLLM 服务未启动!")
        print("\n请先启动 vLLM 服务:")
        print("python -m vllm.entrypoints.openai.api_server \\")
        print("    --model <你的模型路径> \\")
        print("    --port 8000")
        return
    print("✓ vLLM 服务正常")
    
    # 2. 创建 pipeline
    print("\n2️⃣  创建 Pipeline...")
    pipeline = create_medical_pipeline()
    print(f"✓ Pipeline 包含 {len(pipeline.operations)} 个操作")
    for i, op in enumerate(pipeline.operations):
        print(f"   {i+1}. {op.name}: {len(op.candidates)} 个候选算子")
    
    # 3. 创建执行器
    print("\n3️⃣  创建执行器...")
    executor = RealExecutor(
        vllm_base_url="http://localhost:8000",
        vllm_model="default",
        data_path="planner/data/medical_documents.json"
    )
    print("✓ 执行器初始化完成")
    
    # 4. 创建优化器
    print("\n4️⃣  创建 Optuna 优化器...")
    optimizer = OptunaOptimizer(
        pipeline=pipeline,
        executor=executor,
        evaluator=evaluate_results,
        n_trials=20,  # 试验次数（Optuna 通常比 MCTS 需要更少的迭代）
        n_jobs=1,  # 串行执行（可改为 2、4 进行并行优化）
        save_dir="planner/results/optuna_optimization",
        verbose=True
    )
    print("✓ 优化器初始化完成")
    
    # 5. 执行优化
    print("\n5️⃣  开始优化...")
    print("-"*70)
    pareto_trials = optimizer.optimize()
    
    # 6. 打印结果摘要
    print("\n6️⃣  优化结果摘要")
    optimizer.print_summary()
    
    # 7. 生成可视化
    print("\n7️⃣  生成可视化图表...")
    try:
        save_all_visualizations(
            optimizer.study,
            output_dir="planner/results/optuna_optimization"
        )
    except Exception as e:
        print(f"⚠️  可视化生成失败: {e}")
        print("提示: 安装 plotly 以启用可视化: pip install plotly")
    
    # 8. 推荐方案
    print("\n8️⃣  推荐方案")
    print("="*70)
    
    # 获取不同目标的最佳方案
    best_accuracy_trial = optimizer.get_best_trial_for_objective(0)
    best_tokens_trial = optimizer.get_best_trial_for_objective(1)
    best_time_trial = optimizer.get_best_trial_for_objective(2)
    
    print("\n🎯 最高精度方案:")
    print(f"   精度: {best_accuracy_trial.values[0]:.3f}")
    print(f"   Tokens: {best_accuracy_trial.values[1]}")
    print(f"   时间: {best_accuracy_trial.values[2]:.2f}s")
    print(f"   配置: {best_accuracy_trial.params}")
    
    print("\n💰 最低成本方案:")
    print(f"   精度: {best_tokens_trial.values[0]:.3f}")
    print(f"   Tokens: {best_tokens_trial.values[1]}")
    print(f"   时间: {best_tokens_trial.values[2]:.2f}s")
    print(f"   配置: {best_tokens_trial.params}")
    
    print("\n⚡ 最快速度方案:")
    print(f"   精度: {best_time_trial.values[0]:.3f}")
    print(f"   Tokens: {best_time_trial.values[1]}")
    print(f"   时间: {best_time_trial.values[2]:.2f}s")
    print(f"   配置: {best_time_trial.params}")
    
    print("\n" + "="*70)
    print("✨ 优化完成!")
    print("="*70)


def run_test():
    """测试单个 pipeline 配置"""
    print("="*70)
    print("🧪 测试 Pipeline 执行")
    print("="*70)
    
    # 检查服务
    if not check_vllm_service():
        print("❌ vLLM 服务未启动!")
        return
    
    # 创建 pipeline
    pipeline = create_medical_pipeline()
    print(f"\n测试 Pipeline: {pipeline}")
    
    # 创建执行器
    executor = RealExecutor(
        vllm_base_url="http://localhost:8000",
        vllm_model="default",
        data_path="planner/data/medical_documents.json"
    )
    
    # 执行
    print("\n执行中...")
    result = executor.execute(pipeline)
    metrics = executor.last_metrics
    
    # 评估
    accuracy = evaluate_results(result)
    
    # 输出结果
    print("\n" + "="*70)
    print("📊 执行结果")
    print("="*70)
    print(f"精度: {accuracy:.3f}")
    print(f"Tokens: {metrics.tokens}")
    print(f"时间: {metrics.execution_time:.2f}s")
    print(f"成本: ${metrics.cost:.4f}")
    print(f"\n输出文档数量: {len(result)}")
    
    # 显示部分结果
    if result:
        print(f"\n示例文档:")
        doc = result[0]
        print(f"  ID: {doc.get('id', 'N/A')}")
        if 'medications' in doc:
            print(f"  提取的药物: {doc['medications'][:3]}")  # 显示前3个


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Optuna Pipeline 优化示例")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["test", "optimize"],
        default="optimize",
        help="运行模式: test=测试单个配置, optimize=运行优化"
    )
    
    args = parser.parse_args()
    
    if args.mode == "test":
        run_test()
    else:
        run_optimization()


if __name__ == "__main__":
    main()
