# LeanSpec UI 问题排查

## 问题：UI 看不到任务

### 可能原因

1. **所有规范状态都是 `complete`**
   - LeanSpec UI 默认可能只显示 `planned` 或 `in-progress` 状态的任务
   - 已完成的规范可能不会在任务看板中显示

2. **规范文件格式问题**
   - frontmatter 格式不正确
   - 文件编码问题

3. **UI 未正确启动**
   - 端口冲突
   - 缓存问题

## 解决方案

### 方案 1: 检查规范状态

查看所有规范的状态：

```bash
lean-spec list
```

如果所有规范都是 `complete`，UI 可能不会显示它们。可以：

1. **创建新的规划中任务**：
   ```bash
   lean-spec create new-feature --tags feature --priority high
   ```

2. **或者将某些规范状态改为 `planned`**（如果它们还需要后续工作）：
   ```bash
   lean-spec update 001-browser-rpc-core --status planned
   ```

### 方案 2: 启动 UI 并检查

```bash
# 启动 UI（默认端口 3000）
lean-spec ui

# 如果端口被占用，使用其他端口
lean-spec ui --port 3100

# 指定规范目录
lean-spec ui --specs ./specs
```

### 方案 3: 验证规范文件

```bash
# 验证所有规范文件
lean-spec validate

# 查看项目看板
lean-spec board
```

### 方案 4: 检查配置

确保 `.lean-spec/config.json` 配置正确：

```json
{
  "specsDir": "specs",
  "templatesDir": ".lean-spec/templates",
  "defaultStatus": "planned",
  "defaultPriority": "medium"
}
```

## 当前规范状态

所有现有规范都是 `complete` 状态：

- `001-browser-rpc-core` - ✅ complete
- `002-distributed-architecture` - ✅ complete
- `003-monitoring-observability` - ✅ complete
- `004-region-aware-routing` - ✅ complete
- `005-kubernetes-deployment` - ✅ complete

## 建议

1. **创建新的规划任务**：如果有新的功能需求，创建 `planned` 状态的规范
2. **查看所有规范**：使用 `lean-spec list` 查看所有规范（包括已完成的）
3. **使用 board 视图**：`lean-spec board` 可能显示所有状态的规范

## 快速测试

```bash
# 1. 查看所有规范
lean-spec list

# 2. 查看看板
lean-spec board

# 3. 创建测试规范（planned 状态）
lean-spec create test-spec --tags test --priority low

# 4. 启动 UI
lean-spec ui
```

## 如果仍然看不到

1. 检查浏览器控制台是否有错误
2. 检查 `specs/` 目录是否存在且包含规范文件
3. 检查规范文件的 frontmatter 格式是否正确
4. 尝试清除缓存或重启 UI

