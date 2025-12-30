"""
MCTS (Monte Carlo Tree Search) 搜索引擎

借鉴 DocETL 的 MOARSearch 实现，用于探索 pipeline 配置空间。
"""

from typing import Optional, Callable, Dict, Any, List
import random
import time
from planner.core.pipeline import Pipeline
from planner.core.node import Node, ExecutionMetrics
from planner.optimizer.pareto import ParetoFrontier
from planner.optimizer.actions import ActionGenerator


class MCTSSearchEngine:
    """
    基于 MCTS 的 pipeline 优化搜索引擎。
    
    核心流程：
    1. Selection: 从根节点选择最有希望的叶子节点
    2. Expansion: 扩展该节点，生成子节点
    3. Simulation: 执行 pipeline 并评估
    4. Backpropagation: 回溯更新节点统计信息
    """
    
    def __init__(
        self,
        root_pipeline: Pipeline,
        executor_func: Callable[[Pipeline], ExecutionMetrics],
        max_iterations: int = 50,
        exploration_weight: float = 1.414,
        max_children_per_node: int = 5,
        verbose: bool = True
    ):
        """
        初始化 MCTS 搜索引擎。
        
        Args:
            root_pipeline: 初始 pipeline 配置
            executor_func: 执行器函数，接收 Pipeline，返回 ExecutionMetrics
            max_iterations: 最大搜索迭代次数
            exploration_weight: UCB 探索权重
            max_children_per_node: 每个节点最大子节点数
            verbose: 是否打印详细信息
        """
        self.root = Node(pipeline=root_pipeline, action_description="root")
        self.executor_func = executor_func
        self.max_iterations = max_iterations
        self.exploration_weight = exploration_weight
        self.max_children_per_node = max_children_per_node
        self.verbose = verbose
        
        # 搜索统计
        self.iteration_count = 0
        self.total_evaluations = 0
        self.start_time = 0.0
        
        # Pareto 前沿
        self.pareto_frontier = ParetoFrontier()
        
        # 动作生成器
        self.action_generator = ActionGenerator()
        
        # 已访问节点（去重）
        self.visited_pipeline_hashes = set()
    
    def search(self) -> ParetoFrontier:
        """
        执行 MCTS 搜索。
        
        Returns:
            Pareto 前沿
        """
        self.start_time = time.time()
        self.log("🚀 开始 MCTS 搜索...")
        
        # 评估根节点
        self.log("📊 评估初始 pipeline...")
        self._simulate(self.root)
        self.pareto_frontier.add_node(self.root)
        
        # 迭代搜索
        for iteration in range(self.max_iterations):
            self.iteration_count = iteration + 1
            
            self.log(f"\n{'='*60}")
            self.log(f"🔍 迭代 {self.iteration_count}/{self.max_iterations}")
            
            # 1. Selection: 选择最有希望的节点
            selected_node = self._select(self.root)
            
            if selected_node is None:
                self.log("⚠️  无法选择节点，搜索结束")
                break
            
            self.log(f"✓ 选中节点: depth={selected_node.get_depth()}, "
                    f"visits={selected_node.visits}")
            
            # 2. Expansion: 扩展节点
            children = self._expand(selected_node)
            
            if not children:
                self.log("⚠️  无法扩展节点，标记为已访问")
                # 即使无法生成子节点，也要增加 visits，避免下次再次选中
                selected_node.visits += 1
                continue
            
            self.log(f"✓ 生成 {len(children)} 个子节点")
            
            # 3. Simulation: 随机选择一个子节点进行评估
            child_to_simulate = random.choice(children)
            self.log(f"✓ 选择子节点进行模拟: {child_to_simulate.action_description[:50]}")
            
            metrics = self._simulate(child_to_simulate)
            
            if metrics:
                # 4. Backpropagation: 回溯更新
                reward = self._calculate_reward(metrics)
                child_to_simulate.backpropagate(reward)
                
                # 尝试添加到 Pareto 前沿
                if self.pareto_frontier.add_node(child_to_simulate):
                    self.log(f"✨ 新 Pareto 点! Accuracy={metrics.accuracy:.3f}, "
                            f"Tokens={metrics.tokens}, Time={metrics.execution_time:.2f}s")
            
            # 输出当前状态
            elapsed = time.time() - self.start_time
            self.log(f"\n📈 当前统计:")
            self.log(f"   - Pareto 前沿大小: {self.pareto_frontier.size()}")
            self.log(f"   - 总评估次数: {self.total_evaluations}")
            self.log(f"   - 已用时间: {elapsed:.1f}s")
        
        self.log(f"\n{'='*60}")
        self.log(f"✅ 搜索完成!")
        self.log(f"   - 总迭代: {self.iteration_count}")
        self.log(f"   - Pareto 前沿: {self.pareto_frontier.size()} 个解")
        self.log(f"   - 总时间: {time.time() - self.start_time:.1f}s")
        
        return self.pareto_frontier
    
    def _select(self, node: Node) -> Optional[Node]:
        """
        Selection 阶段: 使用 UCB 选择最有希望的叶子节点。
        
        Args:
            node: 起始节点
        
        Returns:
            选中的叶子节点
        """
        current = node
        
        while not current.is_leaf():
            # 如果节点未完全扩展，返回它
            if not current.is_fully_expanded():
                return current
            
            # 选择 UCB 分数最高的子节点
            current = max(
                current.children,
                key=lambda c: c.get_ucb_score(self.exploration_weight)
            )
        
        return current
    
    def _expand(self, node: Node) -> List[Node]:
        """
        Expansion 阶段: 生成子节点。
        
        Args:
            node: 要扩展的节点
        
        Returns:
            生成的子节点列表
        """
        # 使用动作生成器创建子节点
        children = self.action_generator.generate_children(
            node,
            max_children=self.max_children_per_node
        )
        
        # 过滤已访问的 pipeline
        unique_children = []
        for child in children:
            pipeline_hash = child.pipeline.get_hash()
            if pipeline_hash not in self.visited_pipeline_hashes:
                self.visited_pipeline_hashes.add(pipeline_hash)
                unique_children.append(child)
                node.add_child(child)
        
        return unique_children
    
    def _simulate(self, node: Node) -> Optional[ExecutionMetrics]:
        """
        Simulation 阶段: 执行 pipeline 并评估。
        
        Args:
            node: 要评估的节点
        
        Returns:
            执行指标
        """
        if node.is_evaluated:
            return node.metrics
        
        try:
            # 执行 pipeline
            metrics = self.executor_func(node.pipeline)
            node.update_metrics(metrics)
            self.total_evaluations += 1
            
            return metrics
        
        except Exception as e:
            self.log(f"❌ 执行失败: {e}")
            node.mark_evaluation_failed()
            return None
    
    def _calculate_reward(self, metrics: ExecutionMetrics) -> float:
        """
        计算奖励值（用于回溯）。
        
        对于三目标优化，使用加权和：
        reward = w1 * accuracy - w2 * normalized_tokens - w3 * normalized_time
        
        Args:
            metrics: 执行指标
        
        Returns:
            奖励值
        """
        # 简化实现：等权重归一化
        # 实际应用中可以根据目标优先级调整权重
        
        # 精度贡献（0-1）
        accuracy_reward = metrics.accuracy
        
        # Token 惩罚（归一化到 0-1）
        # 假设 10000 tokens 为基准
        token_penalty = min(metrics.tokens / 10000.0, 1.0)
        
        # 时间惩罚（归一化到 0-1）
        # 假设 60 秒为基准
        time_penalty = min(metrics.execution_time / 60.0, 1.0)
        
        # 综合奖励（精度权重更高）
        reward = (
            2.0 * accuracy_reward -
            0.5 * token_penalty -
            0.5 * time_penalty
        )
        
        return reward
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        return {
            "iterations": self.iteration_count,
            "total_evaluations": self.total_evaluations,
            "pareto_size": self.pareto_frontier.size(),
            "elapsed_time": time.time() - self.start_time,
            "root_visits": self.root.visits
        }
    
    def log(self, message: str):
        """打印日志"""
        if self.verbose:
            print(message)
