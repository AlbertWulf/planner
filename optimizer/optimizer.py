"""
主优化器接口

整合 MCTS 搜索、Pareto 前沿管理和执行器。
"""

from typing import Callable, Optional, Any, Dict
from planner.core.pipeline import Pipeline
from planner.core.node import ExecutionMetrics
from planner.core.executor import (
    PipelineExecutor,
    Evaluator,
    MockExecutor,
    create_executor_func
)
from planner.optimizer.mcts import MCTSSearchEngine
from planner.optimizer.pareto import ParetoFrontier
import json
import os


class PipelineOptimizer:
    """
    Pipeline 优化器。
    
    整合 MCTS 搜索和 Pareto 前沿管理，提供简单的优化接口。
    """
    
    def __init__(
        self,
        pipeline: Pipeline,
        executor: Optional[PipelineExecutor] = None,
        evaluator: Optional[Evaluator] = None,
        input_data: Any = None,
        ground_truth: Any = None,
        max_iterations: int = 50,
        exploration_weight: float = 1.414,
        max_children_per_node: int = 5,
        save_dir: Optional[str] = None,
        verbose: bool = True
    ):
        """
        初始化优化器。
        
        Args:
            pipeline: 初始 pipeline 配置
            executor: Pipeline 执行器（默认使用 MockExecutor）
            evaluator: 精度评估器（可选）
            input_data: 输入数据
            ground_truth: 真实标签（用于评估）
            max_iterations: 最大搜索迭代次数
            exploration_weight: UCB 探索权重
            max_children_per_node: 每个节点最大子节点数
            save_dir: 结果保存目录
            verbose: 是否打印详细信息
        """
        self.pipeline = pipeline
        self.executor = executor or MockExecutor()
        self.evaluator = evaluator
        self.input_data = input_data
        self.ground_truth = ground_truth
        self.max_iterations = max_iterations
        self.exploration_weight = exploration_weight
        self.max_children_per_node = max_children_per_node
        self.save_dir = save_dir
        self.verbose = verbose
        
        # 创建执行器函数
        self.executor_func = create_executor_func(
            executor=self.executor,
            evaluator=self.evaluator,
            input_data=self.input_data,
            ground_truth=self.ground_truth
        )
        
        # MCTS 搜索引擎
        self.search_engine: Optional[MCTSSearchEngine] = None
        
        # Pareto 前沿
        self.pareto_frontier: Optional[ParetoFrontier] = None
    
    def optimize(self) -> ParetoFrontier:
        """
        运行优化。
        
        Returns:
            Pareto 前沿
        """
        # 创建搜索引擎
        self.search_engine = MCTSSearchEngine(
            root_pipeline=self.pipeline,
            executor_func=self.executor_func,
            max_iterations=self.max_iterations,
            exploration_weight=self.exploration_weight,
            max_children_per_node=self.max_children_per_node,
            verbose=self.verbose
        )
        
        # 执行搜索
        self.pareto_frontier = self.search_engine.search()
        
        # 保存结果
        if self.save_dir:
            self.save_results()
        
        return self.pareto_frontier
    
    def save_results(self):
        """保存优化结果"""
        if not self.save_dir:
            return
        
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 保存 Pareto 前沿
        pareto_file = os.path.join(self.save_dir, "pareto_frontier.json")
        with open(pareto_file, 'w', encoding='utf-8') as f:
            json.dump(self.pareto_frontier.to_dict(), f, indent=2, ensure_ascii=False)
        
        # 保存搜索统计
        stats_file = os.path.join(self.save_dir, "search_stats.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.search_engine.get_statistics(), f, indent=2)
        
        # 保存推荐方案
        self.save_recommendations()
        
        if self.verbose:
            print(f"\n✅ 结果已保存到: {self.save_dir}")
    
    def save_recommendations(self):
        """保存推荐方案"""
        if not self.pareto_frontier or not self.save_dir:
            return
        
        recommendations = {
            "best_accuracy": self.pareto_frontier.get_best_accuracy().to_dict() 
                if self.pareto_frontier.get_best_accuracy() else None,
            "lowest_cost": self.pareto_frontier.get_lowest_cost().to_dict() 
                if self.pareto_frontier.get_lowest_cost() else None,
            "fastest": self.pareto_frontier.get_fastest().to_dict() 
                if self.pareto_frontier.get_fastest() else None,
            "balanced": self.pareto_frontier.get_balanced().to_dict() 
                if self.pareto_frontier.get_balanced() else None,
        }
        
        rec_file = os.path.join(self.save_dir, "recommendations.json")
        with open(rec_file, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, indent=2, ensure_ascii=False)
    
    def print_summary(self):
        """打印优化结果摘要"""
        if not self.pareto_frontier:
            print("⚠️  未运行优化")
            return
        
        print(f"\n{'='*70}")
        print("📊 优化结果摘要")
        print(f"{'='*70}")
        
        print(f"\n🎯 Pareto 前沿大小: {self.pareto_frontier.size()} 个解")
        
        # 最佳精度
        best_acc = self.pareto_frontier.get_best_accuracy()
        if best_acc:
            print(f"\n🏆 最佳精度方案:")
            print(f"   Accuracy: {best_acc.accuracy:.3f}")
            print(f"   Tokens: {best_acc.tokens}")
            print(f"   Time: {best_acc.execution_time:.2f}s")
            print(f"   Cost: ${best_acc.cost:.4f}")
            print(f"   Pipeline: {best_acc.node.pipeline}")
        
        # 最低成本
        lowest_cost = self.pareto_frontier.get_lowest_cost()
        if lowest_cost:
            print(f"\n💰 最低成本方案:")
            print(f"   Accuracy: {lowest_cost.accuracy:.3f}")
            print(f"   Tokens: {lowest_cost.tokens}")
            print(f"   Time: {lowest_cost.execution_time:.2f}s")
            print(f"   Cost: ${lowest_cost.cost:.4f}")
            print(f"   Pipeline: {lowest_cost.node.pipeline}")
        
        # 最快执行
        fastest = self.pareto_frontier.get_fastest()
        if fastest:
            print(f"\n⚡ 最快执行方案:")
            print(f"   Accuracy: {fastest.accuracy:.3f}")
            print(f"   Tokens: {fastest.tokens}")
            print(f"   Time: {fastest.execution_time:.2f}s")
            print(f"   Cost: ${fastest.cost:.4f}")
            print(f"   Pipeline: {fastest.node.pipeline}")
        
        # 平衡方案
        balanced = self.pareto_frontier.get_balanced()
        if balanced:
            print(f"\n⚖️  平衡方案:")
            print(f"   Accuracy: {balanced.accuracy:.3f}")
            print(f"   Tokens: {balanced.tokens}")
            print(f"   Time: {balanced.execution_time:.2f}s")
            print(f"   Cost: ${balanced.cost:.4f}")
            print(f"   Pipeline: {balanced.node.pipeline}")
        
        print(f"\n{'='*70}")
