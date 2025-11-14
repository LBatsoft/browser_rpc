"""
gRPC 客户端示例
展示如何使用浏览器 RPC 服务
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

import grpc

# 注意：需要先编译 proto 文件
try:
    import spider_pb2
    import spider_pb2_grpc
except ImportError:
    print("警告: proto 文件尚未编译")
    spider_pb2 = None
    spider_pb2_grpc = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrowserRPCClient:
    """浏览器 RPC 客户端"""
    
    def __init__(self, host: str = 'localhost', port: int = 50051):
        self.host = host
        self.port = port
        self.channel = None
        self.stub = None
        self.session_id = None
    
    async def connect(self):
        """连接到 RPC 服务器"""
        if spider_pb2 is None or spider_pb2_grpc is None:
            raise RuntimeError("proto 文件尚未编译")
        
        max_message_length = 32 * 1024 * 1024  # 32 MB
        self.channel = grpc.aio.insecure_channel(
            f'{self.host}:{self.port}',
            options=(
                ('grpc.max_send_message_length', max_message_length),
                ('grpc.max_receive_message_length', max_message_length),
            )
        )
        self.stub = spider_pb2_grpc.BrowserServiceStub(self.channel)
        logger.info(f"已连接到 RPC 服务器: {self.host}:{self.port}")
    
    async def close(self):
        """关闭连接"""
        if self.session_id:
            await self.close_session()
        if self.channel:
            await self.channel.close()
            logger.info("已关闭 RPC 连接")
    
    async def create_session(
        self,
        headless: bool = True,
        user_agent: str = '',
        proxy: List[str] = None,
        width: int = 1920,
        height: int = 1080
    ) -> str:
        """创建浏览器会话"""
        request = spider_pb2.CreateSessionRequest(
            headless=headless,
            user_agent=user_agent,
            proxy=proxy or [],
            width=width,
            height=height
        )
        
        response = await self.stub.CreateSession(request)
        
        if response.success:
            self.session_id = response.session_id
            logger.info(f"创建会话成功: {self.session_id}")
            return self.session_id
        else:
            raise RuntimeError(f"创建会话失败: {response.message}")
    
    async def close_session(self) -> bool:
        """关闭浏览器会话"""
        if not self.session_id:
            return False
        
        request = spider_pb2.CloseSessionRequest(session_id=self.session_id)
        response = await self.stub.CloseSession(request)
        
        if response.success:
            logger.info(f"关闭会话成功: {self.session_id}")
            self.session_id = None
            return True
        else:
            logger.error(f"关闭会话失败: {response.message}")
            return False
    
    async def navigate(self, url: str, timeout: int = 30) -> str:
        """导航到指定 URL"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.NavigateRequest(
            session_id=self.session_id,
            url=url,
            timeout=timeout
        )
        
        response = await self.stub.Navigate(request)
        
        if response.success:
            logger.info(f"导航成功: {url} -> {response.final_url}")
            return response.final_url
        else:
            raise RuntimeError(f"导航失败: {response.message}")
    
    async def execute_script(self, script: str) -> Any:
        """执行 JavaScript"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.ExecuteScriptRequest(
            session_id=self.session_id,
            script=script
        )
        
        response = await self.stub.ExecuteScript(request)
        
        if response.success:
            result = json.loads(response.result) if response.result else None
            logger.info(f"脚本执行成功")
            return result
        else:
            raise RuntimeError(f"脚本执行失败: {response.error}")
    
    async def get_page_content(self) -> str:
        """获取页面 HTML"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.GetPageContentRequest(session_id=self.session_id)
        response = await self.stub.GetPageContent(request)
        
        if response.success:
            logger.info(f"获取页面内容成功: {len(response.html)} 字节")
            return response.html
        else:
            raise RuntimeError(f"获取页面内容失败: {response.message}")
    
    async def get_network_requests(self, url_pattern: str = '') -> List[Dict[str, Any]]:
        """获取拦截的网络请求"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.GetNetworkRequestsRequest(
            session_id=self.session_id,
            url_pattern=url_pattern
        )
        
        response = await self.stub.GetNetworkRequests(request)
        
        if response.success:
            requests = []
            for req in response.requests:
                requests.append({
                    'request_id': req.request_id,
                    'url': req.url,
                    'method': req.method,
                    'headers': dict(req.headers),
                    'post_data': req.post_data,
                    'status_code': req.status_code,
                    'response_body': req.response_body,
                    'response_headers': dict(req.response_headers),
                    'timestamp': req.timestamp
                })
            logger.info(f"获取网络请求成功: {len(requests)} 个")
            return requests
        else:
            raise RuntimeError(f"获取网络请求失败: {response.message}")
    
    async def wait_for_element(self, selector: str, timeout: int = 30) -> bool:
        """等待元素出现"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.WaitForElementRequest(
            session_id=self.session_id,
            selector=selector,
            timeout=timeout
        )
        
        response = await self.stub.WaitForElement(request)
        
        if response.success:
            logger.info(f"等待元素成功: {selector}")
            return True
        else:
            raise RuntimeError(f"等待元素失败: {response.message}")
    
    async def click_element(self, selector: str) -> bool:
        """点击元素"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.ClickElementRequest(
            session_id=self.session_id,
            selector=selector
        )
        
        response = await self.stub.ClickElement(request)
        
        if response.success:
            logger.info(f"点击元素成功: {selector}")
            return True
        else:
            raise RuntimeError(f"点击元素失败: {response.message}")
    
    async def type_text(self, selector: str, text: str) -> bool:
        """输入文本"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.TypeTextRequest(
            session_id=self.session_id,
            selector=selector,
            text=text
        )
        
        response = await self.stub.TypeText(request)
        
        if response.success:
            logger.info(f"输入文本成功: {selector}")
            return True
        else:
            raise RuntimeError(f"输入文本失败: {response.message}")
    
    async def take_screenshot(
        self,
        selector: str = '',
        full_page: bool = False,
        save_path: Optional[str] = None
    ) -> bytes:
        """截图"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.TakeScreenshotRequest(
            session_id=self.session_id,
            selector=selector,
            full_page=full_page
        )
        
        response = await self.stub.TakeScreenshot(request)
        
        if response.success:
            logger.info(f"截图成功: {len(response.image_data)} 字节")
            
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(response.image_data)
                logger.info(f"截图已保存: {save_path}")
            
            return response.image_data
        else:
            raise RuntimeError(f"截图失败: {response.message}")
    
    async def set_headers(self, headers: Dict[str, str]) -> bool:
        """设置请求头"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.SetHeadersRequest(
            session_id=self.session_id,
            headers=headers
        )
        
        response = await self.stub.SetHeaders(request)
        
        if response.success:
            logger.info(f"设置请求头成功")
            return True
        else:
            raise RuntimeError(f"设置请求头失败: {response.message}")
    
    async def set_cookies(self, cookies: List[Dict[str, Any]]) -> bool:
        """设置 Cookie"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        pb_cookies = []
        for cookie in cookies:
            pb_cookie = spider_pb2.Cookie(
                name=cookie.get('name', ''),
                value=cookie.get('value', ''),
                domain=cookie.get('domain', ''),
                path=cookie.get('path', '/'),
                expires=cookie.get('expires', 0),
                http_only=cookie.get('httpOnly', False),
                secure=cookie.get('secure', False),
                same_site=cookie.get('sameSite', '')
            )
            pb_cookies.append(pb_cookie)
        
        request = spider_pb2.SetCookiesRequest(
            session_id=self.session_id,
            cookies=pb_cookies
        )
        
        response = await self.stub.SetCookies(request)
        
        if response.success:
            logger.info(f"设置 Cookie 成功")
            return True
        else:
            raise RuntimeError(f"设置 Cookie 失败: {response.message}")
    
    async def get_cookies(self, url: str = '') -> List[Dict[str, Any]]:
        """获取 Cookie"""
        if not self.session_id:
            raise RuntimeError("会话未创建")
        
        request = spider_pb2.GetCookiesRequest(
            session_id=self.session_id,
            url=url
        )
        
        response = await self.stub.GetCookies(request)
        
        if response.success:
            cookies = []
            for cookie in response.cookies:
                cookies.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'expires': cookie.expires,
                    'httpOnly': cookie.http_only,
                    'secure': cookie.secure,
                    'sameSite': cookie.same_site
                })
            logger.info(f"获取 Cookie 成功: {len(cookies)} 个")
            return cookies
        else:
            raise RuntimeError(f"获取 Cookie 失败: {response.message}")


# 使用示例
async def example_basic_usage():
    """基础使用示例"""
    client = BrowserRPCClient()
    
    try:
        # 连接到服务器
        await client.connect()
        
        # 创建会话
        await client.create_session(headless=False, width=1920, height=1080)
        
        # 导航到网页
        await client.navigate('https://www.baidu.com')
        
        # 等待搜索框出现
        await client.wait_for_element('#kw', timeout=10)
        
        # 输入搜索内容
        await client.type_text('#kw', 'Python 爬虫')
        
        # 点击搜索按钮
        await client.click_element('#su')
        
        # 等待结果加载
        await asyncio.sleep(2)
        
        # 获取页面标题
        title = await client.execute_script('document.title')
        logger.info(f"页面标题: {title}")
        
        # 截图
        await client.take_screenshot(save_path='baidu_search.png', full_page=True)
        
        # 获取页面 HTML
        html = await client.get_page_content()
        logger.info(f"页面 HTML 长度: {len(html)}")
        
    finally:
        # 关闭连接
        await client.close()


async def example_network_intercept():
    """网络拦截示例"""
    client = BrowserRPCClient()
    
    try:
        await client.connect()
        await client.create_session(headless=True)
        
        # 导航到网页
        await client.navigate('https://amap.com')
        
        # 等待页面加载
        await asyncio.sleep(2)
        
        # 获取所有网络请求
        requests = await client.get_network_requests()
        
        logger.info(f"\n捕获到 {len(requests)} 个网络请求:")
        for req in requests:
            logger.info(f"  {req['method']} {req['url']}")
            if req['response_body']:
                logger.info(f"    响应状态: {req['status_code']}")
                logger.info(f"    响应大小: {len(req['response_body'])} 字节")
        
        # 过滤特定 API 请求
        api_requests = await client.get_network_requests(url_pattern=r'/posts')
        logger.info(f"\nAPI 请求数量: {len(api_requests)}")
        
        # 对浏览器进行截图
        # 对浏览器进行截图
        await client.take_screenshot(save_path='amap_screenshot.png', full_page=True)
        logger.info("已保存 amap.com 页面截图到 amap_screenshot.png")
    finally:
        await client.close()


async def example_cookie_management():
    """Cookie 管理示例"""
    client = BrowserRPCClient()
    
    try:
        await client.connect()
        await client.create_session(headless=True)
        
        # 设置自定义 Cookie
        cookies = [
            {
                'name': 'user_token',
                'value': 'abc123',
                'domain': '.example.com',
                'path': '/',
                'httpOnly': True,
                'secure': True
            }
        ]
        await client.set_cookies(cookies)
        
        # 导航到网页
        await client.navigate('https://www.example.com')
        
        # 获取所有 Cookie
        all_cookies = await client.get_cookies()
        logger.info(f"当前 Cookie: {json.dumps(all_cookies, indent=2)}")
        
    finally:
        await client.close()


async def example_custom_headers():
    """自定义请求头示例"""
    client = BrowserRPCClient()
    
    try:
        await client.connect()
        await client.create_session(headless=True)
        
        # 设置自定义请求头
        headers = {
            'X-Custom-Header': 'MyValue',
            'Authorization': 'Bearer token123'
        }
        await client.set_headers(headers)
        
        # 导航到网页
        await client.navigate('https://httpbin.org/headers')
        
        # 获取页面内容
        html = await client.get_page_content()
        logger.info(f"响应内容:\n{html}")
        
    finally:
        await client.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='浏览器 RPC 客户端示例')
    parser.add_argument('--example', choices=['basic', 'network', 'cookie', 'headers'],
                       default='basic', help='运行的示例')
    parser.add_argument('--host', default='localhost', help='RPC 服务器地址')
    parser.add_argument('--port', type=int, default=50051, help='RPC 服务器端口')
    
    args = parser.parse_args()
    
    # 设置全局连接参数
    BrowserRPCClient.default_host = args.host
    BrowserRPCClient.default_port = args.port
    
    # 运行对应的示例
    if args.example == 'basic':
        asyncio.run(example_basic_usage())
    elif args.example == 'network':
        asyncio.run(example_network_intercept())
    elif args.example == 'cookie':
        asyncio.run(example_cookie_management())
    elif args.example == 'headers':
        asyncio.run(example_custom_headers())


if __name__ == '__main__':
    main()


