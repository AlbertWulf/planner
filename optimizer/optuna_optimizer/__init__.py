"""
基于 Optuna 的 Pipeline 优化器

相比 MCTS+Pareto 前沿的方案，Optuna 提供了：
- 更简单的 API
- 更快的收敛速度
- 内置的多目标优化支持
- 自动 Pareto 前沿计算
- 丰富的可视化功能
"""

from .optimizer import OptunaOptimizer
from .visualizer import plot_pareto_front, plot_optimization_history

__all__ = [
    'OptunaOptimizer',
    'plot_pareto_front',
    'plot_optimization_history',
]
