# Kubernetes 部署指南

本目录包含 Browser RPC 集群的 Kubernetes 部署清单。

## 文件说明

- `namespace.yaml`: 创建 `browser-rpc` 命名空间
- `configmap.yaml`: 应用配置（非敏感信息）
- `secret.yaml`: 敏感配置（API Key、集群密钥等）
- `redis-deployment.yaml`: Redis 服务部署
- `gateway-deployment.yaml`: Gateway 服务部署
- `worker-deployment.yaml`: Worker 节点部署
- `ingress.yaml`: 外部访问入口配置

## 部署步骤

### 1. 构建并推送 Docker 镜像

```bash
# 构建镜像
docker build -t your-registry/browser-rpc:latest .

# 推送到镜像仓库
docker push your-registry/browser-rpc:latest
```

### 2. 修改配置

- 编辑 `secret.yaml`，设置实际的 `CLUSTER_SECRET` 和 `API_KEY`
- 编辑 `gateway-deployment.yaml` 和 `worker-deployment.yaml`，将镜像地址改为你的镜像仓库
- 编辑 `ingress.yaml`，设置你的域名

### 3. 按顺序部署

```bash
# 1. 创建命名空间
kubectl apply -f namespace.yaml

# 2. 创建配置
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# 3. 部署 Redis
kubectl apply -f redis-deployment.yaml

# 4. 等待 Redis 就绪
kubectl wait --for=condition=ready pod -l app=redis -n browser-rpc --timeout=60s

# 5. 部署 Worker 节点
kubectl apply -f worker-deployment.yaml

# 6. 部署 Gateway
kubectl apply -f gateway-deployment.yaml

# 7. 部署 Ingress（可选）
kubectl apply -f ingress.yaml
```

### 4. 验证部署

```bash
# 查看所有 Pod 状态
kubectl get pods -n browser-rpc

# 查看服务
kubectl get svc -n browser-rpc

# 查看 Gateway 日志
kubectl logs -f deployment/gateway -n browser-rpc

# 查看 Worker 日志
kubectl logs -f deployment/worker -n browser-rpc
```

## 扩缩容

### 扩展 Worker 节点

```bash
kubectl scale deployment worker --replicas=5 -n browser-rpc
```

### 扩展 Gateway

```bash
kubectl scale deployment gateway --replicas=3 -n browser-rpc
```

## 监控集成

如果已部署 Prometheus，可以添加 ServiceMonitor：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: browser-rpc
  namespace: browser-rpc
spec:
  selector:
    matchLabels:
      app: gateway  # 或 worker
  endpoints:
  - port: http
    path: /metrics
```

## 测试

### 快速测试

```bash
# 使用快速测试脚本
./k8s/quick_test.sh

# 或使用 Python 测试脚本
python3 k8s/test_k8s.py
```

### 详细测试指南

查看 [K8s 测试指南](./TEST_GUIDE.md) 了解完整的测试流程，包括：
- 功能测试
- 监控测试
- 负载测试
- 故障排查

## 注意事项

1. **资源限制**: 根据实际负载调整 `resources.requests` 和 `resources.limits`
2. **持久化存储**: 如果需要持久化日志，可以使用 PVC 替代 `emptyDir`
3. **高可用**: Redis 可以配置为主从模式或使用 Redis Sentinel
4. **安全**: 生产环境务必修改默认密钥，启用 TLS
5. **镜像仓库**: 确保 Kubernetes 集群可以访问你的镜像仓库

## 相关文档

- [K8s 测试指南](./TEST_GUIDE.md) - 详细的测试方法和故障排查
- [长期规划实施总结](../docs/long_term_planning_summary.md) - 了解所有功能
- [本地测试指南](../docs/test_guide.md) - Docker Compose 测试方法

