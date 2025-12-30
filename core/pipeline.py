"""
Pipeline 和 Operation 定义

定义线性 pipeline 的数据结构和操作符表示。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import hashlib
import json


@dataclass
class Operation:
    """
    Pipeline 中的单个操作。
    
    Attributes:
        name: 操作名称（如 "map", "filter", "chunk"）
        op_type: 操作类型（"map", "reduce", "filter", "transform"）
        prompt: LLM 操作的提示词（可选）
        candidates: 候选算子列表（如 ["gpt-4o", "gpt-4o-mini", "claude"]）
        selected_operator: 当前选择的算子
        params: 操作的额外参数
    """
    name: str
    op_type: str
    candidates: List[str]
    prompt: Optional[str] = None
    selected_operator: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后，如果没有选择算子，默认选择第一个候选"""
        if self.selected_operator is None and self.candidates:
            self.selected_operator = self.candidates[0]
    
    def clone(self) -> "Operation":
        """克隆操作"""
        return Operation(
            name=self.name,
            op_type=self.op_type,
            candidates=self.candidates.copy(),
            prompt=self.prompt,
            selected_operator=self.selected_operator,
            params=self.params.copy()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "op_type": self.op_type,
            "prompt": self.prompt,
            "selected_operator": self.selected_operator,
            "params": self.params,
            "candidates": self.candidates
        }
    
    def get_hash(self) -> str:
        """获取操作的哈希值（用于去重）"""
        key_data = {
            "name": self.name,
            "op_type": self.op_type,
            "prompt": self.prompt,
            "selected_operator": self.selected_operator,
            "params": self.params
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()


@dataclass
class Pipeline:
    """
    线性 Pipeline 定义。
    
    Attributes:
        operations: 操作列表（顺序执行）
        name: Pipeline 名称
        metadata: 额外元数据
    """
    operations: List[Operation]
    name: str = "pipeline"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def clone(self) -> "Pipeline":
        """克隆 pipeline"""
        return Pipeline(
            operations=[op.clone() for op in self.operations],
            name=self.name,
            metadata=self.metadata.copy()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "operations": [op.to_dict() for op in self.operations],
            "metadata": self.metadata
        }
    
    def get_hash(self) -> str:
        """获取 pipeline 的哈希值"""
        ops_hash = "".join([op.get_hash() for op in self.operations])
        return hashlib.md5(ops_hash.encode()).hexdigest()
    
    def get_operation_by_name(self, name: str) -> Optional[Operation]:
        """根据名称获取操作"""
        for op in self.operations:
            if op.name == name:
                return op
        return None
    
    def replace_operation(self, index: int, new_operation: Operation):
        """替换指定位置的操作"""
        if 0 <= index < len(self.operations):
            self.operations[index] = new_operation
    
    def swap_operations(self, idx1: int, idx2: int):
        """交换两个操作的位置（用于操作重排优化）"""
        if 0 <= idx1 < len(self.operations) and 0 <= idx2 < len(self.operations):
            self.operations[idx1], self.operations[idx2] = (
                self.operations[idx2],
                self.operations[idx1]
            )
    
    def __len__(self) -> int:
        return len(self.operations)
    
    def __getitem__(self, index: int) -> Operation:
        return self.operations[index]
    
    def __repr__(self) -> str:
        ops_str = " -> ".join([
            f"{op.name}({op.selected_operator})" 
            for op in self.operations
        ])
        return f"Pipeline({ops_str})"


def create_llm_operation(
    name: str,
    prompt: str,
    candidates: List[str] = None,
    op_type: str = "map"
) -> Operation:
    """
    创建 LLM 操作的便捷函数。
    
    Args:
        name: 操作名称
        prompt: LLM 提示词
        candidates: 候选模型列表
        op_type: 操作类型
    
    Returns:
        Operation 对象
    """
    if candidates is None:
        candidates = ["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-20241022"]
    
    return Operation(
        name=name,
        op_type=op_type,
        prompt=prompt,
        candidates=candidates
    )


def create_transform_operation(
    name: str,
    candidates: List[str],
    params: Dict[str, Any] = None
) -> Operation:
    """
    创建数据转换操作的便捷函数。
    
    Args:
        name: 操作名称
        candidates: 候选算子列表
        params: 操作参数
    
    Returns:
        Operation 对象
    """
    return Operation(
        name=name,
        op_type="transform",
        candidates=candidates,
        params=params or {}
    )
