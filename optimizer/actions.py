"""
优化动作定义

定义可以对 pipeline 进行的优化动作。
"""

from typing import List, Callable
from planner.core.pipeline import Pipeline, Operation
from planner.core.node import Node
import random


class OptimizationAction:
    """
    优化动作基类。
    
    每个动作可以从一个 pipeline 生成一个或多个新的 pipeline 配置。
    """
    
    def __init__(self, name: str, description: str):
        """
        初始化优化动作。
        
        Args:
            name: 动作名称
            description: 动作描述
        """
        self.name = name
        self.description = description
    
    def apply(self, pipeline: Pipeline) -> List[Pipeline]:
        """
        对 pipeline 应用优化动作。
        
        Args:
            pipeline: 原始 pipeline
        
        Returns:
            生成的新 pipeline 列表
        """
        raise NotImplementedError
    
    def is_applicable(self, pipeline: Pipeline) -> bool:
        """
        判断动作是否可应用于给定 pipeline。
        
        Args:
            pipeline: Pipeline 实例
        
        Returns:
            是否可应用
        """
        return True


class SwitchOperatorAction(OptimizationAction):
    """
    切换操作的算子。
    
    例如：将某个 map 操作的模型从 gpt-4o-mini 切换到 gpt-4o。
    """
    
    def __init__(self):
        super().__init__(
            name="switch_operator",
            description="切换操作的算子（如更换 LLM 模型）"
        )
    
    def apply(self, pipeline: Pipeline) -> List[Pipeline]:
        """生成切换算子的 pipeline 变体"""
        variants = []
        
        for i, operation in enumerate(pipeline.operations):
            # 对于每个有多个候选算子的操作
            if len(operation.candidates) > 1:
                for candidate in operation.candidates:
                    # 跳过当前已选择的算子
                    if candidate == operation.selected_operator:
                        continue
                    
                    # 创建新的 pipeline
                    new_pipeline = pipeline.clone()
                    new_op = new_pipeline.operations[i]
                    new_op.selected_operator = candidate
                    
                    variants.append(new_pipeline)
        
        return variants
    
    def is_applicable(self, pipeline: Pipeline) -> bool:
        """检查是否有操作可以切换算子"""
        return any(len(op.candidates) > 1 for op in pipeline.operations)


class ReorderOperationsAction(OptimizationAction):
    """
    重排相邻操作的顺序。
    
    例如：将 filter 移到 map 之前（谓词下推）。
    """
    
    def __init__(self):
        super().__init__(
            name="reorder_operations",
            description="重排相邻操作的顺序（如谓词下推）"
        )
    
    def apply(self, pipeline: Pipeline) -> List[Pipeline]:
        """生成重排操作的 pipeline 变体"""
        variants = []
        
        # 尝试交换每对相邻操作
        for i in range(len(pipeline) - 1):
            op1 = pipeline[i]
            op2 = pipeline[i + 1]
            
            # 只有当交换有意义时才执行
            # 例如：filter 可以移到 map 之前
            if self._can_swap(op1, op2):
                new_pipeline = pipeline.clone()
                new_pipeline.swap_operations(i, i + 1)
                variants.append(new_pipeline)
        
        return variants
    
    def _can_swap(self, op1: Operation, op2: Operation) -> bool:
        """
        判断两个操作是否可以交换。
        
        简化规则：
        - filter 可以移到 map 之前（谓词下推）
        - transform 操作一般可以交换
        """
        # Filter 可以移到 map 之前
        if op2.op_type == "filter" and op1.op_type == "map":
            return True
        
        # 两个 transform 操作可以交换
        if op1.op_type == "transform" and op2.op_type == "transform":
            return True
        
        return False
    
    def is_applicable(self, pipeline: Pipeline) -> bool:
        """检查是否有相邻操作可以交换"""
        for i in range(len(pipeline) - 1):
            if self._can_swap(pipeline[i], pipeline[i + 1]):
                return True
        return False


class ParameterTuningAction(OptimizationAction):
    """
    调整操作参数。
    
    例如：调整 chunk_size、temperature 等参数。
    """
    
    def __init__(self):
        super().__init__(
            name="parameter_tuning",
            description="调整操作参数（如 chunk_size、temperature）"
        )
    
    def apply(self, pipeline: Pipeline) -> List[Pipeline]:
        """生成参数调整的 pipeline 变体"""
        variants = []
        
        for i, operation in enumerate(pipeline.operations):
            # 为有参数的操作生成变体
            if operation.params:
                # 这里简化实现，实际可以根据参数类型智能调整
                # 例如：temperature 从 0.3 调到 0.7
                new_pipeline = pipeline.clone()
                # 具体参数调整逻辑由用户扩展
                variants.append(new_pipeline)
        
        return variants
    
    def is_applicable(self, pipeline: Pipeline) -> bool:
        """检查是否有操作有可调参数"""
        return any(op.params for op in pipeline.operations)


class ActionGenerator:
    """
    动作生成器。
    
    根据当前 pipeline 状态，选择并应用优化动作。
    """
    
    def __init__(self):
        """初始化动作生成器"""
        self.actions: List[OptimizationAction] = [
            SwitchOperatorAction(),
            ReorderOperationsAction(),
            # ParameterTuningAction(),  # 可选
        ]
    
    def get_applicable_actions(self, pipeline: Pipeline) -> List[OptimizationAction]:
        """
        获取可应用于 pipeline 的动作列表。
        
        Args:
            pipeline: Pipeline 实例
        
        Returns:
            可应用的动作列表
        """
        return [action for action in self.actions if action.is_applicable(pipeline)]
    
    def generate_children(self, node: Node, max_children: int = 5) -> List[Node]:
        """
        为节点生成子节点。
        
        Args:
            node: 父节点
            max_children: 最大子节点数
        
        Returns:
            生成的子节点列表
        """
        pipeline = node.pipeline
        applicable_actions = self.get_applicable_actions(pipeline)
        
        if not applicable_actions:
            return []
        
        # 随机选择一个动作
        action = random.choice(applicable_actions)
        
        # 应用动作生成新 pipeline
        new_pipelines = action.apply(pipeline)
        
        # 限制子节点数量
        if len(new_pipelines) > max_children:
            new_pipelines = random.sample(new_pipelines, max_children)
        
        # 创建子节点
        children = []
        for new_pipeline in new_pipelines:
            child = Node(
                pipeline=new_pipeline,
                parent=node,
                action_description=f"{action.name}: {new_pipeline}"
            )
            children.append(child)
        
        return children
