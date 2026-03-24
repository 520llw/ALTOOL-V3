@echo off
chcp 65001 >nul
title 功率器件参数提取系统

echo ==========================================
echo   ⚡ 功率器件参数提取系统
echo ==========================================
echo.

:: 获取脚本所在目录
cd /d "%~dp0"

:: 检查Python环境
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 错误: 未找到Python环境，请先安装Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do echo ✓ %%i

:: 检查并安装依赖
echo.
echo 正在检查依赖...
python -c "import streamlit" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 正在安装依赖...
    python -m pip install -r requirements.txt -q
)

echo ✓ 依赖检查完成

:: 创建必要目录
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "output" mkdir output

:: 启动Streamlit
echo.
echo 正在启动系统...
echo 请稍候，浏览器将自动打开...
echo.
echo 如果浏览器未自动打开，请访问: http://localhost:8501
echo 按 Ctrl+C 停止服务
echo.

python -m streamlit run main.py ^
    --server.port 8501 ^
    --server.headless false ^
    --browser.gatherUsageStats false ^
    --theme.base light

pause

