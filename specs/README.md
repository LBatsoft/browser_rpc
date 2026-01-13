# Browser RPC - SDD 规范文档

本文档目录包含所有基于 LeanSpec 的软件设计文档（SDD）。

## ⚠️ 重要提示

**所有规范必须使用 `lean-spec create` 工具创建**，手动创建的文件不会被 LeanSpec 识别。

## 创建规范

使用以下命令创建新规范：

```bash
# 创建规范
lean-spec create <name> --tags <tag1,tag2> --priority <high|medium|low>

# 查看项目状态
lean-spec board

# 列出所有规范
lean-spec list

# 查看规范详情
lean-spec view <name>

# 更新规范状态
lean-spec update <name> --status <planned|in-progress|complete>

# 链接依赖
lean-spec link <spec> --depends-on <other-spec>
```

## 规范列表

规范将在此列出（使用 `lean-spec list` 查看）。

## 工作流程

### 创建新规范

1. **发现**: 使用 `lean-spec board` 查看项目状态
2. **搜索**: 使用 `lean-spec search "query"` 查找相关规范
3. **创建**: 使用 `lean-spec create <name>` 创建新规范
4. **开发**: 更新状态为 `in-progress`，开始实现
5. **完成**: 实现完成后更新状态为 `complete`

### 更新规范

- **状态变更**: 使用 `lean-spec update <spec> --status <status>`
- **链接依赖**: 使用 `lean-spec link <spec> --depends-on <other>`
- **查看依赖**: 使用 `lean-spec deps <spec>`

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

## 相关文档

- [AGENTS.md](../AGENTS.md) - AI Agent 使用指南
- [LeanSpec 指南](../docs/lean-spec-guide.md) - 详细使用文档
- [重新创建指南](../docs/lean-spec-recreate-guide.md) - 如何正确创建规范
