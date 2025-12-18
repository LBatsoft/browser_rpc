# 反风控策略优化指南

## 当前已实现的增强功能

### 1. 浏览器指纹伪装
- ✅ 真实的 Chrome User-Agent
- ✅ 完整的 HTTP Headers（Accept-Language, Accept-Encoding 等）
- ✅ WebGL 指纹伪装（Intel Inc. / Intel Iris）
- ✅ Canvas 指纹随机化（添加噪声）
- ✅ Screen 参数完善
- ✅ Navigator 属性完善（hardwareConcurrency, deviceMemory 等）
- ✅ 时区和语言设置（Asia/Shanghai, zh-CN）

### 2. 行为模拟
- ✅ 随机延迟（0.5-2秒）在导航前
- ✅ 页面加载后随机鼠标移动
- ✅ playwright-stealth 完整补丁

## 针对严格风控（如小红书）的进一步优化建议

### 方案 1: 使用住宅代理 IP（推荐）

**问题**：数据中心 IP（如 AWS、阿里云）容易被标记。

**解决方案**：
```python
# 在创建会话时传入代理
client = BrowserHTTPClient(base_url='http://localhost:8000')
await client.create_session(
    headless=True,
    proxy={'server': 'http://your-residential-proxy:port'}
)
```

**推荐代理服务**：
- 住宅代理：Bright Data, Smartproxy, Oxylabs
- 移动代理：对于移动端检测更有效

### 方案 2: 添加 Cookies 和 Session

**问题**：首次访问容易被标记为新用户。

**解决方案**：
```python
# 在导航前设置 cookies
await client.set_cookies([
    {
        'name': 'session_id',
        'value': 'your_session_value',
        'domain': '.xiaohongshu.com',
        'path': '/',
        'secure': True,
        'httpOnly': True
    }
])
```

**获取 Cookies 方法**：
1. 手动登录一次，导出 cookies
2. 使用浏览器插件（如 EditThisCookie）导出
3. 通过正常浏览器访问后，使用 DevTools 复制 cookies

### 方案 3: 使用移动端 User-Agent

**问题**：某些网站对移动端检测更宽松。

**解决方案**：
```python
# 使用移动端 UA
mobile_ua = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
)

await client.create_session(
    headless=True,
    user_agent=mobile_ua,
    width=375,  # iPhone 宽度
    height=812   # iPhone 高度
)
```

### 方案 4: 增加访问预热

**问题**：直接访问目标网站容易被识别。

**解决方案**：
```python
# 先访问一些常见网站，建立"正常"访问历史
warmup_urls = [
    'https://www.baidu.com',
    'https://www.google.com',
    'https://www.zhihu.com'
]

for url in warmup_urls:
    await client.navigate(url)
    await asyncio.sleep(random.uniform(2, 5))  # 模拟阅读时间

# 然后再访问目标网站
await client.navigate('https://www.xiaohongshu.com')
```

### 方案 5: 降低访问频率

**问题**：高频访问容易被限流。

**解决方案**：
- 在请求之间添加随机延迟（5-30秒）
- 使用队列系统，控制并发数
- 实现指数退避重试策略

### 方案 6: 使用真实浏览器环境（非 Headless）

**问题**：Headless 模式更容易被检测。

**解决方案**：
```python
# 设置 headless=False（需要 Xvfb 在服务器上）
await client.create_session(headless=False)
```

**注意**：在 Docker 中需要安装 Xvfb：
```dockerfile
RUN apt-get install -y xvfb
ENV DISPLAY=:99
CMD ["Xvfb", ":99", "-screen", "0", "1920x1080x24"] &
```

## 检测和调试

### 检查当前指纹
```python
fingerprint = await client.execute_script("""
    return {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        languages: navigator.languages,
        webdriver: navigator.webdriver,
        plugins: Array.from(navigator.plugins).map(p => p.name),
        screen: {
            width: screen.width,
            height: screen.height,
            colorDepth: screen.colorDepth
        },
        hardwareConcurrency: navigator.hardwareConcurrency,
        deviceMemory: navigator.deviceMemory
    };
""")
print(json.dumps(fingerprint, indent=2))
```

### 测试反检测效果
访问以下检测网站：
- https://bot.sannysoft.com/
- https://arh.antoinevastel.com/bots/areyouheadless
- https://pixelscan.net/

## 最佳实践总结

1. **组合使用**：代理 + Cookies + 预热 + 延迟
2. **环境隔离**：每个任务使用独立的浏览器会话
3. **监控告警**：检测到风控时自动切换策略
4. **成本平衡**：住宅代理成本较高，根据需求选择

## 紧急应对措施

如果遇到风控：
1. **立即停止**：避免 IP 被永久封禁
2. **更换代理**：使用新的住宅 IP
3. **清理痕迹**：删除 cookies，更换 User-Agent
4. **降低频率**：增加延迟，减少并发

