# LeanSpec SDD 使用指南

## ⚠️ 重要提示

根据 `AGENTS.md` 的要求，**所有规范变更都应该使用 lean-spec 工具**，而不是手动编辑文件。

## 已创建的规范

以下规范已创建（作为初始基础）：

1. `001-browser-rpc-core.md` - 核心 RPC 服务
2. `002-distributed-architecture.md` - 分布式架构
3. `003-monitoring-observability.md` - 监控与可观测性
4. `004-region-aware-routing.md` - 地域感知路由
5. `005-kubernetes-deployment.md` - Kubernetes 部署

## 后续工作流程

### 查看项目状态

```bash
lean-spec board
```

### 搜索规范

```bash
lean-spec search "monitoring"
lean-spec search "rpc"
```

### 查看规范

```bash
lean-spec view 001-browser-rpc-core
```

### 更新规范状态

```bash
# 开始实现
lean-spec update 001-browser-rpc-core --status in-progress

# 完成实现
lean-spec update 001-browser-rpc-core --status complete
```

### 链接依赖

```bash
lean-spec link 002-distributed-architecture --depends-on 001-browser-rpc-core
```

### 创建新规范

```bash
lean-spec create new-feature --tags feature --priority high
```

## 规范管理原则

1. **不要手动编辑 frontmatter** - 使用 `update`、`link`、`unlink` 工具
2. **创建前先搜索** - 避免重复工作
3. **跟踪状态转换** - `planned` → `in-progress` → `complete`
4. **链接依赖关系** - 使用 `depends_on` 表达规范间的依赖

## 规范状态

- `planned` - 计划中
- `in-progress` - 进行中
- `complete` - 已完成
- `blocked` - 被阻塞
- `cancelled` - 已取消

## 后续变更原则

**所有代码变更必须基于规范**:

1. ✅ 新功能 → 先创建规范 (`lean-spec create`)
2. ✅ 修改功能 → 更新相关规范 (`lean-spec update`)
3. ✅ Bug 修复 → 检查是否影响规范
4. ✅ 重构 → 更新架构规范

## 注意事项

当前已创建的规范文件是**初始基础**，后续应该：
- 使用 `lean-spec update` 更新状态和元数据
- 使用 `lean-spec link` 管理依赖关系
- 不要手动编辑 frontmatter（YAML 头部）

如果需要修改规范内容（非 frontmatter），可以直接编辑 Markdown 内容部分。

