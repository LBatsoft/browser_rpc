# 项目结构说明

## 目录结构

```
browser_rpc/
├── core/                    # 核心模块
│   ├── metrics.py          # Prometheus 监控指标
│   └── registry.py         # 节点注册与发现
│
├── docs/                    # 文档目录
│   ├── README_CN.md        # 中文 README
│   ├── test_guide.md       # 测试指南
│   ├── code_review.md      # 代码审查报告
│   └── ...                 # 其他文档
│
├── k8s/                     # Kubernetes 部署文件
│   ├── *.yaml              # K8s 资源清单
│   ├── README.md           # K8s 部署指南
│   ├── TEST_GUIDE.md      # K8s 测试指南
│   └── *.sh, *.py          # 测试脚本
│
├── monitoring/              # 监控配置
│   ├── prometheus.yml      # Prometheus 配置
│   └── grafana/            # Grafana 配置
│
├── proto/                   # Protocol Buffers 定义
│   └── spider.proto
│
├── resources/               # 资源文件
│   ├── screenshots/        # 截图目录（空，由 .gitignore 忽略）
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
├── gateway.py              # Gateway 服务
├── http_server.py          # Worker HTTP 服务
├── http_client.py          # HTTP 客户端
├── rpc_server.py           # gRPC 服务
├── rpc_client.py           # gRPC 客户端
├── cdp_client.py           # CDP 客户端
├── config.py               # 配置管理
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
- `rpc_server.py` - **RPC 服务器**（核心服务）
- `rpc_client.py` - **RPC 客户端**（Python API）
- `cdp_client.py` - **浏览器控制核心**（CDP 封装，反检测集成）
- `spider_pb2.py`, `spider_pb2_grpc.py` - 生成的 gRPC 代码

**扩展功能**:
- `gateway.py` - 统一网关，负责路由和负载均衡（可选）
- `http_server.py` - Worker 节点的 HTTP API 服务（可选）
- `http_client.py` - HTTP 客户端（可选）
- `core/registry.py` - 服务注册与发现（分布式架构）
- `core/metrics.py` - Prometheus 监控指标（监控增强）

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

