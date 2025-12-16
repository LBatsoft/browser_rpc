# Remote Control 功能问题记录

## 功能概述
实现浏览器远程 GUI 操作能力和任务重放功能。

## 已完成的工作

### 1. 架构设计
- WebSocket 接口 `/ws/sessions/{session_id}` 用于实时通信
- CDP `Page.startScreencast` 实现视频流推送
- CDP `Input.dispatchMouseEvent` / `Input.dispatchKeyEvent` 处理输入事件

### 2. 前端实现 (`static/remote.html`)
- 视频流接收和显示
- 鼠标事件捕获和坐标转换
- 键盘事件捕获
- 录制/重放控制界面
- 调试模式（显示坐标转换信息）

### 3. 后端实现 (`cdp_client.py`, `http_server.py`)
- `start_screencast` / `stop_screencast` 方法
- `handle_input_event` 方法（使用 CDP 原生 Input 事件）
- `replay_events` 方法
- WebSocket 路由处理

## 当前问题

### 问题1: 点击操作不稳定
**现象**: 有的区域可以点击，有的区域无法点击

**可能原因**:
1. 坐标计算仍有偏差
2. CDP screencast 图片尺寸与 viewport 尺寸的关系不确定
3. 高 DPI 屏幕的缩放问题

**已尝试的方案**:
- 使用相对位置计算 `(imgX / rect.width) * deviceWidth`
- 移除图片的 `max-width: 100%` 限制
- 使用 CDP 原生 `Input.dispatchMouseEvent` 替代 Playwright 方法

**待验证**:
- [ ] 检查 CDP screencast metadata 中是否有缩放因子信息
- [ ] 对比 `screen.naturalWidth` 和 `metadata.deviceWidth` 的关系
- [ ] 测试固定 viewport 尺寸是否能解决问题

### 问题2: 键盘输入可能不完整
**现象**: 特殊按键可能无法正确发送

**可能原因**:
- CDP `Input.dispatchKeyEvent` 需要更多参数（如 `code`, `windowsVirtualKeyCode` 等）

**待修复**:
- [ ] 补充键盘事件的完整参数
- [ ] 测试中文输入

## 调试方法

### 前端调试
1. 勾选页面上的"调试"复选框
2. 查看右下角的调试信息：
   - 鼠标位置
   - 图片内位置
   - 图片显示尺寸 vs 原始尺寸
   - viewport 尺寸
   - 发送坐标

### 后端调试
查看服务器日志：
```bash
tail -f log/http_server.log
```

## 下一步计划

1. **深入分析坐标问题**
   - 在调试模式下，对比点击位置和实际响应位置
   - 检查 CDP screencast 的具体行为

2. **完善键盘输入**
   - 参考 Playwright 的键盘事件实现
   - 支持组合键（Ctrl+C 等）

3. **优化用户体验**
   - 降低视频延迟（调整 screencast 参数）
   - 添加加载状态指示

## 相关文件

- `static/remote.html` - 前端控制页面
- `static/test_page.html` - 测试页面
- `cdp_client.py` - CDP 客户端封装
- `http_server.py` - HTTP/WebSocket 服务器

## 参考资料

- [CDP Input Domain](https://chromedevtools.github.io/devtools-protocol/tot/Input/)
- [CDP Page.startScreencast](https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-startScreencast)

