# 快速重新创建规范

由于 shell 环境限制，已创建自动化脚本。请执行以下命令：

## 方式 1: 使用脚本（推荐）

```bash
./scripts/recreate_specs.sh
```

## 方式 2: 手动执行命令

如果脚本无法执行，请手动运行以下命令：

```bash
# 1. 创建核心 RPC 服务规范
lean-spec create browser-rpc-core --tags core,rpc,browser-automation --priority high

# 2. 创建分布式架构规范
lean-spec create distributed-architecture --tags architecture,gateway,load-balancing --priority medium
lean-spec link distributed-architecture --depends-on browser-rpc-core

# 3. 创建监控规范
lean-spec create monitoring-observability --tags monitoring,prometheus,observability --priority medium
lean-spec link monitoring-observability --depends-on browser-rpc-core
lean-spec link monitoring-observability --depends-on distributed-architecture

# 4. 创建地域路由规范
lean-spec create region-aware-routing --tags routing,region,zone --priority low
lean-spec link region-aware-routing --depends-on distributed-architecture

# 5. 创建 K8s 部署规范
lean-spec create kubernetes-deployment --tags k8s,deployment,infrastructure --priority medium
lean-spec link kubernetes-deployment --depends-on distributed-architecture
lean-spec link kubernetes-deployment --depends-on monitoring-observability

# 6. 更新已完成规范的状态
lean-spec update browser-rpc-core --status complete
lean-spec update distributed-architecture --status complete
lean-spec update monitoring-observability --status complete
lean-spec update region-aware-routing --status complete
lean-spec update kubernetes-deployment --status complete

# 7. 验证
lean-spec board
lean-spec list
```

## 验证

执行完成后，运行：

```bash
lean-spec board
```

应该能看到所有创建的规范。

