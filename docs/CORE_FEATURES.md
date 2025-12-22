# 核心功能文档

## 项目核心

**Browser RPC** 的核心是提供**浏览器自动化 RPC 服务**，通过 gRPC 接口远程控制浏览器，实现高性能的浏览器自动化能力。

## 核心架构

```
┌─────────────────┐
│  RPC Client     │  ← 客户端调用
│  (rpc_client.py)│
└────────┬────────┘
         │ gRPC
         ▼
┌─────────────────┐
│  RPC Server     │  ← 核心服务
│  (rpc_server.py)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CDP Client     │  ← 浏览器控制核心
│  (cdp_client.py)│
└────────┬────────┘
         │ Chrome DevTools Protocol
         ▼
┌─────────────────┐
│  Chromium       │  ← 实际浏览器
│  (Playwright)   │
└─────────────────┘
```

## 核心组件

### 1. gRPC 服务定义 (`proto/spider.proto`)

定义了 13 个核心 RPC 接口：

| 接口 | 功能 | 说明 |
|------|------|------|
| `CreateSession` | 创建浏览器会话 | 支持无头模式、自定义 UA、代理 |
| `CloseSession` | 关闭会话 | 清理资源 |
| `Navigate` | 页面导航 | 支持超时、重定向 |
| `ExecuteScript` | 执行 JavaScript | 返回执行结果 |
| `GetPageContent` | 获取页面 HTML | 完整页面源码 |
| `GetNetworkRequests` | 网络拦截 | 捕获所有请求/响应 |
| `WaitForElement` | 等待元素 | CSS 选择器 |
| `ClickElement` | 点击元素 | 支持各种元素 |
| `TypeText` | 输入文本 | 模拟键盘输入 |
| `TakeScreenshot` | 截图 | 支持全页/元素截图 |
| `SetHeaders` | 设置请求头 | 自定义 HTTP 头 |
| `SetCookies` | 设置 Cookie | 批量设置 |
| `GetCookies` | 获取 Cookie | 获取当前 Cookie |

### 2. RPC 服务器 (`rpc_server.py`)

- **BrowserServiceImpl**: 实现所有 RPC 接口
- **BrowserPool**: 管理浏览器会话池
- 支持多会话并发
- 自动资源清理

### 3. RPC 客户端 (`rpc_client.py`)

- **BrowserRPCClient**: 提供简洁的 Python API
- 异步接口，高性能
- 自动连接管理
- 错误处理

### 4. CDP 客户端 (`cdp_client.py`)

**这是真正的核心**，负责：

- **BrowserSession**: 单个浏览器会话管理
  - 页面导航
  - JavaScript 执行
  - 元素操作
  - 网络拦截
  - 截图功能
  
- **BrowserPool**: 会话池管理
  - 会话创建/销毁
  - 资源限制
  - 超时管理
  - 反检测集成

- **反检测能力**:
  - playwright-stealth 集成
  - 自定义反检测脚本
  - WebDriver 特征隐藏
  - 指纹一致性

## 核心能力

### 1. 浏览器会话管理

```python
from rpc_client import BrowserRPCClient

client = BrowserRPCClient()
await client.connect()

# 创建会话（支持自定义配置）
session_id = await client.create_session(
    headless=True,
    user_agent="Mozilla/5.0...",
    proxy=["http://proxy:8080"],
    width=1920,
    height=1080
)
```

### 2. 页面操作

```python
# 导航
await client.navigate('https://example.com', timeout=30)

# 获取内容
html = await client.get_page_content()

# 执行脚本
result = await client.execute_script("document.title")
```

### 3. 元素操作

```python
# 等待元素
await client.wait_for_element('button#submit', timeout=10)

# 点击
await client.click_element('button#submit')

# 输入
await client.type_text('input#username', 'myname')
```

### 4. 网络拦截

```python
# 获取所有网络请求
requests = await client.get_network_requests()

# 按 URL 模式过滤
api_requests = await client.get_network_requests(
    url_pattern=r'/api/.*'
)

# 查看请求详情
for req in requests:
    print(f"{req['method']} {req['url']}")
    print(f"Status: {req['status_code']}")
    print(f"Body: {req['response_body']}")
```

### 5. 反检测

自动集成反检测能力：
- ✅ 隐藏 `navigator.webdriver`
- ✅ 模拟真实浏览器特征
- ✅ WebGL 指纹一致性
- ✅ 权限状态模拟

## 使用场景

### 场景 1: 数据采集

```python
client = BrowserRPCClient()
await client.connect()
await client.create_session(headless=True)

# 访问页面
await client.navigate('https://target-site.com')

# 等待内容加载
await client.wait_for_element('.content', timeout=30)

# 获取数据
html = await client.get_page_content()
# 解析数据...

await client.close()
```

### 场景 2: API 拦截

```python
await client.navigate('https://spa-app.com')

# 拦截 API 请求
requests = await client.get_network_requests(
    url_pattern=r'/api/.*'
)

# 提取数据
for req in requests:
    if req['status_code'] == 200:
        data = json.loads(req['response_body'])
        # 处理数据...
```

### 场景 3: 自动化测试

```python
await client.create_session(headless=False)  # 可视化模式
await client.navigate('https://app.com/login')

# 登录流程
await client.type_text('#username', 'user')
await client.type_text('#password', 'pass')
await client.click_element('#login-btn')

# 验证
await client.wait_for_element('.dashboard')
screenshot = await client.take_screenshot()
```

## 性能特性

1. **多会话并发**: 支持同时管理多个浏览器会话
2. **资源池化**: 自动管理浏览器资源
3. **异步接口**: 基于 asyncio，高性能
4. **连接复用**: gRPC 长连接，低延迟

## 扩展功能

虽然核心是 RPC，但项目还提供了：

- **HTTP API** (`http_server.py`): 为了易用性，提供 RESTful 接口
- **Gateway** (`gateway.py`): 分布式架构，负载均衡
- **监控** (`core/metrics.py`): Prometheus 指标
- **Web UI** (`static/remote.html`): 可视化控制界面

但这些是**可选的增强功能**，核心始终是 **Browser RPC 能力**。

## 快速开始（核心功能）

### 1. 启动 RPC 服务器

```bash
python rpc_server.py
```

默认端口: `50051`

### 2. 使用 RPC 客户端

```python
import asyncio
from rpc_client import BrowserRPCClient

async def main():
    client = BrowserRPCClient()
    await client.connect()
    
    # 使用核心功能
    await client.create_session(headless=True)
    await client.navigate('https://example.com')
    content = await client.get_page_content()
    
    print(content)
    
    await client.close()

asyncio.run(main())
```

## 核心文件清单

- `proto/spider.proto` - RPC 接口定义
- `rpc_server.py` - RPC 服务器实现
- `rpc_client.py` - RPC 客户端
- `cdp_client.py` - **浏览器控制核心**
- `spider_pb2.py`, `spider_pb2_grpc.py` - 生成的 gRPC 代码

## 总结

**Browser RPC** 的核心价值在于：
1. ✅ **高性能**: gRPC + 异步 + 连接池
2. ✅ **易用性**: 简洁的 Python API
3. ✅ **反检测**: 强大的反检测能力
4. ✅ **功能完整**: 13 个核心接口覆盖所有需求
5. ✅ **可扩展**: 支持分布式部署（可选）

Gateway、HTTP API、监控等都是**可选的增强功能**，核心始终是 **Browser RPC 服务**。

