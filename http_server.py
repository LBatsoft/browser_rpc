"""
HTTP 服务器实现
基于 FastAPI 提供浏览器控制的 HTTP REST API
"""

import asyncio
import base64
import json
import logging
import sys
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from cdp_client import BrowserPool

# 配置日志
import os
log_dir = os.path.join(os.path.dirname(__file__), 'log')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'http_server.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Browser RPC HTTP API",
    description="Browser automation service via HTTP REST API",
    version="1.0.0"
)

# 全局浏览器池
browser_pool: Optional[BrowserPool] = None


# Pydantic 模型定义
class CreateSessionRequest(BaseModel):
    headless: bool = True
    user_agent: Optional[str] = None
    proxy: Optional[List[str]] = None
    width: int = 1920
    height: int = 1080


class CreateSessionResponse(BaseModel):
    session_id: str
    success: bool
    message: str


class CloseSessionResponse(BaseModel):
    success: bool
    message: str


class NavigateRequest(BaseModel):
    url: str
    timeout: int = 30


class NavigateResponse(BaseModel):
    success: bool
    message: str
    final_url: Optional[str] = None


class ExecuteScriptRequest(BaseModel):
    script: str


class ExecuteScriptResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class GetPageContentResponse(BaseModel):
    success: bool
    html: Optional[str] = None
    message: str


class GetNetworkRequestsRequest(BaseModel):
    url_pattern: Optional[str] = None


class NetworkRequest(BaseModel):
    request_id: str
    url: str
    method: str
    headers: Dict[str, str]
    post_data: Optional[str] = None
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    response_headers: Optional[Dict[str, str]] = None
    timestamp: float


class GetNetworkRequestsResponse(BaseModel):
    success: bool
    requests: List[NetworkRequest]
    message: str


class WaitForElementRequest(BaseModel):
    selector: str
    timeout: int = 30


class WaitForElementResponse(BaseModel):
    success: bool
    message: str


class ClickElementRequest(BaseModel):
    selector: str


class ClickElementResponse(BaseModel):
    success: bool
    message: str


class TypeTextRequest(BaseModel):
    selector: str
    text: str


class TypeTextResponse(BaseModel):
    success: bool
    message: str


class TakeScreenshotRequest(BaseModel):
    selector: Optional[str] = None
    full_page: bool = False


class TakeScreenshotResponse(BaseModel):
    success: bool
    image_data: Optional[str] = None  # base64 encoded
    message: str


class SetHeadersRequest(BaseModel):
    headers: Dict[str, str]


class SetHeadersResponse(BaseModel):
    success: bool
    message: str


class Cookie(BaseModel):
    name: str
    value: str
    domain: Optional[str] = None
    path: Optional[str] = None
    expires: Optional[float] = None
    http_only: Optional[bool] = None
    secure: Optional[bool] = None
    same_site: Optional[str] = None


class SetCookiesRequest(BaseModel):
    cookies: List[Cookie]


class SetCookiesResponse(BaseModel):
    success: bool
    message: str


class GetCookiesRequest(BaseModel):
    url: Optional[str] = None


class GetCookiesResponse(BaseModel):
    success: bool
    cookies: List[Cookie]
    message: str


def get_session(session_id: str):
    """获取会话，如果不存在则抛出 HTTP 异常"""
    session = browser_pool.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化浏览器池"""
    global browser_pool
    from config import get_config
    config = get_config()
    browser_pool = BrowserPool(config.MAX_SESSIONS, config.SESSION_TIMEOUT)
    logger.info(f"HTTP 服务器启动完成 (最大会话数: {config.MAX_SESSIONS})")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理浏览器池"""
    global browser_pool
    if browser_pool:
        await browser_pool.cleanup()
        logger.info("浏览器池已清理")


@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "name": "Browser RPC HTTP API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """创建浏览器会话"""
    try:
        proxy = None
        if request.proxy:
            proxy = {'server': request.proxy[0]}
        
        session_id = await browser_pool.create_session(
            headless=request.headless,
            user_agent=request.user_agent,
            proxy=proxy,
            width=request.width,
            height=request.height
        )
        
        logger.info(f"创建会话成功: {session_id}")
        return CreateSessionResponse(
            session_id=session_id,
            success=True,
            message="会话创建成功"
        )
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@app.delete("/api/sessions/{session_id}", response_model=CloseSessionResponse)
async def close_session(session_id: str):
    """关闭浏览器会话"""
    try:
        success = await browser_pool.close_session(session_id)
        if success:
            logger.info(f"关闭会话成功: {session_id}")
            return CloseSessionResponse(
                success=True,
                message="会话关闭成功"
            )
        else:
            raise HTTPException(status_code=404, detail="会话不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"关闭会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"关闭会话失败: {str(e)}")


@app.post("/api/sessions/{session_id}/navigate", response_model=NavigateResponse)
async def navigate(session_id: str, request: NavigateRequest):
    """导航到指定 URL"""
    try:
        session = get_session(session_id)
        final_url = await session.navigate(request.url, timeout=request.timeout)
        
        logger.info(f"导航成功: {request.url} -> {final_url}")
        return NavigateResponse(
            success=True,
            message="导航成功",
            final_url=final_url
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导航失败: {e}")
        raise HTTPException(status_code=500, detail=f"导航失败: {str(e)}")


@app.post("/api/sessions/{session_id}/execute", response_model=ExecuteScriptResponse)
async def execute_script(session_id: str, request: ExecuteScriptRequest):
    """执行 JavaScript"""
    try:
        session = get_session(session_id)
        result = await session.execute_script(request.script)
        
        logger.info(f"脚本执行成功")
        return ExecuteScriptResponse(
            success=True,
            result=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        return ExecuteScriptResponse(
            success=False,
            error=str(e)
        )


@app.get("/api/sessions/{session_id}/content", response_model=GetPageContentResponse)
async def get_page_content(session_id: str):
    """获取页面内容"""
    try:
        session = get_session(session_id)
        html = await session.get_content()
        
        logger.info(f"获取页面内容成功: {len(html)} 字节")
        return GetPageContentResponse(
            success=True,
            html=html,
            message="获取成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取页面内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@app.post("/api/sessions/{session_id}/network", response_model=GetNetworkRequestsResponse)
async def get_network_requests(session_id: str, request: GetNetworkRequestsRequest):
    """获取拦截的网络请求"""
    try:
        session = get_session(session_id)
        requests = session.get_network_requests(request.url_pattern)
        
        # 转换为响应格式
        network_requests = []
        for req in requests:
            resp = req.get('response', {})
            network_requests.append(NetworkRequest(
                request_id=req['request_id'],
                url=req['url'],
                method=req['method'],
                headers=req['headers'],
                post_data=req.get('post_data'),
                status_code=resp.get('status_code') if resp else None,
                response_body=resp.get('body') if resp else None,
                response_headers=resp.get('headers', {}) if resp else {},
                timestamp=req['timestamp']
            ))
        
        logger.info(f"获取网络请求成功: {len(network_requests)} 个")
        return GetNetworkRequestsResponse(
            success=True,
            requests=network_requests,
            message="获取成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取网络请求失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@app.post("/api/sessions/{session_id}/wait", response_model=WaitForElementResponse)
async def wait_for_element(session_id: str, request: WaitForElementRequest):
    """等待元素出现"""
    try:
        session = get_session(session_id)
        await session.wait_for_selector(request.selector, timeout=request.timeout)
        
        logger.info(f"等待元素成功: {request.selector}")
        return WaitForElementResponse(
            success=True,
            message="元素已出现"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"等待元素失败: {e}")
        raise HTTPException(status_code=500, detail=f"等待失败: {str(e)}")


@app.post("/api/sessions/{session_id}/click", response_model=ClickElementResponse)
async def click_element(session_id: str, request: ClickElementRequest):
    """点击元素"""
    try:
        session = get_session(session_id)
        await session.click(request.selector)
        
        logger.info(f"点击元素成功: {request.selector}")
        return ClickElementResponse(
            success=True,
            message="点击成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"点击元素失败: {e}")
        raise HTTPException(status_code=500, detail=f"点击失败: {str(e)}")


@app.post("/api/sessions/{session_id}/type", response_model=TypeTextResponse)
async def type_text(session_id: str, request: TypeTextRequest):
    """输入文本"""
    try:
        session = get_session(session_id)
        await session.type_text(request.selector, request.text)
        
        logger.info(f"输入文本成功: {request.selector}")
        return TypeTextResponse(
            success=True,
            message="输入成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"输入文本失败: {e}")
        raise HTTPException(status_code=500, detail=f"输入失败: {str(e)}")


@app.post("/api/sessions/{session_id}/screenshot", response_model=TakeScreenshotResponse)
async def take_screenshot(session_id: str, request: TakeScreenshotRequest):
    """页面截图"""
    try:
        session = get_session(session_id)
        image_data = await session.take_screenshot(
            selector=request.selector,
            full_page=request.full_page
        )
        
        # 转换为 base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        logger.info(f"截图成功")
        return TakeScreenshotResponse(
            success=True,
            image_data=image_base64,
            message="截图成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"截图失败: {e}")
        raise HTTPException(status_code=500, detail=f"截图失败: {str(e)}")


@app.post("/api/sessions/{session_id}/headers", response_model=SetHeadersResponse)
async def set_headers(session_id: str, request: SetHeadersRequest):
    """设置请求头"""
    try:
        session = get_session(session_id)
        await session.set_extra_http_headers(request.headers)
        
        logger.info(f"设置请求头成功")
        return SetHeadersResponse(
            success=True,
            message="设置成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置请求头失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置失败: {str(e)}")


@app.post("/api/sessions/{session_id}/cookies", response_model=SetCookiesResponse)
async def set_cookies(session_id: str, request: SetCookiesRequest):
    """设置 Cookie"""
    try:
        session = get_session(session_id)
        
        # 转换为 Playwright Cookie 格式
        cookies = []
        for cookie in request.cookies:
            cookie_dict = {
                'name': cookie.name,
                'value': cookie.value,
            }
            if cookie.domain:
                cookie_dict['domain'] = cookie.domain
            if cookie.path:
                cookie_dict['path'] = cookie.path
            if cookie.expires:
                cookie_dict['expires'] = cookie.expires
            if cookie.http_only is not None:
                cookie_dict['httpOnly'] = cookie.http_only
            if cookie.secure is not None:
                cookie_dict['secure'] = cookie.secure
            if cookie.same_site:
                cookie_dict['sameSite'] = cookie.same_site
            cookies.append(cookie_dict)
        
        await session.set_cookies(cookies)
        
        logger.info(f"设置 Cookie 成功: {len(cookies)} 个")
        return SetCookiesResponse(
            success=True,
            message="设置成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置 Cookie 失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置失败: {str(e)}")


@app.get("/api/sessions/{session_id}/cookies", response_model=GetCookiesResponse)
async def get_cookies(session_id: str, url: Optional[str] = None):
    """获取 Cookie"""
    try:
        session = get_session(session_id)
        cookies = await session.get_cookies(url)
        
        # 转换为响应格式
        cookie_list = []
        for cookie in cookies:
            cookie_list.append(Cookie(
                name=cookie['name'],
                value=cookie['value'],
                domain=cookie.get('domain'),
                path=cookie.get('path'),
                expires=cookie.get('expires'),
                http_only=cookie.get('httpOnly'),
                secure=cookie.get('secure'),
                same_site=cookie.get('sameSite')
            ))
        
        logger.info(f"获取 Cookie 成功: {len(cookie_list)} 个")
        return GetCookiesResponse(
            success=True,
            cookies=cookie_list,
            message="获取成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Cookie 失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    from config import get_config
    
    config = get_config()
    uvicorn.run(
        app,
        host=config.HTTP_HOST,
        port=config.HTTP_PORT,
        log_level="info"
    )

