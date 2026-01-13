---
status: complete
created: '2026-01-09'
tags:
  - refactoring
  - structure
  - maintenance
priority: medium
created_at: '2026-01-09T10:22:53.598Z'
updated_at: '2026-01-09T10:29:53.419Z'
transitions:
  - status: in-progress
    at: '2026-01-09T10:24:01.708Z'
  - status: complete
    at: '2026-01-09T10:29:53.419Z'
completed_at: '2026-01-09T10:29:53.419Z'
completed: '2026-01-09'
---

# directory-structure-optimization

> **Status**: ✅ Complete · **Priority**: Medium · **Created**: 2026-01-09 · **Tags**: refactoring, structure, maintenance

## Overview

当前项目根目录包含大量 Python 文件（gateway.py, http_server.py, rpc_server.py, rpc_client.py, cdp_client.py, config.py 等），导致目录结构混乱，不利于代码维护和扩展。

**问题**:
- 根目录文件过多，缺乏清晰的模块组织
- 核心代码、服务器、客户端代码混在一起
- 生成的 proto 文件（spider_pb2.py, spider_pb2_grpc.py）位于根目录
- 缺乏标准的 Python 包结构

**目标**:
- 创建清晰的模块化目录结构
- 将相关代码组织到合适的包中
- 保持向后兼容，确保现有脚本和配置正常工作
- 遵循 Python 最佳实践

## Design

### 目标目录结构

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
├── proto/                   # Proto 定义（保持不变）
├── scripts/                 # 脚本（保持不变）
├── docs/                   # 文档（保持不变）
├── specs/                  # 规范（保持不变）
├── static/                 # 静态文件（保持不变）
├── resources/              # 资源文件（保持不变）
├── monitoring/             # 监控配置（保持不变）
├── k8s/                    # K8s 配置（保持不变）
├── gateway.py              # 入口脚本（向后兼容）
├── http_server.py          # 入口脚本（向后兼容）
├── rpc_server.py           # 入口脚本（向后兼容）
├── rpc_client.py           # 入口脚本（向后兼容）
├── requirements.txt
├── docker-compose.yml
└── Dockerfile
```

### 设计原则

1. **向后兼容**: 根目录保留入口脚本，通过导入新包结构实现功能
2. **模块化**: 按功能将代码组织到 client/, server/, core/ 子包
3. **清晰分离**: 客户端、服务器、核心功能明确分离
4. **标准结构**: 遵循 Python 包结构最佳实践

## Plan

### Phase 1: 创建新的包结构
- [ ] 创建 `src/browser_rpc/` 主包目录
- [ ] 创建 `src/browser_rpc/client/` 子包
- [ ] 创建 `src/browser_rpc/server/` 子包
- [ ] 创建 `src/browser_rpc/core/` 子包（移动现有 core/）
- [ ] 创建 `src/browser_rpc/proto_gen/` 子包

### Phase 2: 移动核心代码
- [ ] 移动 `cdp_client.py` → `src/browser_rpc/core/cdp_client.py`
- [ ] 移动 `config.py` → `src/browser_rpc/core/config.py`
- [ ] 移动 `core/metrics.py` → `src/browser_rpc/core/metrics.py`
- [ ] 移动 `core/registry.py` → `src/browser_rpc/core/registry.py`

### Phase 3: 移动服务器代码
- [ ] 移动 `rpc_server.py` → `src/browser_rpc/server/rpc_server.py`
- [ ] 移动 `http_server.py` → `src/browser_rpc/server/http_server.py`
- [ ] 移动 `gateway.py` → `src/browser_rpc/server/gateway.py`

### Phase 4: 移动客户端代码
- [ ] 移动 `rpc_client.py` → `src/browser_rpc/client/rpc_client.py`
- [ ] 移动 `http_client.py` → `src/browser_rpc/client/http_client.py`

### Phase 5: 移动生成的 Proto 文件
- [ ] 移动 `spider_pb2.py` → `src/browser_rpc/proto_gen/spider_pb2.py`
- [ ] 移动 `spider_pb2_grpc.py` → `src/browser_rpc/proto_gen/spider_pb2_grpc.py`
- [ ] 更新 proto 编译脚本，输出到新位置

### Phase 6: 更新导入路径
- [ ] 更新所有模块内的相对导入
- [ ] 更新 `__init__.py` 文件，导出主要接口
- [ ] 确保所有内部导入使用新路径

### Phase 7: 创建向后兼容的入口脚本
- [ ] 在根目录创建 `gateway.py`（导入并启动新包中的 gateway）
- [ ] 在根目录创建 `http_server.py`（导入并启动新包中的 http_server）
- [ ] 在根目录创建 `rpc_server.py`（导入并启动新包中的 rpc_server）
- [ ] 在根目录创建 `rpc_client.py`（导入新包中的 rpc_client）

### Phase 8: 更新配置和脚本
- [ ] 更新 `Dockerfile` 中的路径引用
- [ ] 更新 `docker-compose.yml` 中的命令（如果需要）
- [ ] 更新 `scripts/` 中的脚本路径引用
- [ ] 更新 `k8s/` 配置中的路径引用

### Phase 9: 更新文档
- [ ] 更新 `README.md` 中的项目结构说明
- [ ] 更新 `docs/project_structure.md`
- [ ] 更新所有文档中的导入示例

## Test

### 功能测试
- [ ] 验证 RPC 服务器可以正常启动
- [ ] 验证 HTTP 服务器可以正常启动
- [ ] 验证 Gateway 可以正常启动
- [ ] 验证 RPC 客户端可以正常连接和使用
- [ ] 验证 HTTP 客户端可以正常使用
- [ ] 验证所有现有脚本仍然可以正常工作

### 集成测试
- [ ] 运行 `scripts/test_gateway_local.py` 确保通过
- [ ] 运行 `scripts/test_http_api.py` 确保通过
- [ ] 运行 `scripts/test_local_cluster.py` 确保通过
- [ ] 验证 Docker Compose 可以正常启动所有服务

### 导入测试
- [ ] 验证所有模块可以正确导入
- [ ] 验证向后兼容的入口脚本可以正常工作
- [ ] 验证现有代码中的导入路径仍然有效（通过兼容层）

## Notes

### 考虑事项
- 保持向后兼容性至关重要，避免破坏现有部署
- 需要更新所有内部导入路径
- Proto 文件编译路径需要调整
- Docker 镜像构建可能需要调整工作目录

### 迁移策略
1. 先创建新结构并移动文件
2. 更新所有导入路径
3. 创建兼容层入口脚本
4. 测试确保一切正常
5. 更新文档

### 风险评估
- **低风险**: 代码移动和重组
- **中风险**: 导入路径更新可能遗漏某些引用
- **缓解措施**: 全面测试，保持向后兼容入口
