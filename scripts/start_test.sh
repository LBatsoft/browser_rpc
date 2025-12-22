#!/bin/bash
# 启动测试脚本

set -e

echo "=========================================="
echo "Browser RPC - 启动测试"
echo "=========================================="

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

echo ""
echo "1. 构建镜像..."
docker-compose build

echo ""
echo "2. 启动服务..."
docker-compose up -d

echo ""
echo "3. 等待服务就绪..."
sleep 5

echo ""
echo "4. 检查服务状态..."
docker-compose ps

echo ""
echo "5. 测试服务健康..."
echo "   - Gateway: http://localhost:8000"
echo "   - Prometheus: http://localhost:9090"
echo "   - Grafana: http://localhost:3000"

# 等待一下让服务完全启动
sleep 3

echo ""
echo "6. 运行监控测试..."
python3 scripts/test_monitoring.py

echo ""
echo "=========================================="
echo "✅ 测试启动完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  - Gateway API: http://localhost:8000"
echo "  - Gateway Docs: http://localhost:8000/docs"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "查看日志:"
echo "  docker-compose logs -f gateway"
echo "  docker-compose logs -f browser-node-1"
echo ""
echo "停止服务:"
echo "  docker-compose down"

