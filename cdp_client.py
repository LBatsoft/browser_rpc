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
from playwright_stealth import stealth_async
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
THIRD_PARTY_STEALTH_PATH = BASE_DIR / 'resources' / 'stealth' / 'stealth.min.js'


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
                        logger.warning(f"获取响应体失败: {e}")
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
            
            # 创建上下文
            context_options = {
                'viewport': {'width': width, 'height': height},
                'bypass_csp': True,
            }
            
            if user_agent:
                context_options['user_agent'] = user_agent
            
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
        """导航到指定 URL"""
        if not self.page:
            raise RuntimeError("浏览器会话未初始化")
        
        try:
            response = await self.page.goto(url, timeout=timeout * 1000, wait_until='domcontentloaded')
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

