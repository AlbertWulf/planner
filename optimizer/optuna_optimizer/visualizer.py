"""
Optuna 优化结果可视化
"""

import optuna
from typing import List
import matplotlib.pyplot as plt
from pathlib import Path


def plot_pareto_front(study: optuna.Study, save_path: str = None):
    """
    绘制 Pareto 前沿图。
    
    Args:
        study: Optuna study 对象
        save_path: 保存路径（可选）
    """
    try:
        import plotly.graph_objects as go
        
        # 获取所有试验
        trials = study.get_trials()
        
        # 分离 Pareto 前沿和其他点
        pareto_trials = study.best_trials
        pareto_numbers = {t.number for t in pareto_trials}
        
        # 提取数据
        accuracies = [t.values[0] for t in trials if t.values is not None]
        tokens = [t.values[1] for t in trials if t.values is not None]
        times = [t.values[2] for t in trials if t.values is not None]
        
        pareto_acc = [t.values[0] for t in pareto_trials]
        pareto_tok = [t.values[1] for t in pareto_trials]
        pareto_time = [t.values[2] for t in pareto_trials]
        
        # 创建 3D 散点图
        fig = go.Figure()
        
        # 所有试验点
        fig.add_trace(go.Scatter3d(
            x=accuracies,
            y=tokens,
            z=times,
            mode='markers',
            marker=dict(size=5, color='lightblue', opacity=0.5),
            name='所有试验'
        ))
        
        # Pareto 前沿点
        fig.add_trace(go.Scatter3d(
            x=pareto_acc,
            y=pareto_tok,
            z=pareto_time,
            mode='markers',
            marker=dict(size=10, color='red', symbol='diamond'),
            name='Pareto 前沿'
        ))
        
        fig.update_layout(
            title='Pareto 前沿可视化',
            scene=dict(
                xaxis_title='精度 (↑)',
                yaxis_title='Tokens (↓)',
                zaxis_title='时间 (↓)'
            ),
            width=900,
            height=700
        )
        
        if save_path:
            fig.write_html(save_path)
            print(f"✓ Pareto 前沿图已保存: {save_path}")
        else:
            fig.show()
    
    except ImportError:
        print("⚠️  需要安装 plotly: pip install plotly")


def plot_optimization_history(study: optuna.Study, save_path: str = None):
    """
    绘制优化历史图。
    
    Args:
        study: Optuna study 对象
        save_path: 保存路径（可选）
    """
    try:
        # 使用 Optuna 内置的可视化
        fig = optuna.visualization.plot_optimization_history(study)
        
        if save_path:
            fig.write_html(save_path)
            print(f"✓ 优化历史图已保存: {save_path}")
        else:
            fig.show()
    
    except ImportError:
        print("⚠️  需要安装 plotly: pip install plotly")


def plot_param_importances(study: optuna.Study, save_path: str = None):
    """
    绘制参数重要性图。
    
    Args:
        study: Optuna study 对象
        save_path: 保存路径（可选）
    """
    try:
        fig = optuna.visualization.plot_param_importances(study)
        
        if save_path:
            fig.write_html(save_path)
            print(f"✓ 参数重要性图已保存: {save_path}")
        else:
            fig.show()
    
    except ImportError:
        print("⚠️  需要安装 plotly: pip install plotly")


def save_all_visualizations(study: optuna.Study, output_dir: str):
    """
    保存所有可视化图表。
    
    Args:
        study: Optuna study 对象
        output_dir: 输出目录
    """
    from pathlib import Path
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("\n📊 生成可视化图表...")
    
    # Pareto 前沿
    plot_pareto_front(
        study,
        save_path=str(output_path / "pareto_front.html")
    )
    
    # 优化历史
    plot_optimization_history(
        study,
        save_path=str(output_path / "optimization_history.html")
    )
    
    # 参数重要性
    try:
        plot_param_importances(
            study,
            save_path=str(output_path / "param_importances.html")
        )
    except Exception as e:
        print(f"⚠️  参数重要性图生成失败: {e}")
    
    print(f"✓ 所有图表已保存到: {output_dir}")
