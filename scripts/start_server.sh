#!/bin/bash

# 浏览器 RPC 服务器启动脚本

set -e

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 检查依赖是否已安装
if ! python -c "import grpc" 2>/dev/null; then
    echo "正在安装依赖..."
    pip install -r requirements.txt
fi

# 检查 Playwright 浏览器是否已安装
if ! python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.executable_path; p.stop()" 2>/dev/null; then
    echo "正在安装 Playwright 浏览器..."
    playwright install chromium
fi

# 编译 proto 文件
echo "编译 proto 文件..."
python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/spider.proto

# 创建日志目录
mkdir -p log

# 启动服务器
echo "启动浏览器 RPC 服务器..."
python rpc_server.py "$@"

