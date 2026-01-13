# LeanSpec 规范重新创建指南

## 问题原因

根据 `AGENTS.md` 的说明：
> **Never create files manually** → Always use `create` tool for new specs
> 
> **Why?** Skipping discovery creates duplicate work. Manual file creation breaks LeanSpec tooling.

手动创建规范文件会破坏 LeanSpec 工具，导致 `lean-spec board` 无法识别这些规范。

## 解决方案

已删除所有手动创建的规范文件。现在需要使用 `lean-spec create` 工具重新创建。

## 重新创建步骤

### 1. 创建核心 RPC 服务规范

```bash
lean-spec create browser-rpc-core --tags core,rpc,browser-automation --priority high
```

然后编辑文件，添加内容。

### 2. 创建分布式架构规范

```bash
lean-spec create distributed-architecture --tags architecture,gateway,load-balancing --priority medium
```

然后：
```bash
lean-spec link distributed-architecture --depends-on browser-rpc-core
```

### 3. 创建监控规范

```bash
lean-spec create monitoring-observability --tags monitoring,prometheus,observability --priority medium
```

然后：
```bash
lean-spec link monitoring-observability --depends-on browser-rpc-core
lean-spec link monitoring-observability --depends-on distributed-architecture
```

### 4. 创建地域路由规范

```bash
lean-spec create region-aware-routing --tags routing,region,zone --priority low
```

然后：
```bash
lean-spec link region-aware-routing --depends-on distributed-architecture
```

### 5. 创建 K8s 部署规范

```bash
lean-spec create kubernetes-deployment --tags k8s,deployment,infrastructure --priority medium
```

然后：
```bash
lean-spec link kubernetes-deployment --depends-on distributed-architecture
lean-spec link kubernetes-deployment --depends-on monitoring-observability
```

## 验证

创建完成后，验证：

```bash
# 查看项目看板
lean-spec board

# 列出所有规范
lean-spec list

# 查看特定规范
lean-spec view browser-rpc-core
```

## 重要提示

1. **始终使用工具创建规范** - 不要手动创建 `.md` 文件
2. **使用工具管理元数据** - 使用 `update`、`link` 等工具管理状态和依赖
3. **内容可以手动编辑** - 但 frontmatter 必须使用工具管理

## 原始内容参考

如果需要参考原始规范内容，可以查看：
- `docs/CORE_FEATURES.md` - 核心功能说明
- `docs/long_term_planning_summary.md` - 长期规划总结
- `docs/code_review.md` - 代码审查记录

