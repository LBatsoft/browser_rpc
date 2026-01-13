# 修复规范链接

## 问题

lean-spec 创建规范时使用目录结构，规范名称会自动添加编号前缀（如 `001-browser-rpc-core`）。在链接依赖时需要使用正确的规范名称。

## 解决方案

如果链接命令失败，可以手动链接。首先查看实际的规范名称：

```bash
lean-spec list
```

然后使用正确的名称链接：

```bash
# 查看规范名称（例如：001-browser-rpc-core, 002-distributed-architecture）
lean-spec list

# 使用正确的名称链接（替换为实际的规范名称）
lean-spec link 002-distributed-architecture --depends-on 001-browser-rpc-core
lean-spec link 003-monitoring-observability --depends-on 001-browser-rpc-core
lean-spec link 003-monitoring-observability --depends-on 002-distributed-architecture
lean-spec link 004-region-aware-routing --depends-on 002-distributed-architecture
lean-spec link 005-kubernetes-deployment --depends-on 002-distributed-architecture
lean-spec link 005-kubernetes-deployment --depends-on 003-monitoring-observability
```

## 或者使用规范目录名称

也可以尝试使用目录名称（不带编号前缀）：

```bash
lean-spec link distributed-architecture --depends-on browser-rpc-core
```

如果这不起作用，请先运行 `lean-spec list` 查看实际的规范名称。

