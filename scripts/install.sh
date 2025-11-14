#!/bin/bash

# 浏览器 RPC 安装脚本

set -e

echo "================================"
echo "浏览器 RPC 工具安装"
echo "================================"

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 检查 Python 版本
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python 版本: $PYTHON_VERSION"

# 创建虚拟环境（可选）
read -p "是否创建虚拟环境？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ ! -d "venv" ]; then
        echo "创建虚拟环境..."
        python -m venv venv
    fi
    source venv/bin/activate
    echo "虚拟环境已激活"
fi

# 更新 pip
echo "更新 pip..."
pip install --upgrade pip

# 安装依赖
echo "安装 Python 依赖..."
pip install -r requirements.txt

# 安装 Playwright 浏览器
echo "安装 Playwright 浏览器..."
playwright install chromium

# 编译 proto 文件
echo "编译 proto 文件..."
python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/spider.proto

# 创建必要的目录
echo "创建目录..."
mkdir -p log

# 复制配置文件
if [ ! -f ".env" ]; then
    echo "创建配置文件..."
    cp .env.example .env
    echo "请根据需要修改 .env 文件"
fi

echo "================================"
echo "安装完成！"
echo "================================"
echo ""
echo "使用方法："
echo "1. 启动服务器: ./scripts/start_server.sh"
echo "2. 运行客户端示例: python rpc_client.py --example basic"
echo ""
echo "更多信息请查看 README.md"


