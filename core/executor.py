"""
Pipeline 执行器和评估器

提供 pipeline 执行和精度评估的接口。
"""

from typing import Callable, Any, Dict, List
from abc import ABC, abstractmethod
from planner.core.pipeline import Pipeline, Operation
from planner.core.node import ExecutionMetrics
import time


class PipelineExecutor(ABC):
    """
    Pipeline 执行器基类。
    
    子类需要实现具体的执行逻辑。
    """
    
    @abstractmethod
    def execute(self, pipeline: Pipeline, input_data: Any) -> Any:
        """
        执行 pipeline。
        
        Args:
            pipeline: Pipeline 配置
            input_data: 输入数据
        
        Returns:
            输出数据
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> ExecutionMetrics:
        """
        获取最近一次执行的指标。
        
        Returns:
            执行指标
        """
        pass


class MockExecutor(PipelineExecutor):
    """
    模拟执行器（用于测试和演示）。
    
    根据 pipeline 配置模拟执行并生成指标。
    """
    
    def __init__(self):
        """初始化模拟执行器"""
        self.last_metrics: Optional[ExecutionMetrics] = None
        
        # 模型成本配置（每 1000 tokens 的价格）
        self.model_costs = {
            "gpt-4o": 0.005,
            "gpt-4o-mini": 0.0005,
            "claude-3-5-sonnet-20241022": 0.003,
            "gpt-3.5-turbo": 0.0005,
            "rule_based": 0.0,  # 规则不用钱
        }
        
        # 模型精度基准（模拟值）
        self.model_accuracy = {
            "gpt-4o": 0.92,
            "gpt-4o-mini": 0.85,
            "claude-3-5-sonnet-20241022": 0.90,
            "gpt-3.5-turbo": 0.80,
            "rule_based": 0.70,
        }
    
    def execute(self, pipeline: Pipeline, input_data: Any = None) -> Any:
        """
        模拟执行 pipeline。
        
        Args:
            pipeline: Pipeline 配置
            input_data: 输入数据（未使用）
        
        Returns:
            模拟输出
        """
        start_time = time.time()
        
        total_tokens = 0
        total_cost = 0.0
        accuracy_scores = []
        
        # 模拟每个操作
        for operation in pipeline.operations:
            operator = operation.selected_operator
            
            # 根据操作类型模拟 token 使用
            if operation.op_type in ["map", "filter"]:
                # LLM 操作
                base_tokens = 500
                tokens = base_tokens + len(operation.prompt or "") * 2
                
                cost_per_1k = self.model_costs.get(operator, 0.001)
                op_cost = (tokens / 1000.0) * cost_per_1k
                
                total_tokens += tokens
                total_cost += op_cost
                
                # 模拟精度
                base_accuracy = self.model_accuracy.get(operator, 0.75)
                accuracy_scores.append(base_accuracy)
                
            elif operation.op_type == "transform":
                # 非 LLM 操作，tokens 很少
                total_tokens += 50
        
        # 计算总精度（平均）
        if accuracy_scores:
            avg_accuracy = sum(accuracy_scores) / len(accuracy_scores)
        else:
            avg_accuracy = 0.8
        
        # 添加一些随机性
        import random
        avg_accuracy += random.uniform(-0.05, 0.05)
        avg_accuracy = max(0.0, min(1.0, avg_accuracy))
        
        execution_time = time.time() - start_time + random.uniform(0.1, 0.5)
        
        # 记录指标
        self.last_metrics = ExecutionMetrics(
            accuracy=avg_accuracy,
            tokens=total_tokens,
            execution_time=execution_time,
            cost=total_cost
        )
        
        return {"result": "mock_output", "metrics": self.last_metrics}
    
    def get_metrics(self) -> ExecutionMetrics:
        """获取最近一次执行的指标"""
        if self.last_metrics is None:
            raise RuntimeError("No execution has been performed yet")
        return self.last_metrics


class Evaluator:
    """
    精度评估器。
    
    用户需要提供评估函数来计算 pipeline 输出的精度。
    """
    
    def __init__(self, eval_func: Callable[[Any, Any], float]):
        """
        初始化评估器。
        
        Args:
            eval_func: 评估函数，接收 (ground_truth, predictions)，返回精度分数
        """
        self.eval_func = eval_func
    
    def evaluate(self, ground_truth: Any, predictions: Any) -> float:
        """
        评估精度。
        
        Args:
            ground_truth: 真实标签
            predictions: 预测结果
        
        Returns:
            精度分数（0-1之间）
        """
        try:
            accuracy = self.eval_func(ground_truth, predictions)
            return max(0.0, min(1.0, accuracy))  # 确保在 [0, 1] 范围内
        except Exception as e:
            print(f"评估失败: {e}")
            return 0.0


def create_executor_func(
    executor: PipelineExecutor,
    evaluator: Optional[Evaluator] = None,
    input_data: Any = None,
    ground_truth: Any = None
) -> Callable[[Pipeline], ExecutionMetrics]:
    """
    创建执行器函数（用于 MCTS 搜索）。
    
    Args:
        executor: Pipeline 执行器
        evaluator: 精度评估器（可选）
        input_data: 输入数据
        ground_truth: 真实标签（用于评估）
    
    Returns:
        执行器函数
    """
    def executor_func(pipeline: Pipeline) -> ExecutionMetrics:
        """执行 pipeline 并返回指标"""
        # 执行 pipeline
        output = executor.execute(pipeline, input_data)
        metrics = executor.get_metrics()
        
        # 如果提供了评估器，计算真实精度
        if evaluator and ground_truth is not None:
            true_accuracy = evaluator.evaluate(ground_truth, output)
            metrics.accuracy = true_accuracy
        
        return metrics
    
    return executor_func
