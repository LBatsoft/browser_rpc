# 测试启动指南

本文档说明如何启动和测试 Browser RPC 集群，包括监控功能。

## 前置要求

1. **Docker 和 Docker Compose** 已安装并运行
2. **Python 3.11+** (用于运行测试脚本)
3. **网络访问** (用于下载 Docker 镜像)

## 快速启动

### 方式 1: 使用启动脚本（推荐）

```bash
# 一键启动所有服务并运行测试
./scripts/start_test.sh
```

### 方式 2: 手动启动

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动所有服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f gateway
```

## 服务访问地址

启动成功后，可以通过以下地址访问：

- **Gateway API**: http://localhost:8000
- **Gateway API 文档**: http://localhost:8000/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - 默认账号: `admin`
  - 默认密码: `admin`

## 测试功能

### 1. 测试基本功能

```bash
# 测试 Gateway API
python3 scripts/test_gateway_local.py

# 测试监控功能
python3 scripts/test_monitoring.py
```

### 2. 测试监控指标

```bash
# 查看 Gateway 指标
curl http://localhost:8000/metrics

# 查看 Worker 指标
curl http://localhost:8001/metrics
curl http://localhost:8002/metrics
```

### 3. 测试地域调度

```bash
# 通过 Header 指定地域偏好
curl -X POST http://localhost:8000/api/sessions \
  -H "X-API-Key: dev-test-key" \
  -H "X-Preferred-Region: us-west" \
  -H "X-Preferred-Zone: us-west-2a" \
  -H "Content-Type: application/json" \
  -d '{"headless": true}'

# 通过请求体指定地域偏好
curl -X POST http://localhost:8000/api/sessions \
  -H "X-API-Key: dev-test-key" \
  -H "Content-Type: application/json" \
  -d '{
    "headless": true,
    "preferred_region": "us-west",
    "preferred_zone": "us-west-2a"
  }'
```

### 4. 查看 Prometheus 指标

1. 打开 http://localhost:9090
2. 在查询框中输入: `gateway_requests_total`
3. 点击 "Execute" 查看指标

### 5. 查看 Grafana 仪表板

1. 打开 http://localhost:3000
2. 使用 `admin/admin` 登录
3. 导航到 "Dashboards" → "Browser RPC Cluster Dashboard"
4. 查看各种监控图表

## 配置节点地域

如果需要测试跨地域调度，可以在 `docker-compose.yml` 中为节点添加地域配置：

```yaml
browser-node-1:
  environment:
    - NODE_REGION=us-west
    - NODE_ZONE=us-west-2a
    # ... 其他配置

browser-node-2:
  environment:
    - NODE_REGION=us-east
    - NODE_ZONE=us-east-1a
    # ... 其他配置
```

然后重启服务：

```bash
docker-compose down
docker-compose up -d
```

## 常见问题

### 1. Docker daemon 未运行

**错误**: `Cannot connect to the Docker daemon`

**解决**: 启动 Docker Desktop 或 Docker daemon

### 2. 端口被占用

**错误**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**解决**: 
- 检查并停止占用端口的进程
- 或修改 `docker-compose.yml` 中的端口映射

### 3. 服务无法启动

**检查日志**:
```bash
docker-compose logs gateway
docker-compose logs browser-node-1
docker-compose logs prometheus
```

### 4. Prometheus 无法抓取指标

**检查**:
1. 确认 Gateway 和 Worker 的 `/metrics` 端点可访问
2. 在 Prometheus UI (http://localhost:9090) 中查看 "Status" → "Targets"
3. 检查 `monitoring/prometheus.yml` 配置是否正确

### 5. Grafana 无法连接 Prometheus

**检查**:
1. 确认 Prometheus 服务运行正常
2. 检查 `monitoring/grafana/datasources/prometheus.yml` 中的 URL
3. 在 Grafana 中手动添加数据源: Configuration → Data Sources → Add data source → Prometheus

## 停止服务

```bash
# 停止并删除容器
docker-compose down

# 停止并删除容器和卷（会删除 Prometheus 和 Grafana 数据）
docker-compose down -v
```

## 清理

```bash
# 删除所有容器、网络和卷
docker-compose down -v

# 删除镜像
docker-compose down --rmi all
```

## 下一步

- 查看 [长期规划实施总结](./long_term_planning_summary.md) 了解所有功能
- 查看 [K8s 部署指南](../k8s/README.md) 了解 Kubernetes 部署
- 查看 [API 文档](http://localhost:8000/docs) 了解 API 使用

