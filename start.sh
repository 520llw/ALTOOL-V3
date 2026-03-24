#!/bin/bash
# 功率器件参数提取系统 - Linux/Mac启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  ⚡ 功率器件参数提取系统"
echo "=========================================="
echo ""

# 检查Python环境
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ 错误: 未找到Python环境，请先安装Python 3.8+"
    exit 1
fi

echo "✓ Python: $($PYTHON_CMD --version)"

# 检查并安装依赖
echo ""
echo "正在检查依赖..."
$PYTHON_CMD -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "正在安装依赖..."
    $PYTHON_CMD -m pip install -r requirements.txt -q
fi

echo "✓ 依赖检查完成"

# 创建必要目录
mkdir -p data logs output

# 启动Streamlit
echo ""
echo "正在启动系统..."
echo "请稍候，浏览器将自动打开..."
echo ""
echo "如果浏览器未自动打开，请访问: http://localhost:8501"
echo "按 Ctrl+C 停止服务"
echo ""

$PYTHON_CMD -m streamlit run main.py \
    --server.port 8501 \
    --server.headless false \
    --browser.gatherUsageStats false \
    --theme.base dark

