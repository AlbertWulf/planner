"""
真实的 Pipeline 执行器

支持预编程算子和 LLM 算子的实际执行。
"""

from typing import Any, Dict, List
import time
from planner.core.pipeline import Pipeline, Operation
from planner.core.executor import PipelineExecutor, ExecutionMetrics
from planner.operators.programmatic import (
    ReadJsonOperator,
    KeywordFilterOperator,
    CountTokensOperator,
    RegexExtractOperator,
    DeduplicateOperator
)
from planner.operators.llm_operators import (
    VLLMClient,
    LLMSummarizeOperator,
    LLMFilterOperator,
    LLMExtractOperator
)


class RealExecutor(PipelineExecutor):
    """
    真实的 Pipeline 执行器。
    
    根据 Operation 的配置，实例化并执行对应的算子。
    """
    
    def __init__(
        self,
        vllm_base_url: str = "http://localhost:8000",
        vllm_model: str = "default",
        data_path: str = "planner/data/medical_documents.json"
    ):
        """
        初始化真实执行器。
        
        Args:
            vllm_base_url: vLLM 服务地址
            vllm_model: vLLM 模型名称
            data_path: 数据文件路径
        """
        self.vllm_client = VLLMClient(base_url=vllm_base_url, model=vllm_model)
        self.data_path = data_path
        self.last_metrics: ExecutionMetrics = None
        
        # 算子注册表
        self.operator_registry = self._build_operator_registry()
    
    def _build_operator_registry(self) -> Dict[str, type]:
        """构建算子注册表"""
        return {
            # 预编程算子
            "read_json": ReadJsonOperator,
            "keyword_filter": KeywordFilterOperator,
            "count_tokens": CountTokensOperator,
            "regex_extract": RegexExtractOperator,
            "deduplicate": DeduplicateOperator,
            
            # LLM 算子
            "llm_summarize": LLMSummarizeOperator,
            "llm_filter": LLMFilterOperator,
            "llm_extract": LLMExtractOperator,
        }
    
    def _instantiate_operator(self, operation: Operation) -> Any:
        """
        根据 Operation 实例化算子。
        
        Args:
            operation: Operation 配置
        
        Returns:
            算子实例
        """
        operator_name = operation.selected_operator
        
        # 特殊处理：read_json
        if operator_name == "read_json":
            return ReadJsonOperator(self.data_path)
        
        # 特殊处理：keyword_filter
        if operator_name == "keyword_filter":
            keywords = operation.params.get("keywords", ["药", "患者", "诊断"])
            return KeywordFilterOperator(keywords=keywords)
        
        # 特殊处理：LLM 算子
        if operator_name == "llm_summarize":
            return LLMSummarizeOperator(
                vllm_client=self.vllm_client,
                max_tokens=operation.params.get("max_tokens", 200),
                temperature=operation.params.get("temperature", 0.3)
            )
        
        if operator_name == "llm_filter":
            criteria = operation.prompt or "是否为医疗相关文档"
            return LLMFilterOperator(
                vllm_client=self.vllm_client,
                filter_criteria=criteria,
                max_tokens=50,
                temperature=0.1
            )
        
        if operator_name == "llm_extract":
            target = operation.params.get("target", "药物名称")
            return LLMExtractOperator(
                vllm_client=self.vllm_client,
                extract_target=target,
                output_field="medications",
                max_tokens=300,
                temperature=0.2
            )
        
        # 其他算子
        operator_class = self.operator_registry.get(operator_name)
        if operator_class:
            return operator_class()
        
        raise ValueError(f"未知的算子: {operator_name}")
    
    def execute(self, pipeline: Pipeline, input_data: Any = None) -> Any:
        """
        执行 pipeline。
        
        Args:
            pipeline: Pipeline 配置
            input_data: 输入数据（可选）
        
        Returns:
            输出数据
        """
        start_time = time.time()
        
        # 执行流程
        data = input_data
        total_tokens = 0
        
        print(f"\n{'='*70}")
        print(f"开始执行 Pipeline: {pipeline.name}")
        print(f"{'='*70}\n")
        
        for i, operation in enumerate(pipeline.operations):
            op_start = time.time()
            
            print(f"[{i+1}/{len(pipeline.operations)}] 执行操作: {operation.name} ({operation.selected_operator})")
            
            # 实例化算子
            operator = self._instantiate_operator(operation)
            
            # 执行算子
            data = operator.execute(data)
            
            op_time = time.time() - op_start
            
            # 统计 tokens（如果是 LLM 算子）
            if hasattr(operator, 'total_tokens'):
                op_tokens = operator.total_tokens
                total_tokens += op_tokens
                print(f"   ✓ 完成，耗时 {op_time:.2f}s，使用 {op_tokens} tokens，输出 {len(data)} 条")
            else:
                print(f"   ✓ 完成，耗时 {op_time:.2f}s，输出 {len(data)} 条")
        
        execution_time = time.time() - start_time
        
        # 计算成本（简化：假设每 1000 tokens = $0.001）
        cost = (total_tokens / 1000.0) * 0.001
        
        print(f"\n{'='*70}")
        print(f"Pipeline 执行完成")
        print(f"   总耗时: {execution_time:.2f}s")
        print(f"   总 tokens: {total_tokens}")
        print(f"   总成本: ${cost:.6f}")
        print(f"   最终输出: {len(data)} 条数据")
        print(f"{'='*70}\n")
        
        # 记录指标
        self.last_metrics = ExecutionMetrics(
            accuracy=0.0,  # 需要评估器计算
            tokens=total_tokens,
            execution_time=execution_time,
            cost=cost
        )
        
        return data
    
    def get_metrics(self) -> ExecutionMetrics:
        """获取最近一次执行的指标"""
        if self.last_metrics is None:
            raise RuntimeError("尚未执行任何 pipeline")
        return self.last_metrics
