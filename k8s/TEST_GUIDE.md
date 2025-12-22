# Kubernetes 测试指南

本文档详细说明如何在 Kubernetes 环境中测试 Browser RPC 集群。

## 目录

1. [前置要求](#前置要求)
2. [部署前准备](#部署前准备)
3. [部署步骤](#部署步骤)
4. [功能测试](#功能测试)
5. [监控测试](#监控测试)
6. [负载测试](#负载测试)
7. [故障排查](#故障排查)
8. [清理资源](#清理资源)

## 前置要求

### 1. Kubernetes 集群

- 本地开发: Minikube, Kind, K3s, Docker Desktop Kubernetes
- 云环境: GKE, EKS, AKS 等
- 确保 `kubectl` 已配置并可以访问集群

### 2. 镜像仓库访问

- 本地集群: 可以使用本地镜像（Kind 需要特殊配置）
- 云环境: 需要推送到可访问的镜像仓库（Docker Hub, GCR, ECR 等）

### 3. 工具

```bash
# 检查 kubectl
kubectl version --client

# 检查集群连接
kubectl cluster-info

# 检查节点
kubectl get nodes
```

## 部署前准备

### 1. 构建和推送镜像

#### 方式 A: 使用本地镜像（Kind/Minikube）

```bash
# 构建镜像
docker build -t browser-rpc:latest .

# 对于 Kind
kind load docker-image browser-rpc:latest

# 对于 Minikube
minikube image load browser-rpc:latest
```

#### 方式 B: 推送到镜像仓库

```bash
# 登录镜像仓库
docker login your-registry.com

# 构建并标记
docker build -t your-registry.com/browser-rpc:latest .
docker tag browser-rpc:latest your-registry.com/browser-rpc:v1.0.0

# 推送
docker push your-registry.com/browser-rpc:latest
docker push your-registry.com/browser-rpc:v1.0.0
```

### 2. 修改配置文件

#### 更新镜像地址

编辑 `gateway-deployment.yaml` 和 `worker-deployment.yaml`:

```yaml
# 本地镜像
image: browser-rpc:latest
imagePullPolicy: IfNotPresent

# 或远程镜像
image: your-registry.com/browser-rpc:latest
imagePullPolicy: Always
```

#### 配置密钥

编辑 `secret.yaml`:

```yaml
stringData:
  CLUSTER_SECRET: "your-secure-cluster-secret"
  API_KEY: "your-api-key"
```

#### 配置 Ingress（可选）

编辑 `ingress.yaml`，设置你的域名或使用 NodePort/LoadBalancer。

## 部署步骤

### 1. 创建命名空间

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. 创建配置

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 验证
kubectl get configmap -n browser-rpc
kubectl get secret -n browser-rpc
```

### 3. 部署 Redis

```bash
kubectl apply -f k8s/redis-deployment.yaml

# 等待 Redis 就绪
kubectl wait --for=condition=ready pod -l app=redis -n browser-rpc --timeout=120s

# 验证
kubectl get pods -l app=redis -n browser-rpc
kubectl logs -l app=redis -n browser-rpc
```

### 4. 部署 Worker 节点

```bash
kubectl apply -f k8s/worker-deployment.yaml

# 等待 Worker 就绪
kubectl wait --for=condition=ready pod -l app=worker -n browser-rpc --timeout=120s

# 验证
kubectl get pods -l app=worker -n browser-rpc
kubectl logs -l app=worker -n browser-rpc --tail=50
```

### 5. 部署 Gateway

```bash
kubectl apply -f k8s/gateway-deployment.yaml

# 等待 Gateway 就绪
kubectl wait --for=condition=ready pod -l app=gateway -n browser-rpc --timeout=120s

# 验证
kubectl get pods -l app=gateway -n browser-rpc
kubectl logs -l app=gateway -n browser-rpc --tail=50
```

### 6. 部署 Ingress（可选）

```bash
kubectl apply -f k8s/ingress.yaml

# 验证
kubectl get ingress -n browser-rpc
```

### 7. 查看所有资源

```bash
# 查看所有 Pod
kubectl get pods -n browser-rpc

# 查看所有服务
kubectl get svc -n browser-rpc

# 查看所有资源
kubectl get all -n browser-rpc
```

## 功能测试

### 1. 端口转发（访问服务）

```bash
# 转发 Gateway 端口
kubectl port-forward svc/gateway-service 8000:8000 -n browser-rpc

# 在另一个终端测试
curl http://localhost:8000/
```

### 2. 使用测试脚本

```bash
# 设置环境变量
export GATEWAY_URL="http://localhost:8000"
export API_KEY="your-api-key"  # 从 secret.yaml 中获取

# 运行测试
python3 scripts/test_gateway_local.py
```

### 3. 创建测试 Pod（在集群内测试）

```bash
# 创建测试 Pod
kubectl run test-pod --image=curlimages/curl --rm -it --restart=Never -n browser-rpc -- sh

# 在 Pod 内测试
curl http://gateway-service:8000/
curl -X POST http://gateway-service:8000/api/sessions \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"headless": true}'
```

### 4. 测试 API 功能

```bash
# 获取 API Key（从 Secret）
API_KEY=$(kubectl get secret browser-rpc-secrets -n browser-rpc -o jsonpath='{.data.API_KEY}' | base64 -d)

# 创建会话
curl -X POST http://localhost:8000/api/sessions \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"headless": true, "width": 1280, "height": 720}'

# 测试地域偏好
curl -X POST http://localhost:8000/api/sessions \
  -H "X-API-Key: $API_KEY" \
  -H "X-Preferred-Region: us-west" \
  -H "Content-Type: application/json" \
  -d '{"headless": true}'
```

## 监控测试

### 1. 检查 Metrics 端点

```bash
# 端口转发 Gateway
kubectl port-forward svc/gateway-service 8000:8000 -n browser-rpc

# 在另一个终端查看指标
curl http://localhost:8000/metrics | grep gateway_requests_total
```

### 2. 集成 Prometheus（如果已部署）

#### 创建 ServiceMonitor

```bash
cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: browser-rpc-gateway
  namespace: browser-rpc
spec:
  selector:
    matchLabels:
      app: gateway
  endpoints:
  - port: http
    path: /metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: browser-rpc-worker
  namespace: browser-rpc
spec:
  selector:
    matchLabels:
      app: worker
  endpoints:
  - port: http
    path: /metrics
EOF
```

### 3. 查看 Pod 资源使用

```bash
# 查看资源使用情况
kubectl top pods -n browser-rpc

# 查看节点资源
kubectl top nodes
```

## 负载测试

### 1. 扩展 Worker 节点

```bash
# 扩展到 5 个 Worker
kubectl scale deployment worker --replicas=5 -n browser-rpc

# 查看扩展进度
kubectl get pods -l app=worker -n browser-rpc -w
```

### 2. 使用压力测试工具

```bash
# 安装 hey (HTTP 负载测试工具)
# macOS: brew install hey
# Linux: go install github.com/rakyll/hey@latest

# 获取 API Key
API_KEY=$(kubectl get secret browser-rpc-secrets -n browser-rpc -o jsonpath='{.data.API_KEY}' | base64 -d)

# 端口转发
kubectl port-forward svc/gateway-service 8000:8000 -n browser-rpc

# 运行负载测试（在另一个终端）
hey -n 100 -c 10 -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"headless": true}' \
  -m POST \
  http://localhost:8000/api/sessions
```

### 3. 监控负载下的表现

```bash
# 实时查看 Pod 状态
watch kubectl get pods -n browser-rpc

# 查看资源使用
watch kubectl top pods -n browser-rpc

# 查看日志
kubectl logs -f deployment/gateway -n browser-rpc
```

## 故障排查

### 1. Pod 无法启动

```bash
# 查看 Pod 状态
kubectl get pods -n browser-rpc

# 查看 Pod 详情
kubectl describe pod <pod-name> -n browser-rpc

# 查看日志
kubectl logs <pod-name> -n browser-rpc

# 查看前一个容器的日志（如果容器崩溃）
kubectl logs <pod-name> -n browser-rpc --previous
```

### 2. 服务无法访问

```bash
# 检查服务
kubectl get svc -n browser-rpc

# 检查端点
kubectl get endpoints -n browser-rpc

# 测试服务 DNS
kubectl run test-dns --image=busybox --rm -it --restart=Never -n browser-rpc -- nslookup gateway-service
```

### 3. 镜像拉取失败

```bash
# 检查镜像
kubectl describe pod <pod-name> -n browser-rpc | grep -i image

# 对于本地集群，确保镜像已加载
# Kind
kind load docker-image browser-rpc:latest

# Minikube
minikube image load browser-rpc:latest
```

### 4. 配置问题

```bash
# 检查 ConfigMap
kubectl get configmap browser-rpc-config -n browser-rpc -o yaml

# 检查 Secret
kubectl get secret browser-rpc-secrets -n browser-rpc -o yaml

# 验证环境变量
kubectl exec <pod-name> -n browser-rpc -- env | grep -E "REDIS_URL|CLUSTER_SECRET"
```

### 5. Redis 连接问题

```bash
# 检查 Redis Pod
kubectl get pods -l app=redis -n browser-rpc

# 测试 Redis 连接
kubectl run redis-test --image=redis:7-alpine --rm -it --restart=Never -n browser-rpc -- redis-cli -h redis-service ping
```

## 清理资源

### 删除所有资源

```bash
# 删除所有部署
kubectl delete -f k8s/

# 或逐个删除
kubectl delete deployment gateway worker redis -n browser-rpc
kubectl delete svc gateway-service worker-service redis-service -n browser-rpc
kubectl delete configmap browser-rpc-config -n browser-rpc
kubectl delete secret browser-rpc-secrets -n browser-rpc
kubectl delete namespace browser-rpc
```

### 保留数据（仅删除 Pod）

```bash
# 仅删除 Pod（Deployment 会重新创建）
kubectl delete pod -l app=gateway -n browser-rpc
kubectl delete pod -l app=worker -n browser-rpc
```

## 快速测试脚本

创建一个测试脚本可以简化测试流程：

```bash
#!/bin/bash
# k8s/quick_test.sh

set -e

NAMESPACE="browser-rpc"
GATEWAY_SVC="gateway-service"

echo "=========================================="
echo "K8s Browser RPC - 快速测试"
echo "=========================================="

# 1. 检查 Pod 状态
echo ""
echo "1. 检查 Pod 状态..."
kubectl get pods -n $NAMESPACE

# 2. 获取 API Key
echo ""
echo "2. 获取 API Key..."
API_KEY=$(kubectl get secret browser-rpc-secrets -n $NAMESPACE -o jsonpath='{.data.API_KEY}' | base64 -d)
echo "API Key: ${API_KEY:0:10}..."

# 3. 端口转发
echo ""
echo "3. 启动端口转发..."
kubectl port-forward svc/$GATEWAY_SVC 8000:8000 -n $NAMESPACE &
PF_PID=$!
sleep 3

# 4. 测试 API
echo ""
echo "4. 测试 API..."
curl -s http://localhost:8000/ | jq . || echo "Gateway 响应正常"

# 5. 创建会话
echo ""
echo "5. 创建会话..."
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/sessions \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"headless": true}')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id // empty')
if [ -n "$SESSION_ID" ]; then
    echo "✅ 会话创建成功: $SESSION_ID"
else
    echo "❌ 会话创建失败: $SESSION_RESPONSE"
fi

# 6. 检查指标
echo ""
echo "6. 检查指标..."
curl -s http://localhost:8000/metrics | grep -c "gateway_requests_total" && echo "✅ Metrics 端点正常" || echo "⚠️  Metrics 端点异常"

# 清理
kill $PF_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
```

## 最佳实践

1. **使用命名空间隔离**: 测试和生产环境使用不同的命名空间
2. **资源限制**: 设置合理的 requests 和 limits
3. **健康检查**: 确保 liveness 和 readiness probes 配置正确
4. **日志收集**: 考虑集成日志收集系统（如 ELK, Loki）
5. **监控告警**: 集成 Prometheus 和 Grafana
6. **备份配置**: 使用 Git 管理 K8s 配置文件

## 下一步

- 查看 [部署指南](./README.md) 了解详细部署步骤
- 查看 [长期规划总结](../docs/long_term_planning_summary.md) 了解所有功能
- 查看 [测试指南](../docs/test_guide.md) 了解本地测试方法

