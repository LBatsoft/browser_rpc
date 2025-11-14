#!/bin/bash

# Browser RPC 服务器启动脚本

echo "🚀 启动 Browser RPC 服务器..."
echo ""

# 检查 conda 环境
if [[ "$CONDA_DEFAULT_ENV" != "spider-api" ]]; then
    echo "⚠️  激活 spider-api 虚拟环境..."
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate spider-api
fi

# 检查是否已有服务器在运行
if lsof -Pi :50051 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口 50051 已被占用，正在停止旧进程..."
    lsof -ti:50051 | xargs kill -9
    sleep 2
fi

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo "📍 工作目录: $(pwd)"
echo "🐍 Python 版本: $(python --version)"
echo "📦 环境: $CONDA_DEFAULT_ENV"
echo ""

# 启动服务器
echo "✅ 启动 RPC 服务器 (端口: 50051)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python rpc_server.py --host 0.0.0.0 --port 50051

