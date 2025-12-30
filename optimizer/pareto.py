"""
Pareto 前沿管理

管理多目标优化的 Pareto 最优解集合。
借鉴 DocETL 的 ParetoFrontier 设计，支持三目标优化。
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from planner.core.node import Node, ExecutionMetrics


@dataclass
class ParetoPoint:
    """
    Pareto 前沿上的一个点。
    
    Attributes:
        node: 对应的搜索树节点
        accuracy: 精度
        tokens: token 数量
        execution_time: 执行时间
        cost: 成本
    """
    node: Node
    accuracy: float
    tokens: int
    execution_time: float
    cost: float
    
    def dominates(self, other: "ParetoPoint") -> bool:
        """
        判断当前点是否 Pareto 支配另一个点。
        
        对于三目标优化（精度最大化、tokens最小化、时间最小化）：
        当前点支配 other，当且仅当：
        - accuracy >= other.accuracy
        - tokens <= other.tokens
        - execution_time <= other.execution_time
        - 至少有一个严格更优
        
        Args:
            other: 另一个点
        
        Returns:
            是否支配
        """
        # 检查是否在所有维度上都不差
        if (self.accuracy < other.accuracy or 
            self.tokens > other.tokens or 
            self.execution_time > other.execution_time):
            return False
        
        # 检查是否至少有一个维度严格更优
        return (self.accuracy > other.accuracy or 
                self.tokens < other.tokens or 
                self.execution_time < other.execution_time)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "pipeline": str(self.node.pipeline),
            "pipeline_config": self.node.pipeline.to_dict(),
            "accuracy": self.accuracy,
            "tokens": self.tokens,
            "execution_time": self.execution_time,
            "cost": self.cost,
            "node_id": self.node.get_id()
        }


class ParetoFrontier:
    """
    Pareto 前沿管理器。
    
    维护一个 Pareto 最优解的集合，支持三目标优化：
    - 最大化精度
    - 最小化 tokens
    - 最小化执行时间
    """
    
    def __init__(self):
        """初始化 Pareto 前沿"""
        self.points: List[ParetoPoint] = []
        self.node_to_point: Dict[str, ParetoPoint] = {}
    
    def add_node(self, node: Node) -> bool:
        """
        尝试将节点添加到 Pareto 前沿。
        
        Args:
            node: 搜索树节点
        
        Returns:
            是否成功添加（True）或被支配（False）
        """
        if not node.is_evaluated or node.evaluation_failed or node.metrics is None:
            return False
        
        metrics = node.metrics
        new_point = ParetoPoint(
            node=node,
            accuracy=metrics.accuracy,
            tokens=metrics.tokens,
            execution_time=metrics.execution_time,
            cost=metrics.cost
        )
        
        # 检查是否被现有点支配
        dominated_by_existing = False
        points_to_remove = []
        
        for existing_point in self.points:
            if existing_point.dominates(new_point):
                dominated_by_existing = True
                break
            elif new_point.dominates(existing_point):
                points_to_remove.append(existing_point)
        
        if dominated_by_existing:
            return False
        
        # 移除被新点支配的点
        for point in points_to_remove:
            self.points.remove(point)
            del self.node_to_point[point.node.get_id()]
        
        # 添加新点
        self.points.append(new_point)
        self.node_to_point[node.get_id()] = new_point
        
        return True
    
    def get_sorted_by_accuracy(self) -> List[ParetoPoint]:
        """按精度排序返回点列表（降序）"""
        return sorted(self.points, key=lambda p: p.accuracy, reverse=True)
    
    def get_sorted_by_cost(self) -> List[ParetoPoint]:
        """按成本排序返回点列表（升序）"""
        return sorted(self.points, key=lambda p: p.cost)
    
    def get_sorted_by_tokens(self) -> List[ParetoPoint]:
        """按 tokens 排序返回点列表（升序）"""
        return sorted(self.points, key=lambda p: p.tokens)
    
    def get_sorted_by_time(self) -> List[ParetoPoint]:
        """按执行时间排序返回点列表（升序）"""
        return sorted(self.points, key=lambda p: p.execution_time)
    
    def get_best_accuracy(self) -> Optional[ParetoPoint]:
        """获取精度最高的点"""
        if not self.points:
            return None
        return max(self.points, key=lambda p: p.accuracy)
    
    def get_lowest_cost(self) -> Optional[ParetoPoint]:
        """获取成本最低的点"""
        if not self.points:
            return None
        return min(self.points, key=lambda p: p.cost)
    
    def get_fastest(self) -> Optional[ParetoPoint]:
        """获取执行最快的点"""
        if not self.points:
            return None
        return min(self.points, key=lambda p: p.execution_time)
    
    def get_balanced(self) -> Optional[ParetoPoint]:
        """
        获取平衡点（基于归一化的综合得分）。
        
        Returns:
            综合得分最高的点
        """
        if not self.points:
            return None
        
        # 归一化各指标
        if len(self.points) == 1:
            return self.points[0]
        
        accuracies = [p.accuracy for p in self.points]
        tokens_list = [p.tokens for p in self.points]
        times = [p.execution_time for p in self.points]
        
        max_accuracy = max(accuracies)
        min_accuracy = min(accuracies)
        max_tokens = max(tokens_list)
        min_tokens = min(tokens_list)
        max_time = max(times)
        min_time = min(times)
        
        def normalize(value, min_val, max_val, maximize=True):
            if max_val == min_val:
                return 1.0
            normalized = (value - min_val) / (max_val - min_val)
            return normalized if maximize else (1 - normalized)
        
        # 计算综合得分（等权重）
        best_score = -float('inf')
        best_point = None
        
        for point in self.points:
            score = (
                normalize(point.accuracy, min_accuracy, max_accuracy, maximize=True) +
                normalize(point.tokens, min_tokens, max_tokens, maximize=False) +
                normalize(point.execution_time, min_time, max_time, maximize=False)
            ) / 3.0
            
            if score > best_score:
                best_score = score
                best_point = point
        
        return best_point
    
    def size(self) -> int:
        """返回 Pareto 前沿上的点数"""
        return len(self.points)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "size": self.size(),
            "points": [p.to_dict() for p in self.get_sorted_by_accuracy()],
            "best_accuracy": self.get_best_accuracy().to_dict() if self.get_best_accuracy() else None,
            "lowest_cost": self.get_lowest_cost().to_dict() if self.get_lowest_cost() else None,
            "fastest": self.get_fastest().to_dict() if self.get_fastest() else None,
            "balanced": self.get_balanced().to_dict() if self.get_balanced() else None
        }
    
    def __len__(self) -> int:
        return len(self.points)
    
    def __repr__(self) -> str:
        return f"ParetoFrontier(size={self.size()})"
