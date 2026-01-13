"""
Chrome DevTools Protocol 客户端封装
支持浏览器控制、网络拦截、数据采集等功能
集成 playwright-stealth 提供全面的反检测能力
"""

import asyncio
import base64
import re
import time
import uuid
from typing import Dict, List, Optional, Any
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
try:
    from playwright_stealth import stealth_async
except ImportError:
    # Fallback for different playwright_stealth versions
    try:
        from playwright_stealth.stealth import stealth_async
    except ImportError:
        # If stealth_async is not available, use a wrapper
        async def stealth_async(page):
            """Fallback stealth function"""
            pass
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
THIRD_PARTY_STEALTH_PATH = BASE_DIR / 'resources' / 'stealth' / 'third_party_stealth.min.js'


class NetworkInterceptor:
    """网络请求拦截器"""
    
    def __init__(self):
        self.requests: List[Dict[str, Any]] = []
        self.url_pattern: Optional[str] = None
    
    def set_url_pattern(self, pattern: str):
        """设置 URL 过滤模式"""
        self.url_pattern = pattern
    
    def clear(self):
        """清空请求记录"""
        self.requests.clear()
    
    async def on_request(self, request):
        """请求拦截回调"""
        try:
            if self.url_pattern and not re.search(self.url_pattern, request.url):
                return
            
            request_data = {
                'request_id': str(uuid.uuid4()),
                'url': request.url,
                'method': request.method,
                'headers': request.headers,
                'post_data': request.post_data if request.method == 'POST' else None,
                'timestamp': time.time(),
                'response': None
            }
            
            self.requests.append(request_data)
        except Exception as e:
            logger.error(f"请求拦截失败: {e}")
    
    async def on_response(self, response):
        """响应拦截回调"""
        try:
            if self.url_pattern and not re.search(self.url_pattern, response.url):
                return
            
            # 查找对应的请求
            for req in self.requests:
                if req['url'] == response.url and req['response'] is None:
                    try:
                        body = await response.body()
                        req['response'] = {
                            'status_code': response.status,
                            'headers': response.headers,
                            'body': body.decode('utf-8', errors='ignore')
                        }
                    except Exception as e:
                        error_msg = str(e)
                        if "No data found" in error_msg or "Target closed" in error_msg:
                            # 忽略预期内的错误，使用 debug 级别
                            logger.debug(f"获取响应体失败 (忽略): {error_msg}")
                        else:
                            logger.warning(f"获取响应体失败: {error_msg}")
                            
                        req['response'] = {
                            'status_code': response.status,
                            'headers': response.headers,
                            'body': None
                        }
                    break
        except Exception as e:
            logger.error(f"响应拦截失败: {e}")
    
    def get_requests(self) -> List[Dict[str, Any]]:
        """获取拦截的请求"""
        return [req for req in self.requests if req.get('response')]


class BrowserSession:
    """浏览器会话管理"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.cdp_session = None
        self.screencast_listener = None
        self.network_interceptor = NetworkInterceptor()
        self.custom_headers: Dict[str, str] = {}
        self.created_at = time.time()
        self.last_activity = time.time()
    
    async def initialize(
        self,
        headless: bool = True,
        user_agent: Optional[str] = None,
        proxy: Optional[Dict[str, str]] = None,
        width: int = 1920,
        height: int = 1080
    ):
        """初始化浏览器会话"""
        try:
            self.playwright = await async_playwright().start()
            
            # 浏览器启动参数（关键：禁用自动化标志）
            launch_options = {
                'headless': headless,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-infobars',
                    '--window-position=0,0',
                    '--ignore-certifcate-errors',
                    '--ignore-certifcate-errors-spki-list',
                ],
                'chromium_sandbox': False,
            }
            
            # 启动浏览器
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # 创建上下文（增强反检测配置）
            # 使用真实的 Chrome User-Agent（如果没有提供）
            default_user_agent = user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            context_options = {
                'viewport': {'width': width, 'height': height},
                'bypass_csp': True,
                'user_agent': default_user_agent,
                # 设置更真实的 HTTP headers
                'extra_http_headers': {
                    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                },
                # 设置更真实的屏幕参数
                'screen': {
                    'width': width,
                    'height': height
                },
                # 设置时区（中国时区）
                'timezone_id': 'Asia/Shanghai',
                # 设置语言
                'locale': 'zh-CN',
            }
            
            if proxy:
                context_options['proxy'] = proxy
            
            self.context = await self.browser.new_context(**context_options)
            
            # 在 context 层面注入脚本，最早移除 webdriver
            await self.context.add_init_script(
                """
Object.defineProperty(Navigator.prototype, 'webdriver', {
    get: () => undefined,
    configurable: true
});
delete Navigator.prototype.webdriver;
                """
            )

            # 注入第三方 stealth 脚本
            if THIRD_PARTY_STEALTH_PATH.exists():
                try:
                    logger.info(f"加载 third_party_stealth: {THIRD_PARTY_STEALTH_PATH}")
                    stealth_js = THIRD_PARTY_STEALTH_PATH.read_text(encoding='utf-8')
                    await self.context.add_init_script(stealth_js)
                    logger.info("third-party stealth.min.js 注入成功")
                except Exception as e:
                    logger.warning(f"third-party stealth.min.js 注入失败: {e}")
            else:
                logger.warning("third-party stealth.min.js 文件不存在，跳过注入")
            
            # 创建页面
            self.page = await self.context.new_page()
            
            # 应用 playwright-stealth 的完整反检测补丁
            await stealth_async(self.page)

            # 增强反检测：额外的指纹伪装
            await self.page.add_init_script("""
                // Canvas 指纹随机化（添加噪声）
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                    const context = this.getContext('2d');
                    if (context) {
                        const imageData = context.getImageData(0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            // 添加微小的随机噪声（不影响视觉）
                            imageData.data[i] += Math.random() * 0.01;
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                    return originalToDataURL.apply(this, arguments);
                };

                // WebGL 指纹伪装
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.apply(this, arguments);
                };

                // 完善 navigator 属性
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });

                // 设置语言
                Object.defineProperty(navigator, 'language', {
                    get: () => 'zh-CN'
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en']
                });

                // 完善 screen 对象
                Object.defineProperty(screen, 'availWidth', {
                    get: () => window.innerWidth || 1920
                });
                Object.defineProperty(screen, 'availHeight', {
                    get: () => window.innerHeight || 1080
                });
                Object.defineProperty(screen, 'colorDepth', {
                    get: () => 24
                });
                Object.defineProperty(screen, 'pixelDepth', {
                    get: () => 24
                });
            """)

            # 调试 webdriver 状态
            info = await self.page.evaluate("""
                () => ({
                    webdriver: navigator.webdriver,
                    has: 'webdriver' in navigator,
                    protoHas: Object.getPrototypeOf(navigator).hasOwnProperty('webdriver')
                })
            """)
            logger.info(f"navigator.webdriver 调试: {info}")
            
            # 设置网络拦截
            self.page.on('request', self.network_interceptor.on_request)
            self.page.on('response', self.network_interceptor.on_response)
            
            self.last_activity = time.time()
            logger.info(f"浏览器会话 {self.session_id} 初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"浏览器会话初始化失败: {e}")
            await self.close()
            raise
    
    async def navigate(self, url: str, timeout: int = 30) -> str:
        """导航到指定 URL（增强反检测：添加人类行为模拟）"""
        if not self.page:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            # 添加随机延迟，模拟人类行为（0.5-2秒）
            import random
            delay = random.uniform(0.5, 2.0)
            await asyncio.sleep(delay)
            
            # 导航时设置更真实的 referer（如果是首次访问则没有 referer）
            response = await self.page.goto(
                url, 
                timeout=timeout * 1000, 
                wait_until='domcontentloaded',
                referer=None  # 首次访问不设置 referer
            )
            
            # 页面加载后，模拟一些人类行为（随机鼠标移动）
            try:
                await asyncio.sleep(random.uniform(0.3, 1.0))
                # 随机移动鼠标到页面中心附近
                await self.page.mouse.move(
                    random.randint(400, 800),
                    random.randint(300, 600)
                )
            except Exception as e:
                logger.debug(f"模拟鼠标移动失败（可忽略）: {e}")
            
            self.last_activity = time.time()
            return self.page.url
        except Exception as e:
            logger.error(f"导航失败: {e}")
            raise
    
    async def execute_script(self, script: str) -> Any:
        """执行 JavaScript"""
        if not self.page:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            result = await self.page.evaluate(script)
            self.last_activity = time.time()
            return result
        except Exception as e:
            logger.error(f"脚本执行失败: {e}")
            raise
            
    async def start_screencast(self, callback):
        """开启屏幕投射"""
        if not self.page:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            # 建立 CDP 会话
            if not self.cdp_session:
                self.cdp_session = await self.context.new_cdp_session(self.page)
            
            # 清理旧的监听器
            if self.screencast_listener:
                self.cdp_session.remove_listener("Page.screencastFrame", self.screencast_listener)
                self.screencast_listener = None

            # 监听 screencast 帧
            async def on_screencast_frame(frame):
                try:
                    # frame 包含 data (base64), sessionId, metadata
                    # 调用回调函数发送给 WebSocket
                    if callback:
                        await callback(frame['data'], frame['metadata'])
                    
                    # 必须确认帧，否则流会停止
                    # 注意：必须使用 frame 中的 sessionId 确认，因为这可能是来自非主页面的帧（如果支持）
                    # 但 Page.screencastFrameAck 需要在开启 screencast 的 session 上发送
                    if self.cdp_session:
                        await self.cdp_session.send("Page.screencastFrameAck", {"sessionId": frame['sessionId']})
                except Exception as e:
                    logger.error(f"Screencast frame error: {e}")

            # 保存并添加新监听器
            self.screencast_listener = on_screencast_frame
            self.cdp_session.on("Page.screencastFrame", self.screencast_listener)
            
            # 开启投射
            await self.cdp_session.send("Page.startScreencast", {
                "format": "jpeg",
                "quality": 80,
                "maxWidth": 1280, # 限制最大宽度，减少传输量
                "maxHeight": 720, # 限制最大高度
                "everyNthFrame": 1
            })
            logger.info(f"Screencast started for session {self.session_id}")
            
            # 监听新页面
            self.context.on("page", self._on_new_page)
            
        except Exception as e:
            logger.error(f"Start screencast failed: {e}")
            raise

    async def _on_new_page(self, page: Page):
        """处理新页面创建"""
        try:
            logger.info(f"New page detected: {page.url}")
            await page.wait_for_load_state()
            
            # 更新当前页面引用
            old_page = self.page
            self.page = page
            
            # 重新应用 stealth
            await stealth_async(self.page)
            
            # 更新网络拦截
            self.page.on('request', self.network_interceptor.on_request)
            self.page.on('response', self.network_interceptor.on_response)
            
            # 切换 CDP 会话到新页面
            # 1. 停止旧页面的 screencast
            if self.cdp_session:
                try:
                    await self.cdp_session.send("Page.stopScreencast")
                    if self.screencast_listener:
                        self.cdp_session.remove_listener("Page.screencastFrame", self.screencast_listener)
                except Exception as e:
                    logger.warning(f"Failed to stop old screencast: {e}")
            
            # 2. 创建新 CDP 会话
            self.cdp_session = await self.context.new_cdp_session(self.page)
            
            # 3. 重新绑定监听器并开启 screencast
            if self.screencast_listener:
                self.cdp_session.on("Page.screencastFrame", self.screencast_listener)
                await self.cdp_session.send("Page.startScreencast", {
                    "format": "jpeg",
                    "quality": 80,
                    "maxWidth": 1280,
                    "maxHeight": 720,
                    "everyNthFrame": 1
                })
                logger.info(f"Screencast switched to new page: {page.url}")
            
            # 通知前端更新标签页
            # 这里需要一种机制通知 WebSocket，目前通过简单的日志或者回调扩展实现
            # 由于没有直接的 ws 引用，这里先依靠前端轮询或后端主动推送（如果设计支持）
            # 暂时只能自动切换，前端看到的会变，但列表没变
                
        except Exception as e:
            logger.error(f"Failed to switch to new page: {e}")

    async def get_pages(self) -> List[Dict[str, str]]:
        """获取所有页面信息"""
        if not self.context:
            return []
        
        pages = []
        for p in self.context.pages:
            try:
                title = await p.title()
            except:
                title = "Loading..."
            
            # 使用 id 作为唯一标识，playwright page 没有公开 id，可以用 guid
            # 这里简单用索引或对象哈希，或者给 page 附加上 id
            if not hasattr(p, '_guid'):
                p._guid = str(uuid.uuid4())
                
            pages.append({
                'id': p._guid,
                'url': p.url,
                'title': title
            })
        return pages

    async def switch_to_page(self, page_id: str):
        """切换到指定页面"""
        if not self.context:
            return
            
        target_page = None
        for p in self.context.pages:
            if hasattr(p, '_guid') and p._guid == page_id:
                target_page = p
                break
        
        if target_page and target_page != self.page:
            logger.info(f"Switching to page {page_id}")
            await self._on_new_page(target_page)

    async def stop_screencast(self):
        """停止屏幕投射"""
        try:
            # 移除页面监听
            if self.context:
                self.context.remove_listener("page", self._on_new_page)

            if self.cdp_session:
                await self.cdp_session.send("Page.stopScreencast")
                
                # 移除监听器
                if self.screencast_listener:
                    self.cdp_session.remove_listener("Page.screencastFrame", self.screencast_listener)
                    self.screencast_listener = None
                    
            logger.info(f"Screencast stopped for session {self.session_id}")
        except Exception as e:
            logger.error(f"Stop screencast failed: {e}")

    async def handle_input_event(self, event: Dict[str, Any]):
        """处理输入事件 - 使用 CDP 原生方法"""
        if not self.page:
            return

        try:
            event_type = event.get('type')
            x = event.get('x', 0)
            y = event.get('y', 0)
            
            # 确保 CDP session 存在
            if not self.cdp_session:
                self.cdp_session = await self.context.new_cdp_session(self.page)
            
            if event_type == 'mousemove':
                await self.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseMoved",
                    "x": x,
                    "y": y,
                    "modifiers": event.get('modifiers', 0)
                })
                
            elif event_type == 'mousedown':
                button = event.get('button', 'left')
                cdp_button = {'left': 'left', 'middle': 'middle', 'right': 'right'}.get(button, 'left')
                buttons = {'left': 1, 'middle': 4, 'right': 2}.get(button, 1)
                
                await self.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mousePressed",
                    "x": x,
                    "y": y,
                    "button": cdp_button,
                    "buttons": buttons,
                    "clickCount": 1,
                    "modifiers": event.get('modifiers', 0)
                })
                
            elif event_type == 'mouseup':
                button = event.get('button', 'left')
                cdp_button = {'left': 'left', 'middle': 'middle', 'right': 'right'}.get(button, 'left')
                
                await self.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseReleased",
                    "x": x,
                    "y": y,
                    "button": cdp_button,
                    "buttons": 0,
                    "clickCount": 1,
                    "modifiers": event.get('modifiers', 0)
                })
                
            elif event_type == 'click':
                # Click is a sequence, we should respect modifiers for all
                button = event.get('button', 'left')
                cdp_button = {'left': 'left', 'middle': 'middle', 'right': 'right'}.get(button, 'left')
                buttons = {'left': 1, 'middle': 4, 'right': 2}.get(button, 1)
                modifiers = event.get('modifiers', 0)
                
                await self.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseMoved",
                    "x": x,
                    "y": y,
                    "modifiers": modifiers
                })
                await self.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mousePressed",
                    "x": x,
                    "y": y,
                    "button": cdp_button,
                    "buttons": buttons,
                    "clickCount": 1,
                    "modifiers": modifiers
                })
                await self.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseReleased",
                    "x": x,
                    "y": y,
                    "button": cdp_button,
                    "buttons": 0,
                    "clickCount": 1,
                    "modifiers": modifiers
                })
                
            elif event_type == 'keydown':
                params = {
                    "type": "keyDown",
                    "key": event.get('key', ''),
                    "code": event.get('code', ''),
                    "modifiers": event.get('modifiers', 0),
                    "windowsVirtualKeyCode": event.get('windowsVirtualKeyCode', 0),
                    "nativeVirtualKeyCode": event.get('nativeVirtualKeyCode', 0),
                    "location": event.get('location', 0),
                    "autoRepeat": False,  # We filter repeats in frontend
                    "isKeypad": event.get('location', 0) == 3
                }
                
                key = event.get('key', '')
                if len(key) == 1:
                    params["text"] = key
                    params["unmodifiedText"] = key
                
                if event.get('commands'): # Optional if we support it later
                    params['commands'] = event.get('commands')
                    
                await self.cdp_session.send("Input.dispatchKeyEvent", params)
                
            elif event_type == 'keyup':
                await self.cdp_session.send("Input.dispatchKeyEvent", {
                    "type": "keyUp",
                    "key": event.get('key', ''),
                    "code": event.get('code', ''),
                    "modifiers": event.get('modifiers', 0),
                    "location": event.get('location', 0)
                })
                
            elif event_type == 'keypress':
                key = event.get('key', '')
                if key:
                    await self.cdp_session.send("Input.dispatchKeyEvent", {
                        "type": "keyDown",
                        "key": key,
                        "text": key if len(key) == 1 else ""
                    })
                    await self.cdp_session.send("Input.dispatchKeyEvent", {
                        "type": "keyUp",
                        "key": key
                    })
                
            elif event_type == 'scroll':
                deltaX = event.get('deltaX', 0)
                deltaY = event.get('deltaY', 0)
                await self.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseWheel",
                    "x": x,
                    "y": y,
                    "deltaX": deltaX,
                    "deltaY": deltaY,
                    "modifiers": event.get('modifiers', 0)
                })
                
            self.last_activity = time.time()
            
        except Exception as e:
            logger.error(f"Handle input event failed: {e}, Event: {event}")

    async def replay_events(self, events: List[dict]):
        """重放事件序列"""
        if not events: return
        
        logger.info(f"开始重放任务，共 {len(events)} 个事件")
        start_time = events[0].get('timestamp', 0)
        
        # 为了保证重放的准确性，使用相对时间
        for i, event in enumerate(events):
            try:
                # 计算需要等待的时间
                if i > 0:
                    prev_time = events[i-1].get('timestamp', 0)
                    curr_time = event.get('timestamp', 0)
                    delay = curr_time - prev_time
                    # 如果间隔太大（比如超过5秒），可能是在思考，可以适当缩短或者按原样等待
                    if delay > 0:
                        await asyncio.sleep(delay)
                
                # 执行操作
                await self.handle_input_event(event)
            except Exception as e:
                logger.error(f"重放事件失败: {e}, index: {i}")
        
        logger.info("任务重放完成")

    
    async def get_content(self) -> str:
        """获取页面内容"""
        if not self.page:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            content = await self.page.content()
            self.last_activity = time.time()
            return content
        except Exception as e:
            logger.error(f"获取页面内容失败: {e}")
            raise
    
    async def wait_for_selector(self, selector: str, timeout: int = 30) -> bool:
        """等待元素出现"""
        if not self.page:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            self.last_activity = time.time()
            return True
        except Exception as e:
            logger.error(f"等待元素失败: {e}")
            raise
    
    async def click(self, selector: str) -> bool:
        """点击元素"""
        if not self.page:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            await self.page.click(selector)
            self.last_activity = time.time()
            return True
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            raise
    
    async def type_text(self, selector: str, text: str) -> bool:
        """输入文本"""
        if not self.page:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            await self.page.fill(selector, text)
            self.last_activity = time.time()
            return True
        except Exception as e:
            logger.error(f"输入文本失败: {e}")
            raise
    
    async def screenshot(self, selector: Optional[str] = None, full_page: bool = False) -> bytes:
        """截图"""
        if not self.page:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            if selector:
                element = await self.page.query_selector(selector)
                if element:
                    screenshot_bytes = await element.screenshot()
                else:
                    raise ValueError(f"未找到元素: {selector}")
            else:
                screenshot_bytes = await self.page.screenshot(full_page=full_page)
            
            self.last_activity = time.time()
            return screenshot_bytes
        except Exception as e:
            logger.error(f"截图失败: {e}")
            raise
    
    async def set_extra_headers(self, headers: Dict[str, str]):
        """设置额外的请求头"""
        if not self.context:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            self.custom_headers.update(headers)
            await self.context.set_extra_http_headers(self.custom_headers)
            self.last_activity = time.time()
        except Exception as e:
            logger.error(f"设置请求头失败: {e}")
            raise
    
    async def set_cookies(self, cookies: List[Dict[str, Any]]):
        """设置 Cookie"""
        if not self.context:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            await self.context.add_cookies(cookies)
            self.last_activity = time.time()
        except Exception as e:
            logger.error(f"设置 Cookie 失败: {e}")
            raise
    
    async def get_cookies(self, url: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取 Cookie"""
        if not self.context:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            if url:
                cookies = await self.context.cookies(url)
            else:
                cookies = await self.context.cookies()
            self.last_activity = time.time()
            return cookies
        except Exception as e:
            logger.error(f"获取 Cookie 失败: {e}")
            raise
    
    def get_network_requests(self, url_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取拦截的网络请求"""
        if url_pattern:
            self.network_interceptor.set_url_pattern(url_pattern)
        return self.network_interceptor.get_requests()
    
    def clear_network_requests(self):
        """清空网络请求记录"""
        self.network_interceptor.clear()
    
    async def close(self):
        """关闭浏览器会话"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            logger.info(f"浏览器会话 {self.session_id} 已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器会话失败: {e}")


class BrowserPool:
    """浏览器会话池"""
    
    def __init__(self, max_sessions: int = 10, session_timeout: int = 3600):
        self.sessions: Dict[str, BrowserSession] = {}
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self._lock = asyncio.Lock()
    
    async def create_session(
        self,
        headless: bool = True,
        user_agent: Optional[str] = None,
        proxy: Optional[Dict[str, str]] = None,
        width: int = 1920,
        height: int = 1080
    ) -> str:
        """创建新的浏览器会话"""
        async with self._lock:
            # 清理过期会话
            await self._cleanup_expired_sessions()
            
            # 检查会话数量限制
            if len(self.sessions) >= self.max_sessions:
                raise RuntimeError(f"会话数量已达上限: {self.max_sessions}")
            
            # 创建新会话
            session_id = str(uuid.uuid4())
            session = BrowserSession(session_id)
            
            try:
                await session.initialize(headless, user_agent, proxy, width, height)
                self.sessions[session_id] = session
                logger.info(f"创建新会话: {session_id}, 当前会话数: {len(self.sessions)}")
                return session_id
            except Exception as e:
                logger.error(f"创建会话失败: {e}")
                await session.close()
                raise
    
    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    async def close_session(self, session_id: str) -> bool:
        """关闭指定会话"""
        async with self._lock:
            session = self.sessions.pop(session_id, None)
            if session:
                await session.close()
                logger.info(f"关闭会话: {session_id}, 当前会话数: {len(self.sessions)}")
                return True
            return False
    
    async def _cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.close_session(session_id)
            logger.info(f"清理过期会话: {session_id}")
    
    async def close_all(self):
        """关闭所有会话"""
        async with self._lock:
            for session in self.sessions.values():
                await session.close()
            self.sessions.clear()
            logger.info("所有会话已关闭")

