"""
gRPC 服务器实现
提供浏览器控制的 RPC 接口
"""

import asyncio
import json
import logging
import sys
from concurrent import futures
from typing import Optional

import grpc

# 注意：需要先编译 proto 文件生成这些模块
# python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/spider.proto
try:
    import spider_pb2
    import spider_pb2_grpc
except ImportError:
    # 如果 proto 文件还未编译，提供占位符
    print("警告: proto 文件尚未编译，请运行: python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/spider.proto")
    spider_pb2 = None
    spider_pb2_grpc = None

from cdp_client import BrowserPool

# 配置日志
import os
log_dir = os.path.join(os.path.dirname(__file__), 'log')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'rpc_server.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BrowserServiceImpl:
    """浏览器服务实现"""
    
    def __init__(self, max_sessions: int = 10, session_timeout: int = 3600):
        self.browser_pool = BrowserPool(max_sessions, session_timeout)
        logger.info(f"浏览器服务初始化完成 (最大会话数: {max_sessions}, 超时: {session_timeout}秒)")
    
    async def CreateSession(self, request, context):
        """创建浏览器会话"""
        try:
            # 解析代理配置
            proxy = None
            if request.proxy:
                proxy = {
                    'server': request.proxy[0] if request.proxy else None
                }
            
            # 创建会话
            session_id = await self.browser_pool.create_session(
                headless=request.headless,
                user_agent=request.user_agent if request.user_agent else None,
                proxy=proxy,
                width=request.width if request.width > 0 else 1920,
                height=request.height if request.height > 0 else 1080
            )
            
            logger.info(f"创建会话成功: {session_id}")
            return spider_pb2.CreateSessionResponse(
                session_id=session_id,
                success=True,
                message="会话创建成功"
            )
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            return spider_pb2.CreateSessionResponse(
                success=False,
                message=f"创建会话失败: {str(e)}"
            )
    
    async def CloseSession(self, request, context):
        """关闭浏览器会话"""
        try:
            success = await self.browser_pool.close_session(request.session_id)
            if success:
                logger.info(f"关闭会话成功: {request.session_id}")
                return spider_pb2.CloseSessionResponse(
                    success=True,
                    message="会话关闭成功"
                )
            else:
                return spider_pb2.CloseSessionResponse(
                    success=False,
                    message="会话不存在"
                )
        except Exception as e:
            logger.error(f"关闭会话失败: {e}")
            return spider_pb2.CloseSessionResponse(
                success=False,
                message=f"关闭会话失败: {str(e)}"
            )
    
    async def Navigate(self, request, context):
        """导航到指定 URL"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.NavigateResponse(
                    success=False,
                    message="会话不存在"
                )
            
            final_url = await session.navigate(
                request.url,
                timeout=request.timeout if request.timeout > 0 else 30
            )
            
            logger.info(f"导航成功: {request.url} -> {final_url}")
            return spider_pb2.NavigateResponse(
                success=True,
                message="导航成功",
                final_url=final_url
            )
        except Exception as e:
            logger.error(f"导航失败: {e}")
            return spider_pb2.NavigateResponse(
                success=False,
                message=f"导航失败: {str(e)}"
            )
    
    async def ExecuteScript(self, request, context):
        """执行 JavaScript"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.ExecuteScriptResponse(
                    success=False,
                    error="会话不存在"
                )
            
            result = await session.execute_script(request.script)
            
            logger.info(f"脚本执行成功: {request.script[:50]}...")
            return spider_pb2.ExecuteScriptResponse(
                success=True,
                result=json.dumps(result, ensure_ascii=False)
            )
        except Exception as e:
            logger.error(f"脚本执行失败: {e}")
            return spider_pb2.ExecuteScriptResponse(
                success=False,
                error=str(e)
            )
    
    async def GetPageContent(self, request, context):
        """获取页面内容"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.GetPageContentResponse(
                    success=False,
                    message="会话不存在"
                )
            
            html = await session.get_content()
            
            logger.info(f"获取页面内容成功: {len(html)} 字节")
            return spider_pb2.GetPageContentResponse(
                success=True,
                html=html,
                message="获取成功"
            )
        except Exception as e:
            logger.error(f"获取页面内容失败: {e}")
            return spider_pb2.GetPageContentResponse(
                success=False,
                message=f"获取失败: {str(e)}"
            )
    
    async def GetNetworkRequests(self, request, context):
        """获取拦截的网络请求"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.GetNetworkRequestsResponse(
                    success=False,
                    message="会话不存在"
                )
            
            requests = session.get_network_requests(
                request.url_pattern if request.url_pattern else None
            )
            
            # 转换为 protobuf 格式
            pb_requests = []
            for req in requests:
                resp = req.get('response', {})
                pb_req = spider_pb2.NetworkRequest(
                    request_id=req['request_id'],
                    url=req['url'],
                    method=req['method'],
                    headers=req['headers'],
                    post_data=req.get('post_data', '') or '',
                    status_code=resp.get('status_code', 0) if resp else 0,
                    response_body=resp.get('body', '') or '' if resp else '',
                    response_headers=resp.get('headers', {}) if resp else {},
                    timestamp=req['timestamp']
                )
                pb_requests.append(pb_req)
            
            logger.info(f"获取网络请求成功: {len(pb_requests)} 个")
            return spider_pb2.GetNetworkRequestsResponse(
                success=True,
                requests=pb_requests,
                message="获取成功"
            )
        except Exception as e:
            logger.error(f"获取网络请求失败: {e}")
            return spider_pb2.GetNetworkRequestsResponse(
                success=False,
                message=f"获取失败: {str(e)}"
            )
    
    async def WaitForElement(self, request, context):
        """等待元素出现"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.WaitForElementResponse(
                    success=False,
                    message="会话不存在"
                )
            
            await session.wait_for_selector(
                request.selector,
                timeout=request.timeout if request.timeout > 0 else 30
            )
            
            logger.info(f"等待元素成功: {request.selector}")
            return spider_pb2.WaitForElementResponse(
                success=True,
                message="元素已出现"
            )
        except Exception as e:
            logger.error(f"等待元素失败: {e}")
            return spider_pb2.WaitForElementResponse(
                success=False,
                message=f"等待失败: {str(e)}"
            )
    
    async def ClickElement(self, request, context):
        """点击元素"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.ClickElementResponse(
                    success=False,
                    message="会话不存在"
                )
            
            await session.click(request.selector)
            
            logger.info(f"点击元素成功: {request.selector}")
            return spider_pb2.ClickElementResponse(
                success=True,
                message="点击成功"
            )
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            return spider_pb2.ClickElementResponse(
                success=False,
                message=f"点击失败: {str(e)}"
            )
    
    async def TypeText(self, request, context):
        """输入文本"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.TypeTextResponse(
                    success=False,
                    message="会话不存在"
                )
            
            await session.type_text(request.selector, request.text)
            
            logger.info(f"输入文本成功: {request.selector}")
            return spider_pb2.TypeTextResponse(
                success=True,
                message="输入成功"
            )
        except Exception as e:
            logger.error(f"输入文本失败: {e}")
            return spider_pb2.TypeTextResponse(
                success=False,
                message=f"输入失败: {str(e)}"
            )
    
    async def TakeScreenshot(self, request, context):
        """截图"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.TakeScreenshotResponse(
                    success=False,
                    message="会话不存在"
                )
            
            image_data = await session.screenshot(
                selector=request.selector if request.selector else None,
                full_page=request.full_page
            )
            
            logger.info(f"截图成功: {len(image_data)} 字节")
            return spider_pb2.TakeScreenshotResponse(
                success=True,
                image_data=image_data,
                message="截图成功"
            )
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return spider_pb2.TakeScreenshotResponse(
                success=False,
                message=f"截图失败: {str(e)}"
            )
    
    async def SetHeaders(self, request, context):
        """设置请求头"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.SetHeadersResponse(
                    success=False,
                    message="会话不存在"
                )
            
            await session.set_extra_headers(dict(request.headers))
            
            logger.info(f"设置请求头成功: {len(request.headers)} 个")
            return spider_pb2.SetHeadersResponse(
                success=True,
                message="设置成功"
            )
        except Exception as e:
            logger.error(f"设置请求头失败: {e}")
            return spider_pb2.SetHeadersResponse(
                success=False,
                message=f"设置失败: {str(e)}"
            )
    
    async def SetCookies(self, request, context):
        """设置 Cookie"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.SetCookiesResponse(
                    success=False,
                    message="会话不存在"
                )
            
            # 转换 Cookie 格式
            cookies = []
            for cookie in request.cookies:
                cookie_dict = {
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path if cookie.path else '/',
                }
                if cookie.expires:
                    cookie_dict['expires'] = cookie.expires
                if cookie.http_only:
                    cookie_dict['httpOnly'] = cookie.http_only
                if cookie.secure:
                    cookie_dict['secure'] = cookie.secure
                if cookie.same_site:
                    cookie_dict['sameSite'] = cookie.same_site
                cookies.append(cookie_dict)
            
            await session.set_cookies(cookies)
            
            logger.info(f"设置 Cookie 成功: {len(cookies)} 个")
            return spider_pb2.SetCookiesResponse(
                success=True,
                message="设置成功"
            )
        except Exception as e:
            logger.error(f"设置 Cookie 失败: {e}")
            return spider_pb2.SetCookiesResponse(
                success=False,
                message=f"设置失败: {str(e)}"
            )
    
    async def GetCookies(self, request, context):
        """获取 Cookie"""
        try:
            session = self.browser_pool.get_session(request.session_id)
            if not session:
                return spider_pb2.GetCookiesResponse(
                    success=False,
                    message="会话不存在"
                )
            
            cookies = await session.get_cookies(
                url=request.url if request.url else None
            )
            
            # 转换为 protobuf 格式
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
            
            logger.info(f"获取 Cookie 成功: {len(pb_cookies)} 个")
            return spider_pb2.GetCookiesResponse(
                success=True,
                cookies=pb_cookies,
                message="获取成功"
            )
        except Exception as e:
            logger.error(f"获取 Cookie 失败: {e}")
            return spider_pb2.GetCookiesResponse(
                success=False,
                message=f"获取失败: {str(e)}"
            )
    
    async def shutdown(self):
        """关闭服务"""
        await self.browser_pool.close_all()
        logger.info("浏览器服务已关闭")


async def serve(host: str = '0.0.0.0', port: int = 50051, max_workers: int = 10):
    """启动 gRPC 服务器"""
    
    if spider_pb2 is None or spider_pb2_grpc is None:
        logger.error("proto 文件尚未编译，请先运行编译命令")
        return
    
    max_message_length = 32 * 1024 * 1024  # 32 MB
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=(
            ('grpc.max_send_message_length', max_message_length),
            ('grpc.max_receive_message_length', max_message_length),
        )
    )
    
    service = BrowserServiceImpl()
    spider_pb2_grpc.add_BrowserServiceServicer_to_server(service, server)
    
    server.add_insecure_port(f'{host}:{port}')
    
    logger.info(f"启动 gRPC 服务器: {host}:{port}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
        await service.shutdown()
        await server.stop(grace=5)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='浏览器 RPC 服务器')
    parser.add_argument('--host', default='0.0.0.0', help='服务器地址')
    parser.add_argument('--port', type=int, default=50051, help='服务器端口')
    parser.add_argument('--max-workers', type=int, default=10, help='最大工作线程数')
    
    args = parser.parse_args()
    
    try:
        asyncio.run(serve(args.host, args.port, args.max_workers))
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()


