"""
基于 Optuna 的 Pipeline 优化器实现
"""

from typing import Callable, List, Dict, Any, Tuple, Optional
import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner
import json
import os
import time
from pathlib import Path

import sys
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from planner.core.pipeline import Pipeline, Operation
from planner.core.executor import PipelineExecutor, ExecutionMetrics


class OptunaOptimizer:
    """
    基于 Optuna 的 Pipeline 优化器。
    
    使用 Optuna 的多目标优化功能，自动搜索最优的算子配置。
    相比 MCTS+Pareto，实现更简单，收敛更快。
    
    特点：
    - 自动多目标优化（精度↑、tokens↓、时间↓）
    - 内置 Pareto 前沿计算
    - 支持并行优化
    - 丰富的采样算法（TPE、Grid、Random 等）
    - 自动剪枝加速收敛
    """
    
    def __init__(
        self,
        pipeline: Pipeline,
        executor: PipelineExecutor,
        evaluator: Optional[Callable] = None,
        n_trials: int = 50,
        n_jobs: int = 1,
        save_dir: str = None,
        verbose: bool = True
    ):
        """
        初始化 Optuna 优化器。
        
        Args:
            pipeline: 初始 pipeline 配置（作为模板）
            executor: Pipeline 执行器
            evaluator: 评估函数，用于计算精度（可选）
            n_trials: 优化试验次数
            n_jobs: 并行任务数（1=串行）
            save_dir: 结果保存目录
            verbose: 是否打印详细信息
        """
        self.template_pipeline = pipeline
        self.executor = executor
        self.evaluator = evaluator
        self.n_trials = n_trials
        self.n_jobs = n_jobs
        self.save_dir = save_dir
        self.verbose = verbose
        
        # 设置日志级别
        if not verbose:
            optuna.logging.set_verbosity(optuna.logging.WARNING)
        
        # 创建 Optuna study（多目标优化）
        sampler = TPESampler(seed=42, n_startup_trials=10)  # 使用 TPE 采样器
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=3)  # 使用中位数剪枝器
        
        self.study = optuna.create_study(
            directions=["maximize", "minimize", "minimize"],  # [精度↑, tokens↓, 时间↓]
            sampler=sampler,
            pruner=pruner,
            study_name="pipeline_optimization"
        )
        
        # 记录所有试验的结果
        self.trial_results: List[Dict] = []
        self.start_time = None
    
    def _suggest_pipeline(self, trial: optuna.Trial) -> Pipeline:
        """
        使用 Optuna 的 suggest API 生成 pipeline 配置。
        
        Args:
            trial: Optuna trial 对象
        
        Returns:
            生成的 pipeline 配置
        """
        new_pipeline = self.template_pipeline.clone()
        
        # 为每个操作选择算子
        for i, operation in enumerate(new_pipeline.operations):
            if len(operation.candidates) > 1:
                # 使用 trial.suggest_categorical 选择算子
                selected = trial.suggest_categorical(
                    f"op_{i}_{operation.name}_operator",
                    operation.candidates
                )
                operation.selected_operator = selected
        
        return new_pipeline
    
    def _objective(self, trial: optuna.Trial) -> Tuple[float, int, float]:
        """
        Optuna 的目标函数。
        
        Args:
            trial: Optuna trial 对象
        
        Returns:
            (accuracy, tokens, execution_time) 元组
        """
        # 生成 pipeline 配置
        pipeline = self._suggest_pipeline(trial)
        
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"[Trial {trial.number + 1}/{self.n_trials}] 测试配置:")
            for i, op in enumerate(pipeline.operations):
                print(f"  {i+1}. {op.name}: {op.selected_operator}")
        
        try:
            # 执行 pipeline
            result = self.executor.execute(pipeline)
            metrics = self.executor.last_metrics
            
            if metrics is None:
                raise ValueError("执行器未返回指标")
            
            # 计算精度
            if self.evaluator:
                accuracy = self.evaluator(result)
            else:
                accuracy = metrics.accuracy
            
            # 记录结果
            trial_record = {
                "trial_number": trial.number,
                "pipeline": str(pipeline),
                "accuracy": accuracy,
                "tokens": metrics.tokens,
                "execution_time": metrics.execution_time,
                "cost": metrics.cost
            }
            self.trial_results.append(trial_record)
            
            if self.verbose:
                print(f"  ✓ 精度: {accuracy:.3f}")
                print(f"  ✓ Tokens: {metrics.tokens}")
                print(f"  ✓ 时间: {metrics.execution_time:.2f}s")
                print(f"  ✓ 成本: ${metrics.cost:.4f}")
            
            return accuracy, metrics.tokens, metrics.execution_time
        
        except Exception as e:
            if self.verbose:
                print(f"  ✗ 执行失败: {e}")
            # 返回最差的指标
            return 0.0, 999999, 999999.0
    
    def optimize(self) -> List[optuna.trial.FrozenTrial]:
        """
        执行优化过程。
        
        Returns:
            Pareto 前沿上的试验列表
        """
        self.start_time = time.time()
        
        if self.verbose:
            print("="*70)
            print("🚀 开始 Optuna 多目标优化")
            print("="*70)
            print(f"优化目标: 精度↑, Tokens↓, 时间↓")
            print(f"试验次数: {self.n_trials}")
            print(f"并行任务: {self.n_jobs}")
            print("="*70)
        
        # 运行优化
        self.study.optimize(
            self._objective,
            n_trials=self.n_trials,
            n_jobs=self.n_jobs,
            show_progress_bar=self.verbose
        )
        
        # 获取 Pareto 前沿
        pareto_trials = self.study.best_trials
        
        elapsed = time.time() - self.start_time
        
        if self.verbose:
            print("\n" + "="*70)
            print("✨ 优化完成!")
            print("="*70)
            print(f"总耗时: {elapsed:.1f}s")
            print(f"完成试验: {len(self.study.trials)}")
            print(f"Pareto 前沿大小: {len(pareto_trials)}")
        
        # 保存结果
        if self.save_dir:
            self._save_results(pareto_trials)
        
        return pareto_trials
    
    def _save_results(self, pareto_trials: List[optuna.trial.FrozenTrial]):
        """保存优化结果"""
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 保存所有试验结果
        results_file = os.path.join(self.save_dir, "optuna_trials.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.trial_results, f, indent=2, ensure_ascii=False)
        
        # 保存 Pareto 前沿
        pareto_data = []
        for trial in pareto_trials:
            pareto_data.append({
                "trial_number": trial.number,
                "params": trial.params,
                "values": {
                    "accuracy": trial.values[0],
                    "tokens": trial.values[1],
                    "execution_time": trial.values[2]
                }
            })
        
        pareto_file = os.path.join(self.save_dir, "pareto_front.json")
        with open(pareto_file, 'w', encoding='utf-8') as f:
            json.dump(pareto_data, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"\n✓ 结果已保存到: {self.save_dir}")
            print(f"  - 所有试验: {results_file}")
            print(f"  - Pareto 前沿: {pareto_file}")
    
    def print_summary(self):
        """打印优化结果摘要"""
        pareto_trials = self.study.best_trials
        
        print("\n" + "="*70)
        print("📊 Pareto 前沿解决方案")
        print("="*70)
        
        for i, trial in enumerate(pareto_trials):
            print(f"\n方案 {i+1}:")
            print(f"  精度: {trial.values[0]:.3f}")
            print(f"  Tokens: {trial.values[1]}")
            print(f"  时间: {trial.values[2]:.2f}s")
            print(f"  配置:")
            for param_name, param_value in trial.params.items():
                # 解析参数名: op_0_filter_operator -> filter
                parts = param_name.split('_')
                op_name = '_'.join(parts[2:-1])  # 提取操作名
                print(f"    - {op_name}: {param_value}")
        
        print("\n" + "="*70)
        print("💡 如何选择方案:")
        print("  - 需要高精度 → 选择精度最高的方案")
        print("  - 需要低成本 → 选择 tokens 最少的方案")
        print("  - 需要快速 → 选择时间最短的方案")
        print("  - 需要平衡 → 根据具体需求权衡")
        print("="*70)
    
    def get_best_trial_for_objective(self, objective_index: int = 0) -> optuna.trial.FrozenTrial:
        """
        获取某个目标的最佳试验。
        
        Args:
            objective_index: 目标索引 (0=精度, 1=tokens, 2=时间)
        
        Returns:
            最佳试验
        """
        pareto_trials = self.study.best_trials
        
        if objective_index == 0:
            # 精度最高
            return max(pareto_trials, key=lambda t: t.values[0])
        else:
            # tokens 或时间最少
            return min(pareto_trials, key=lambda t: t.values[objective_index])
