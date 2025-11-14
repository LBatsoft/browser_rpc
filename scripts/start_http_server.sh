#!/bin/bash

# HTTP 服务器启动脚本

set -e

echo "================================"
echo "启动 Browser RPC HTTP 服务器"
echo "================================"

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 检查 Python 环境
if ! command -v python &> /dev/null; then
    echo "❌ Python 未安装"
    exit 1
fi

# 检查依赖
if ! python -c "import fastapi" 2>/dev/null; then
    echo "⚠️  FastAPI 未安装，正在安装依赖..."
    pip install -r requirements.txt
fi

# 检查浏览器是否已安装
if ! python -c "import playwright; playwright.sync_api.sync_playwright().start().chromium.executable_path" &>/dev/null; then
    echo "⚠️  Playwright 浏览器未安装"
    echo "📥 正在安装 Chromium 浏览器..."
    playwright install chromium
fi

# 编译 proto 文件（如果需要）
if [ ! -f "spider_pb2.py" ]; then
    echo "📦 编译 proto 文件..."
    python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/spider.proto
fi

# 启动服务器
echo ""
echo "🚀 启动 HTTP 服务器..."
echo "📖 API 文档: http://localhost:8000/docs"
echo "📖 ReDoc: http://localhost:8000/redoc"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "================================"
echo ""

python http_server.py

