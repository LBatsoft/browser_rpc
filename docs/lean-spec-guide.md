# LeanSpec SDD 使用指南

## 概述

项目已采用 **LeanSpec** 进行规范驱动开发（SDD），所有后续变更都应基于规范文档。

## 规范目录

所有规范文档位于 `specs/` 目录：

- `001-browser-rpc-core.md` - 核心 RPC 服务
- `002-distributed-architecture.md` - 分布式架构
- `003-monitoring-observability.md` - 监控与可观测性
- `004-region-aware-routing.md` - 地域感知路由
- `005-kubernetes-deployment.md` - Kubernetes 部署

## 工作流程

### 1. 开始新功能

```bash
# 1. 查看项目状态
lean-spec board

# 2. 搜索相关规范
lean-spec search "keyword"

# 3. 创建新规范
lean-spec create feature-name --tags feature --priority high

# 4. 开始实现前更新状态
lean-spec update feature-name --status in-progress
```

### 2. 修改现有功能

```bash
# 1. 查看相关规范
lean-spec view spec-name

# 2. 检查依赖
lean-spec deps spec-name

# 3. 更新状态
lean-spec update spec-name --status in-progress
```

### 3. 完成功能

```bash
# 更新状态为完成
lean-spec update spec-name --status complete
```

## 核心规则

### ⚠️ 禁止操作

1. **不要手动编辑 frontmatter**（YAML 头部）
   - 使用 `lean-spec update` 更新状态、优先级、标签
   - 使用 `lean-spec link` 管理依赖

2. **不要跳过发现步骤**
   - 创建规范前先运行 `lean-spec board` 和 `lean-spec search`

3. **不要手动创建规范文件**
   - 使用 `lean-spec create` 工具

### ✅ 正确操作

1. **使用工具管理元数据**
   ```bash
   lean-spec update spec-name --status in-progress
   lean-spec link spec-a --depends-on spec-b
   ```

2. **规范内容可以手动编辑**
   - Markdown 内容部分可以直接编辑
   - 但 frontmatter 必须使用工具

3. **跟踪状态转换**
   - `planned` → `in-progress` → `complete`

## 规范格式

每个规范文件包含：

```markdown
---
status: complete          # 状态（使用工具更新）
priority: high            # 优先级（使用工具更新）
tags: [core, rpc]         # 标签（使用工具更新）
depends_on: []            # 依赖（使用工具更新）
created: 2025-01-09       # 创建时间（自动）
updated: 2025-01-09       # 更新时间（自动）
---

# 规范标题

## 目标
...

## 关键场景
...

## 验收标准
...
```

## 依赖管理

使用 `depends_on` 表达规范间的依赖关系：

```bash
# 链接依赖
lean-spec link spec-a --depends-on spec-b

# 查看依赖
lean-spec deps spec-a

# 取消依赖
lean-spec unlink spec-a --depends-on spec-b
```

## 何时创建规范

| ✅ 需要规范 | ❌ 不需要规范 |
|------------|-------------|
| 多部分功能 | Bug 修复 |
| 破坏性变更 | 琐碎变更 |
| 设计决策 | 自解释的重构 |

## Token 阈值

- <2,000 tokens: ✅ 最优
- 2,000-3,500 tokens: ✅ 良好
- 3,500-5,000 tokens: ⚠️ 考虑拆分
- >5,000 tokens: 🔴 必须拆分

## 相关文档

- [AGENTS.md](../AGENTS.md) - AI Agent 使用指南
- [specs/README.md](../specs/README.md) - 规范文档索引
- [LeanSpec 官方文档](https://www.lean-spec.dev/)

