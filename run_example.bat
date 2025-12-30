@echo off
echo ======================================================================
echo Pipeline Optimizer - 真实示例运行脚本
echo ======================================================================
echo.

cd /d %~dp0..

echo 检查数据文件...
if not exist "planner\data\medical_documents.json" (
    echo [错误] 数据文件不存在: planner\data\medical_documents.json
    pause
    exit /b 1
)
echo [OK] 数据文件已找到
echo.

echo 选择运行模式:
echo   1. 测试模式 (test) - 运行单个 pipeline
echo   2. 优化模式 (optimize) - 完整优化过程
echo.
set /p MODE="请输入选项 (1 或 2): "

if "%MODE%"=="1" (
    echo.
    echo 运行测试模式...
    python -m planner.examples.real_medical_example --mode test
) else if "%MODE%"=="2" (
    echo.
    echo 运行优化模式...
    python -m planner.examples.real_medical_example --mode optimize
) else (
    echo 无效选项，默认运行测试模式
    python -m planner.examples.real_medical_example --mode test
)

echo.
echo ======================================================================
echo 运行完成
echo ======================================================================
pause
