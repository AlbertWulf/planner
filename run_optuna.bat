@echo off
REM Optuna Pipeline 优化快速启动脚本
REM 
REM 使用方法:
REM   run_optuna.bat test      - 测试单个配置
REM   run_optuna.bat optimize  - 运行优化
REM   run_optuna.bat           - 默认运行优化

cd /d "%~dp0"

if "%1"=="test" (
    echo 运行测试模式...
    python -m planner.examples.optuna_medical_example --mode test
) else if "%1"=="optimize" (
    echo 运行优化模式...
    python -m planner.examples.optuna_medical_example --mode optimize
) else (
    echo 运行优化模式...
    python -m planner.examples.optuna_medical_example --mode optimize
)

pause
