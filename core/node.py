"""
搜索树节点定义

表示 MCTS 搜索树中的一个节点，对应一个 pipeline 配置。
借鉴 DocETL 的 Node 设计。
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import time
from planner.core.pipeline import Pipeline


@dataclass
class ExecutionMetrics:
    """
    Pipeline 执行的指标数据。
    
    Attributes:
        accuracy: 精度（0-1之间，越高越好）
        tokens: 使用的 token 数量
        execution_time: 执行时间（秒）
        cost: 成本（美元）
    """
    accuracy: float = 0.0
    tokens: int = 0
    execution_time: float = 0.0
    cost: float = 0.0
    
    def __repr__(self) -> str:
        return (
            f"Metrics(accuracy={self.accuracy:.3f}, "
            f"tokens={self.tokens}, "
            f"time={self.execution_time:.2f}s, "
            f"cost=${self.cost:.4f})"
        )


class Node:
    """
    MCTS 搜索树节点。
    
    每个节点表示一个 pipeline 配置的状态，包含：
    - pipeline: 当前的 pipeline 配置
    - metrics: 执行后的指标（accuracy, tokens, time）
    - visits: 访问次数（用于 UCB 计算）
    - parent: 父节点
    - children: 子节点列表
    """
    
    def __init__(
        self,
        pipeline: Pipeline,
        parent: Optional["Node"] = None,
        action_description: str = "root"
    ):
        """
        初始化节点。
        
        Args:
            pipeline: Pipeline 配置
            parent: 父节点
            action_description: 从父节点到此节点的动作描述
        """
        self.pipeline = pipeline
        self.parent = parent
        self.children: List[Node] = []
        self.action_description = action_description
        
        # MCTS 统计信息
        self.visits = 0
        self.total_reward = 0.0  # 累积奖励
        
        # 执行指标
        self.metrics: Optional[ExecutionMetrics] = None
        self.is_evaluated = False
        self.evaluation_failed = False
        
        # 时间戳
        self.created_at = time.time()
        self.evaluated_at: Optional[float] = None
        
    def get_id(self) -> str:
        """获取节点唯一标识"""
        return self.pipeline.get_hash()
    
    def add_child(self, child: "Node"):
        """添加子节点"""
        self.children.append(child)
        child.parent = self
    
    def is_leaf(self) -> bool:
        """判断是否为叶子节点"""
        return len(self.children) == 0
    
    def is_fully_expanded(self) -> bool:
        """
        判断节点是否已完全扩展。
        
        对于线性 pipeline，完全扩展意味着：
        - 已经尝试了所有操作的算子切换
        - 已经尝试了相邻操作的重排（如果适用）
        """
        # 简化实现：如果有子节点且访问次数 > 子节点数，认为已充分扩展
        return len(self.children) > 0 and self.visits > len(self.children) * 2
    
    def get_ucb_score(self, exploration_weight: float = 1.414) -> float:
        """
        计算 UCB (Upper Confidence Bound) 分数。
        
        UCB = average_reward + exploration_weight * sqrt(ln(parent_visits) / visits)
        
        Args:
            exploration_weight: 探索权重（c 参数）
        
        Returns:
            UCB 分数
        """
        if self.visits == 0:
            return float('inf')  # 未访问的节点优先
        
        if self.parent is None or self.parent.visits == 0:
            return self.total_reward / self.visits
        
        import math
        
        exploitation = self.total_reward / self.visits
        exploration = exploration_weight * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        
        return exploitation + exploration
    
    def update_metrics(self, metrics: ExecutionMetrics):
        """
        更新节点的执行指标。
        
        Args:
            metrics: 执行指标
        """
        self.metrics = metrics
        self.is_evaluated = True
        self.evaluated_at = time.time()
    
    def mark_evaluation_failed(self):
        """标记评估失败"""
        self.evaluation_failed = True
        self.is_evaluated = True
        self.metrics = ExecutionMetrics(
            accuracy=0.0,
            tokens=0,
            execution_time=0.0,
            cost=0.0
        )
    
    def backpropagate(self, reward: float):
        """
        回溯更新节点统计信息。
        
        Args:
            reward: 奖励值（基于多目标优化计算）
        """
        current = self
        while current is not None:
            current.visits += 1
            current.total_reward += reward
            current = current.parent
    
    def get_path_from_root(self) -> List["Node"]:
        """获取从根节点到当前节点的路径"""
        path = []
        current = self
        while current is not None:
            path.append(current)
            current = current.parent
        return list(reversed(path))
    
    def get_depth(self) -> int:
        """获取节点深度（根节点深度为 0）"""
        depth = 0
        current = self.parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.get_id(),
            "pipeline": self.pipeline.to_dict(),
            "action": self.action_description,
            "metrics": {
                "accuracy": self.metrics.accuracy if self.metrics else None,
                "tokens": self.metrics.tokens if self.metrics else None,
                "execution_time": self.metrics.execution_time if self.metrics else None,
                "cost": self.metrics.cost if self.metrics else None,
            } if self.is_evaluated else None,
            "visits": self.visits,
            "avg_reward": self.total_reward / self.visits if self.visits > 0 else 0,
            "depth": self.get_depth(),
            "is_leaf": self.is_leaf(),
            "num_children": len(self.children)
        }
    
    def __repr__(self) -> str:
        metrics_str = f" {self.metrics}" if self.metrics else ""
        return (
            f"Node(depth={self.get_depth()}, "
            f"visits={self.visits}, "
            f"action='{self.action_description}'"
            f"{metrics_str})"
        )
