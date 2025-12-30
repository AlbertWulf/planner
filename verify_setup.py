"""
快速验证脚本

验证所有组件是否可以正常导入和初始化（不需要 vLLM 服务）。
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_imports():
    """测试所有模块导入"""
    print("="*70)
    print("测试模块导入")
    print("="*70)
    
    try:
        print("\n1. 测试预编程算子...")
        from planner.operators.programmatic import (
            ReadJsonOperator,
            KeywordFilterOperator,
            CountTokensOperator
        )
        print("   ✓ 预编程算子导入成功")
        
        print("\n2. 测试 LLM 算子...")
        from planner.operators.llm_operators import (
            VLLMClient,
            LLMSummarizeOperator,
            LLMFilterOperator,
            LLMExtractOperator
        )
        print("   ✓ LLM 算子导入成功")
        
        print("\n3. 测试真实执行器...")
        from planner.core.real_executor import RealExecutor
        print("   ✓ 真实执行器导入成功")
        
        print("\n4. 测试核心组件...")
        from planner.core.pipeline import Pipeline, Operation
        from planner.core.node import Node, ExecutionMetrics
        from planner.optimizer.optimizer import PipelineOptimizer
        print("   ✓ 核心组件导入成功")
        
        print("\n" + "="*70)
        print("✅ 所有模块导入成功！")
        print("="*70)
        return True
        
    except ImportError as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_initialization():
    """测试组件初始化"""
    print("\n" + "="*70)
    print("测试组件初始化")
    print("="*70)
    
    try:
        from planner.core.pipeline import Pipeline, Operation
        from planner.operators.programmatic import KeywordFilterOperator
        
        print("\n1. 测试 Operation 创建...")
        op = Operation(
            name="test_filter",
            op_type="filter",
            candidates=["keyword_filter", "llm_filter"],
            selected_operator="keyword_filter"
        )
        print(f"   ✓ Operation: {op.name}")
        
        print("\n2. 测试 Pipeline 创建...")
        pipeline = Pipeline([op], name="test_pipeline")
        print(f"   ✓ Pipeline: {pipeline}")
        
        print("\n3. 测试算子初始化...")
        filter_op = KeywordFilterOperator(keywords=["测试", "关键词"])
        print(f"   ✓ KeywordFilterOperator: {len(filter_op.keywords)} 个关键词")
        
        print("\n" + "="*70)
        print("✅ 所有组件初始化成功！")
        print("="*70)
        return True
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_file():
    """测试数据文件"""
    print("\n" + "="*70)
    print("测试数据文件")
    print("="*70)
    
    import json
    
    data_path = "planner/data/medical_documents.json"
    
    if not os.path.exists(data_path):
        print(f"❌ 数据文件不存在: {data_path}")
        return False
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n✓ 数据文件加载成功")
        print(f"  - 文件路径: {data_path}")
        print(f"  - 文档数量: {len(data)}")
        print(f"  - 第一条文档 ID: {data[0]['id']}")
        print(f"  - 第一条文档长度: {len(data[0]['text'])} 字符")
        
        print("\n" + "="*70)
        print("✅ 数据文件验证成功！")
        print("="*70)
        return True
        
    except Exception as e:
        print(f"❌ 数据文件读取失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("Pipeline Optimizer - 组件验证")
    print("="*70)
    
    all_passed = True
    
    # 测试导入
    if not test_imports():
        all_passed = False
    
    # 测试初始化
    if not test_initialization():
        all_passed = False
    
    # 测试数据文件
    if not test_data_file():
        all_passed = False
    
    # 总结
    print("\n" + "="*70)
    if all_passed:
        print("🎉 所有验证通过！")
        print("\n下一步:")
        print("  1. 启动 vLLM 服务")
        print("  2. 运行: python -m planner.examples.real_medical_example --mode test")
    else:
        print("⚠️  部分验证失败，请检查错误信息")
    print("="*70)


if __name__ == "__main__":
    main()
