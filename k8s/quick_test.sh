#!/bin/bash
# K8s 快速测试脚本

set -e

NAMESPACE="browser-rpc"
GATEWAY_SVC="gateway-service"

echo "=========================================="
echo "K8s Browser RPC - 快速测试"
echo "=========================================="

# 检查 kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl 未安装"
    exit 1
fi

# 检查集群连接
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ 无法连接到 Kubernetes 集群"
    exit 1
fi

# 1. 检查 Pod 状态
echo ""
echo "1. 检查 Pod 状态..."
kubectl get pods -n $NAMESPACE || {
    echo "⚠️  命名空间 $NAMESPACE 不存在或没有 Pod"
    echo "   请先运行: kubectl apply -f k8s/"
    exit 1
}

# 2. 等待 Pod 就绪
echo ""
echo "2. 等待 Pod 就绪..."
kubectl wait --for=condition=ready pod -l app=gateway -n $NAMESPACE --timeout=60s || true
kubectl wait --for=condition=ready pod -l app=worker -n $NAMESPACE --timeout=60s || true

# 3. 获取 API Key
echo ""
echo "3. 获取 API Key..."
API_KEY=$(kubectl get secret browser-rpc-secrets -n $NAMESPACE -o jsonpath='{.data.API_KEY}' 2>/dev/null | base64 -d || echo "")
if [ -z "$API_KEY" ]; then
    echo "⚠️  无法获取 API Key，使用默认值"
    API_KEY="dev-test-key"
else
    echo "✅ API Key 获取成功: ${API_KEY:0:10}..."
fi

# 4. 端口转发
echo ""
echo "4. 启动端口转发..."
kubectl port-forward svc/$GATEWAY_SVC 8000:8000 -n $NAMESPACE > /dev/null 2>&1 &
PF_PID=$!
sleep 5

# 清理函数
cleanup() {
    echo ""
    echo "清理端口转发..."
    kill $PF_PID 2>/dev/null || true
    wait $PF_PID 2>/dev/null || true
}
trap cleanup EXIT

# 5. 测试 API
echo ""
echo "5. 测试 Gateway API..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ Gateway 响应正常"
else
    echo "❌ Gateway 无响应"
    exit 1
fi

# 6. 创建会话
echo ""
echo "6. 测试创建会话..."
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/sessions \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"headless": true, "width": 1280, "height": 720}')

if echo "$SESSION_RESPONSE" | grep -q "session_id"; then
    SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -o '"session_id":"[^"]*' | cut -d'"' -f4)
    echo "✅ 会话创建成功: $SESSION_ID"
else
    echo "❌ 会话创建失败"
    echo "响应: $SESSION_RESPONSE"
fi

# 7. 检查指标
echo ""
echo "7. 检查 Metrics 端点..."
METRICS_COUNT=$(curl -s http://localhost:8000/metrics | grep -c "gateway_requests_total" || echo "0")
if [ "$METRICS_COUNT" -gt 0 ]; then
    echo "✅ Metrics 端点正常 (找到 $METRICS_COUNT 个指标)"
else
    echo "⚠️  Metrics 端点可能异常"
fi

# 8. 查看资源使用
echo ""
echo "8. 查看资源使用情况..."
if kubectl top pods -n $NAMESPACE 2>/dev/null; then
    echo "✅ 资源监控正常"
else
    echo "⚠️  无法获取资源使用情况（可能需要 metrics-server）"
fi

# 9. 查看服务状态
echo ""
echo "9. 查看服务状态..."
kubectl get svc -n $NAMESPACE

echo ""
echo "=========================================="
echo "✅ 测试完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  - 端口转发已启动: http://localhost:8000"
echo "  - API 文档: http://localhost:8000/docs"
echo ""
echo "查看日志:"
echo "  kubectl logs -f deployment/gateway -n $NAMESPACE"
echo "  kubectl logs -f deployment/worker -n $NAMESPACE"
echo ""
echo "停止端口转发: Ctrl+C"

# 保持端口转发运行
wait $PF_PID

