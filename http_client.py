"""
HTTP 客户端实现
提供浏览器 RPC 服务的 HTTP 客户端封装
"""

import asyncio
import base64
import json
import logging
from typing import List, Dict, Any, Optional

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrowserHTTPClient:
    """浏览器 HTTP 客户端"""
    
    def __init__(self, base_url: str = 'http://localhost:8000'):
        """
        初始化 HTTP 客户端
        
        Args:
            base_url: HTTP 服务器地址，例如 'http://localhost:8000'
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=60.0)
        self.session_id: Optional[str] = None
    
    async def close(self):
        """关闭连接"""
        if self.session_id:
            await self.close_session()
        await self.client.aclose()
        logger.info("已关闭 HTTP 连接")
    
    async def create_session(
        self,
        headless: bool = True,
        user_agent: Optional[str] = None,
        proxy: Optional[List[str]] = None,
        width: int = 1920,
        height: int = 1080
    ) -> str:
        """创建浏览器会话"""
        data = {
            "headless": headless,
            "width": width,
            "height": height
        }
        if user_agent:
            data["user_agent"] = user_agent
        if proxy:
            data["proxy"] = proxy
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            self.session_id = result["session_id"]
            logger.info(f"创建会话成功: {self.session_id}")
            return self.session_id
        else:
            raise RuntimeError(f"创建会话失败: {result.get('message', '未知错误')}")
    
    async def close_session(self) -> bool:
        """关闭浏览器会话"""
        if not self.session_id:
            return False
        
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/sessions/{self.session_id}"
            )
            response.raise_for_status()
            
            result = response.json()
            if result["success"]:
                logger.info(f"关闭会话成功: {self.session_id}")
                self.session_id = None
                return True
            else:
                logger.error(f"关闭会话失败: {result.get('message', '未知错误')}")
                return False
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("会话不存在")
                self.session_id = None
                return False
            raise
    
    async def navigate(self, url: str, timeout: int = 30) -> str:
        """导航到指定 URL"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        data = {
            "url": url,
            "timeout": timeout
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions/{self.session_id}/navigate",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            logger.info(f"导航成功: {url}")
            return result.get("final_url", url)
        else:
            raise RuntimeError(f"导航失败: {result.get('message', '未知错误')}")
    
    async def execute_script(self, script: str) -> Any:
        """执行 JavaScript"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        data = {"script": script}
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions/{self.session_id}/execute",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            return result.get("result")
        else:
            raise RuntimeError(f"脚本执行失败: {result.get('error', '未知错误')}")
    
    async def get_page_content(self) -> str:
        """获取页面内容"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        response = await self.client.get(
            f"{self.base_url}/api/sessions/{self.session_id}/content"
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            return result.get("html", "")
        else:
            raise RuntimeError(f"获取页面内容失败: {result.get('message', '未知错误')}")
    
    async def get_network_requests(self, url_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取拦截的网络请求"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        data = {}
        if url_pattern:
            data["url_pattern"] = url_pattern
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions/{self.session_id}/network",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            # 转换为字典列表
            requests = []
            for req in result.get("requests", []):
                requests.append({
                    "request_id": req["request_id"],
                    "url": req["url"],
                    "method": req["method"],
                    "headers": req["headers"],
                    "post_data": req.get("post_data"),
                    "timestamp": req["timestamp"],
                    "response": {
                        "status_code": req.get("status_code"),
                        "body": req.get("response_body"),
                        "headers": req.get("response_headers", {})
                    } if req.get("status_code") else None
                })
            return requests
        else:
            raise RuntimeError(f"获取网络请求失败: {result.get('message', '未知错误')}")
    
    async def wait_for_element(self, selector: str, timeout: int = 30) -> bool:
        """等待元素出现"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        data = {
            "selector": selector,
            "timeout": timeout
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions/{self.session_id}/wait",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            logger.info(f"等待元素成功: {selector}")
            return True
        else:
            raise RuntimeError(f"等待元素失败: {result.get('message', '未知错误')}")
    
    async def click_element(self, selector: str) -> bool:
        """点击元素"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        data = {"selector": selector}
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions/{self.session_id}/click",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            logger.info(f"点击元素成功: {selector}")
            return True
        else:
            raise RuntimeError(f"点击元素失败: {result.get('message', '未知错误')}")
    
    async def type_text(self, selector: str, text: str) -> bool:
        """输入文本"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        data = {
            "selector": selector,
            "text": text
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions/{self.session_id}/type",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            logger.info(f"输入文本成功: {selector}")
            return True
        else:
            raise RuntimeError(f"输入文本失败: {result.get('message', '未知错误')}")
    
    async def take_screenshot(
        self,
        save_path: Optional[str] = None,
        selector: Optional[str] = None,
        full_page: bool = False
    ) -> bytes:
        """页面截图"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        data = {
            "full_page": full_page
        }
        if selector:
            data["selector"] = selector
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions/{self.session_id}/screenshot",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            # 解码 base64
            image_data = base64.b64decode(result["image_data"])
            
            # 保存到文件（如果指定）
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(image_data)
                logger.info(f"截图已保存: {save_path}")
            
            return image_data
        else:
            raise RuntimeError(f"截图失败: {result.get('message', '未知错误')}")
    
    async def set_headers(self, headers: Dict[str, str]) -> bool:
        """设置请求头"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        data = {"headers": headers}
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions/{self.session_id}/headers",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            logger.info("设置请求头成功")
            return True
        else:
            raise RuntimeError(f"设置请求头失败: {result.get('message', '未知错误')}")
    
    async def set_cookies(self, cookies: List[Dict[str, Any]]) -> bool:
        """设置 Cookie"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        data = {"cookies": cookies}
        
        response = await self.client.post(
            f"{self.base_url}/api/sessions/{self.session_id}/cookies",
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            logger.info(f"设置 Cookie 成功: {len(cookies)} 个")
            return True
        else:
            raise RuntimeError(f"设置 Cookie 失败: {result.get('message', '未知错误')}")
    
    async def get_cookies(self, url: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取 Cookie"""
        if not self.session_id:
            raise RuntimeError("会话未创建，请先调用 create_session()")
        
        params = {}
        if url:
            params["url"] = url
        
        response = await self.client.get(
            f"{self.base_url}/api/sessions/{self.session_id}/cookies",
            params=params
        )
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            cookies = []
            for cookie in result.get("cookies", []):
                cookies.append({
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie.get("domain"),
                    "path": cookie.get("path"),
                    "expires": cookie.get("expires"),
                    "httpOnly": cookie.get("http_only"),
                    "secure": cookie.get("secure"),
                    "sameSite": cookie.get("same_site")
                })
            return cookies
        else:
            raise RuntimeError(f"获取 Cookie 失败: {result.get('message', '未知错误')}")


# 示例用法
async def example_basic_usage():
    """基础使用示例"""
    client = BrowserHTTPClient(base_url='http://localhost:8000')
    
    try:
        # 创建会话
        await client.create_session(headless=True)
        
        # 访问网页
        await client.navigate('https://www.example.com')
        
        # 获取内容
        html = await client.get_page_content()
        print(f"页面内容长度: {len(html)} 字节")
        
        # 截图
        await client.take_screenshot(save_path='example.png', full_page=True)
        
    finally:
        await client.close()


async def example_advanced_usage():
    """高级使用示例"""
    client = BrowserHTTPClient(base_url='http://localhost:8000')
    
    try:
        await client.create_session(headless=True)
        
        # 设置请求头
        await client.set_headers({
            'Authorization': 'Bearer token',
            'User-Agent': 'Custom Agent'
        })
        
        # 设置 Cookie
        await client.set_cookies([{
            'name': 'session',
            'value': 'abc123',
            'domain': '.example.com'
        }])
        
        # 导航
        await client.navigate('https://www.example.com')
        
        # 等待并点击元素
        await client.wait_for_element('button#submit')
        await client.click_element('button#submit')
        
        # 输入文本
        await client.type_text('input#username', 'myname')
        
        # 获取网络请求
        requests = await client.get_network_requests(url_pattern=r'/api/')
        for req in requests:
            print(f"{req['method']} {req['url']}")
        
    finally:
        await client.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--example':
        if len(sys.argv) > 2 and sys.argv[2] == 'advanced':
            asyncio.run(example_advanced_usage())
        else:
            asyncio.run(example_basic_usage())
    else:
        print("Usage: python http_client.py --example [basic|advanced]")

