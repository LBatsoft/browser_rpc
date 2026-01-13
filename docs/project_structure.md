# 项目结构说明

## 目录结构

```
browser_rpc/
├── src/
│   └── browser_rpc/          # 主包目录
│       ├── __init__.py
│       ├── client/          # 客户端代码
│       │   ├── __init__.py
│       │   ├── rpc_client.py
│       │   └── http_client.py
│       ├── server/          # 服务器代码
│       │   ├── __init__.py
│       │   ├── rpc_server.py
│       │   ├── http_server.py
│       │   └── gateway.py
│       ├── core/            # 核心模块
│       │   ├── __init__.py
│       │   ├── cdp_client.py
│       │   ├── config.py
│       │   ├── metrics.py
│       │   └── registry.py
│       └── proto_gen/       # 生成的 proto 文件
│           ├── __init__.py
│           ├── spider_pb2.py
│           └── spider_pb2_grpc.py
│
├── proto/                   # Protocol Buffers 定义
│   └── spider.proto
│
├── docs/                    # 文档目录
│   ├── README_CN.md        # 中文 README
│   ├── test_guide.md       # 测试指南
│   └── ...                 # 其他文档
│
├── k8s/                     # Kubernetes 部署文件
│   ├── *.yaml              # K8s 资源清单
│   └── ...
│
├── monitoring/              # 监控配置
│   ├── prometheus.yml      # Prometheus 配置
│   └── grafana/            # Grafana 配置
│
├── resources/               # 资源文件
│   ├── screenshots/        # 截图目录
│   └── stealth/            # 反检测脚本
│
├── scripts/                 # 脚本目录
│   ├── cleanup.sh          # 清理脚本
│   ├── start_*.sh          # 启动脚本
│   └── test_*.py           # 测试脚本
│
├── static/                  # 静态文件（Web UI）
│   ├── remote.html         # 远程控制界面
│   └── ...
│
├── log/                     # 日志目录（由 .gitignore 忽略）
│
├── gateway.py              # Gateway 入口脚本（向后兼容）
├── http_server.py          # HTTP Server 入口脚本（向后兼容）
├── rpc_server.py           # RPC Server 入口脚本（向后兼容）
├── rpc_client.py           # RPC Client 入口脚本（向后兼容）
│
├── docker-compose.yml      # Docker Compose 配置
├── Dockerfile              # Docker 镜像构建
├── requirements.txt        # Python 依赖
├── README.md               # 项目说明
└── .gitignore              # Git 忽略规则
```

## 文件说明

### 核心代码（Browser RPC 能力）

**核心组件**:
- `proto/spider.proto` - **RPC 接口定义**（13个核心接口）
- `src/browser_rpc/server/rpc_server.py` - **RPC 服务器**（核心服务）
- `src/browser_rpc/client/rpc_client.py` - **RPC 客户端**（Python API）
- `src/browser_rpc/core/cdp_client.py` - **浏览器控制核心**（CDP 封装，反检测集成）
- `src/browser_rpc/proto_gen/spider_pb2.py`, `spider_pb2_grpc.py` - 生成的 gRPC 代码

**扩展功能**:
- `src/browser_rpc/server/gateway.py` - 统一网关，负责路由和负载均衡（可选）
- `src/browser_rpc/server/http_server.py` - Worker 节点的 HTTP API 服务（可选）
- `src/browser_rpc/client/http_client.py` - HTTP 客户端（可选）
- `src/browser_rpc/core/registry.py` - 服务注册与发现（分布式架构）
- `src/browser_rpc/core/metrics.py` - Prometheus 监控指标（监控增强）

**向后兼容入口脚本**:
- `gateway.py` - Gateway 入口（导入新包结构）
- `http_server.py` - HTTP Server 入口（导入新包结构）
- `rpc_server.py` - RPC Server 入口（导入新包结构）
- `rpc_client.py` - RPC Client 入口（导入新包结构）

### 配置文件
- `docker-compose.yml` - 本地开发环境
- `k8s/*.yaml` - Kubernetes 部署清单
- `monitoring/*.yml` - 监控系统配置
- `config.py` - 应用配置管理

### 脚本文件
- `scripts/cleanup.sh` - 清理临时文件
- `scripts/start_*.sh` - 各种启动脚本
- `scripts/test_*.py` - 测试脚本

### 文档
- `docs/` - 所有项目文档
- `README.md` - 项目主文档

## 被忽略的文件

以下文件/目录由 `.gitignore` 管理，不会提交到版本控制：

- `*.log` - 所有日志文件
- `__pycache__/` - Python 缓存
- `*.png`, `*.jpg` - 截图文件（除了 resources/stealth/）
- `log/` - 日志目录
- `.env` - 环境变量文件
- `venv/`, `env/` - 虚拟环境

## 清理

运行清理脚本删除临时文件：

```bash
./scripts/cleanup.sh
```

或手动清理：

```bash
# 删除日志
find . -name "*.log" -delete

# 删除缓存
find . -type d -name "__pycache__" -exec rm -r {} +
```

