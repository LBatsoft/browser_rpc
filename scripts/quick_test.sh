#!/bin/bash

# 快速测试脚本 - 自动启动服务器并运行测试

echo "🧪 Browser RPC 快速测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 激活环境
if [[ "$CONDA_DEFAULT_ENV" != "spider-api" ]]; then
    echo "⚠️  激活 spider-api 虚拟环境..."
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate spider-api
fi

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 检查浏览器是否已安装
if ! python -c "import playwright; playwright.sync_api.sync_playwright().start().chromium.executable_path" &>/dev/null; then
    echo "⚠️  Playwright 浏览器未安装"
    echo "📥 正在安装 Chromium 浏览器..."
    playwright install chromium
    echo ""
fi

# 启动服务器（后台运行）
echo "🚀 启动 RPC 服务器（后台）..."
python rpc_server.py --host 127.0.0.1 --port 50051 &
SERVER_PID=$!

# 等待服务器启动
echo "⏳ 等待服务器启动..."
sleep 3

# 检查服务器是否成功启动
if ! ps -p $SERVER_PID > /dev/null; then
    echo "❌ 服务器启动失败"
    exit 1
fi

echo "✅ 服务器已启动 (PID: $SERVER_PID)"
echo ""

# 运行测试
echo "🔍 运行反检测测试..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python test_anti_detection.py --test basic

# 测试完成后清理
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 清理：停止 RPC 服务器..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

echo "✅ 测试完成！"

