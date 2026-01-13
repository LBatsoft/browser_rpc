# LeanSpec MCP 设置和问题排查

## MCP 配置

项目已配置 LeanSpec MCP 服务器（`.mcp.json`）：

```json
{
  "mcpServers": {
    "lean-spec": {
      "command": "npx",
      "args": [
        "-y",
        "@leanspec/mcp",
        "--project",
        "${workspaceFolder}"
      ]
    }
  }
}
```

## 可用的 MCP 工具

根据 `AGENTS.md`，LeanSpec MCP 提供以下工具：

| MCP Tool | 功能 | CLI 等价命令 |
|----------|------|-------------|
| `board` | 查看项目状态 | `lean-spec board` |
| `list` | 列出所有规范 | `lean-spec list` |
| `search` | 搜索规范 | `lean-spec search "query"` |
| `view` | 查看规范详情 | `lean-spec view <spec>` |
| `create` | 创建新规范 | `lean-spec create <name>` |
| `update` | 更新规范状态 | `lean-spec update <spec> --status <status>` |
| `link` | 链接依赖 | `lean-spec link <spec> --depends-on <other>` |
| `unlink` | 取消链接 | `lean-spec unlink <spec> --depends-on <other>` |
| `deps` | 查看依赖 | `lean-spec deps <spec>` |
| `tokens` | 查看 token 数 | `lean-spec tokens <spec>` |

## 当前规范文件

规范文件位于 `specs/` 目录：

1. `001-browser-rpc-core.md` - status: complete
2. `002-distributed-architecture.md` - status: complete
3. `003-monitoring-observability.md` - status: complete
4. `004-region-aware-routing.md` - status: complete
5. `005-kubernetes-deployment.md` - status: complete
6. `006-future-enhancements.md` - status: planned

## UI 看不到任务的可能原因

### 1. 所有规范都是 `complete` 状态

**问题**: UI 可能默认只显示 `planned` 或 `in-progress` 状态的任务。

**解决**: 
- 已创建 `006-future-enhancements.md`（planned 状态）
- 如果仍看不到，可能需要将某些规范状态改为 `in-progress`

### 2. 规范文件格式问题

**检查点**:
- frontmatter 格式是否正确（YAML 格式）
- 文件编码（应该是 UTF-8）
- 文件扩展名（应该是 `.md`）

### 3. MCP 服务器未正确连接

**检查**:
- MCP 服务器是否已启动
- Cursor/IDE 是否正确配置 MCP
- 检查 MCP 服务器日志

## 使用 MCP 工具查看

如果 MCP 服务器已正确连接，可以使用以下方式查看：

1. **查看项目看板**:
   ```
   使用 MCP 工具: board
   ```

2. **列出所有规范**:
   ```
   使用 MCP 工具: list
   ```

3. **查看特定规范**:
   ```
   使用 MCP 工具: view 001-browser-rpc-core
   ```

## 验证步骤

1. **检查规范文件是否存在**:
   ```bash
   ls -la specs/*.md
   ```

2. **验证规范格式**:
   ```bash
   lean-spec validate
   ```

3. **查看所有规范**:
   ```bash
   lean-spec list
   ```

4. **查看看板**:
   ```bash
   lean-spec board
   ```

## 如果仍然看不到

1. **检查 MCP 服务器状态**
   - 确认 MCP 服务器已启动
   - 检查 Cursor/IDE 的 MCP 配置

2. **检查规范文件**
   - 确认文件在 `specs/` 目录
   - 确认 frontmatter 格式正确
   - 确认文件编码正确

3. **尝试重新初始化**
   ```bash
   lean-spec init -y
   ```

4. **检查配置**
   - `.lean-spec/config.json` 中的 `specsDir` 是否正确
   - 确认路径配置正确

## 快速测试

创建一个新的测试规范：

```bash
lean-spec create test-spec --tags test --priority low
```

然后检查 UI 是否显示。

