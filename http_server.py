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

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cdp_client import BrowserPool
from core.registry import NodeRegistry
from core.metrics import (
    worker_requests_total, worker_request_duration_seconds,
    worker_active_sessions, worker_session_operations_total,
    get_metrics, get_metrics_content_type
)
import time
import os

# 配置日志
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

# 挂载静态文件
static_dir = os.path.join(os.path.dirname(__file__), 'static')
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 全局浏览器池
browser_pool: Optional[BrowserPool] = None
node_registry: Optional[NodeRegistry] = None


async def verify_cluster_secret(x_cluster_secret: Optional[str] = Header(None, alias="X-Cluster-Secret")):
    """验证内部集群通信密钥"""
    from config import get_config
    config = get_config()
    if config.CLUSTER_SECRET:
         if x_cluster_secret != config.CLUSTER_SECRET:
             raise HTTPException(status_code=403, detail="Invalid Cluster Secret")


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
    """应用启动时初始化浏览器池和注册节点"""
    global browser_pool, node_registry
    from config import get_config
    config = get_config()
    browser_pool = BrowserPool(config.MAX_SESSIONS, config.SESSION_TIMEOUT)
    logger.info(f"HTTP 服务器启动完成 (最大会话数: {config.MAX_SESSIONS})")
    
    # 初始化节点注册
    if config.REDIS_URL:
        try:
            node_registry = NodeRegistry(config.REDIS_URL)
            await node_registry.register_node()
            logger.info("节点注册成功")
        except Exception as e:
            logger.error(f"节点注册失败: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    global browser_pool, node_registry
    if browser_pool:
        await browser_pool.close_all()
        logger.info("浏览器池已清理")
    
    if node_registry:
        await node_registry.close()


@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "name": "Browser RPC HTTP API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    # 更新活跃会话数
    if browser_pool and node_registry:
        active_count = len(browser_pool.sessions)
        worker_active_sessions.labels(node_id=node_registry.node_id).set(active_count)
    
    from fastapi.responses import Response
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


@app.post("/api/sessions", response_model=CreateSessionResponse, dependencies=[Depends(verify_cluster_secret)])
async def create_session(request: CreateSessionRequest):
    """创建浏览器会话"""
    start_time = time.time()
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
        
        # 更新负载信息
        if node_registry:
            active_count = len(browser_pool.sessions)
            await node_registry.update_load(active_count)
            # 注册会话路由
            await node_registry.register_session(session_id, node_registry.node_id)
            # 更新指标
            worker_active_sessions.labels(node_id=node_registry.node_id).set(active_count)
        
        # 记录指标
        duration = time.time() - start_time
        worker_request_duration_seconds.labels(method='POST', endpoint='/api/sessions').observe(duration)
        worker_requests_total.labels(method='POST', endpoint='/api/sessions', status='success').inc()
        worker_session_operations_total.labels(operation='create', status='success').inc()
        
        logger.info(f"创建会话成功: {session_id}")
        return CreateSessionResponse(
            session_id=session_id,
            success=True,
            message="会话创建成功"
        )
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        # 记录错误指标
        duration = time.time() - start_time
        worker_request_duration_seconds.labels(method='POST', endpoint='/api/sessions').observe(duration)
        worker_requests_total.labels(method='POST', endpoint='/api/sessions', status='error').inc()
        worker_session_operations_total.labels(operation='create', status='error').inc()
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@app.delete("/api/sessions/{session_id}", response_model=CloseSessionResponse, dependencies=[Depends(verify_cluster_secret)])
async def close_session(session_id: str):
    """关闭浏览器会话"""
    start_time = time.time()
    try:
        success = await browser_pool.close_session(session_id)
        
        # 更新负载信息
        if node_registry:
            active_count = len(browser_pool.sessions)
            await node_registry.update_load(active_count)
            # 更新指标
            worker_active_sessions.labels(node_id=node_registry.node_id).set(active_count)
        
        # 记录指标
        duration = time.time() - start_time
        worker_request_duration_seconds.labels(method='DELETE', endpoint='/api/sessions/{session_id}').observe(duration)
        
        if success:
            worker_requests_total.labels(method='DELETE', endpoint='/api/sessions/{session_id}', status='success').inc()
            worker_session_operations_total.labels(operation='close', status='success').inc()
            logger.info(f"关闭会话成功: {session_id}")
            return CloseSessionResponse(
                success=True,
                message="会话关闭成功"
            )
        else:
            worker_requests_total.labels(method='DELETE', endpoint='/api/sessions/{session_id}', status='not_found').inc()
            worker_session_operations_total.labels(operation='close', status='not_found').inc()
            raise HTTPException(status_code=404, detail="会话不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"关闭会话失败: {e}")
        duration = time.time() - start_time
        worker_request_duration_seconds.labels(method='DELETE', endpoint='/api/sessions/{session_id}').observe(duration)
        worker_requests_total.labels(method='DELETE', endpoint='/api/sessions/{session_id}', status='error').inc()
        worker_session_operations_total.labels(operation='close', status='error').inc()
        raise HTTPException(status_code=500, detail=f"关闭会话失败: {str(e)}")


@app.post("/api/sessions/{session_id}/navigate", response_model=NavigateResponse, dependencies=[Depends(verify_cluster_secret)])
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


@app.post("/api/sessions/{session_id}/execute", response_model=ExecuteScriptResponse, dependencies=[Depends(verify_cluster_secret)])
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


@app.get("/api/sessions/{session_id}/content", response_model=GetPageContentResponse, dependencies=[Depends(verify_cluster_secret)])
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


@app.post("/api/sessions/{session_id}/network", response_model=GetNetworkRequestsResponse, dependencies=[Depends(verify_cluster_secret)])
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


@app.post("/api/sessions/{session_id}/wait", response_model=WaitForElementResponse, dependencies=[Depends(verify_cluster_secret)])
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


@app.post("/api/sessions/{session_id}/click", response_model=ClickElementResponse, dependencies=[Depends(verify_cluster_secret)])
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


@app.post("/api/sessions/{session_id}/type", response_model=TypeTextResponse, dependencies=[Depends(verify_cluster_secret)])
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


@app.post("/api/sessions/{session_id}/screenshot", response_model=TakeScreenshotResponse, dependencies=[Depends(verify_cluster_secret)])
async def take_screenshot(session_id: str, request: TakeScreenshotRequest):
    """页面截图"""
    try:
        session = get_session(session_id)
        image_data = await session.screenshot(
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


@app.post("/api/sessions/{session_id}/headers", response_model=SetHeadersResponse, dependencies=[Depends(verify_cluster_secret)])
async def set_headers(session_id: str, request: SetHeadersRequest):
    """设置请求头"""
    try:
        session = get_session(session_id)
        await session.set_extra_headers(request.headers)
        
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


@app.post("/api/sessions/{session_id}/cookies", response_model=SetCookiesResponse, dependencies=[Depends(verify_cluster_secret)])
async def set_cookies(session_id: str, request: SetCookiesRequest):
    """设置 Cookie"""
    try:
        session = get_session(session_id)
        
        # 转换为 Playwright Cookie 格式
        # Playwright 要求每个 Cookie 必须有 url 或 domain+path
        cookies = []
        # 获取当前页面 URL，如果没有页面则使用默认 URL
        try:
            current_url = session.page.url if session.page else None
        except:
            current_url = None
        
        if not current_url:
            # 如果没有当前页面，使用第一个 cookie 的 domain 构建 URL
            if request.cookies and request.cookies[0].domain:
                domain = request.cookies[0].domain.lstrip('.')
                current_url = f'https://{domain}'
            else:
                current_url = 'https://example.com'
        
        for cookie in request.cookies:
            cookie_dict = {
                'name': cookie.name,
                'value': cookie.value,
            }
            # Playwright 要求必须有 url 或 domain+path
            if cookie.domain:
                cookie_dict['domain'] = cookie.domain
                cookie_dict['path'] = cookie.path if cookie.path else '/'
            else:
                # 如果没有 domain，使用 url
                cookie_dict['url'] = current_url
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


@app.get("/api/sessions/{session_id}/cookies", response_model=GetCookiesResponse, dependencies=[Depends(verify_cluster_secret)])
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


# 简单的任务存储 (内存中)
# 实际生产环境应该使用数据库
recorded_tasks: Dict[str, List[Dict]] = {}

@app.websocket("/ws/sessions/{session_id}", dependencies=[Depends(verify_cluster_secret)])
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 远程控制接口"""
    await websocket.accept()
    
    try:
        # 获取会话 (不使用 get_session 包装器，避免 HTTPException)
        session = browser_pool.get_session(session_id)
        if not session:
            await websocket.close(code=4004, reason="Session not found")
            return

        # 录制状态
        is_recording = False
        current_recording = []
        
        # 定义发送帧的回调
        async def send_frame(data, metadata):
            try:
                # 顺便检查是否有新标签页，如果有，推送列表
                # 这是一个简化的做法，理想情况是基于事件
                # 为了性能，每 60 帧 (约1秒) 检查一次
                nonlocal frame_counter
                frame_counter += 1
                if frame_counter % 60 == 0:
                    pages = await session.get_pages()
                    if pages:
                        active_id = getattr(session.page, '_guid', None)
                        await websocket.send_json({
                            "type": "tabs",
                            "tabs": pages,
                            "activeId": active_id
                        })

                await websocket.send_json({
                    "type": "frame",
                    "data": data,
                    "metadata": metadata
                })
            except Exception as e:
                logger.error(f"WebSocket send frame error: {e}")
                # 连接断开时可能会报错，这里暂时忽略

        try:
            frame_counter = 0
            # 开启投射
            await session.start_screencast(send_frame)
            logger.info(f"WebSocket connected for session {session_id}")
            
            # 初始发送一次标签页列表
            pages = await session.get_pages()
            active_id = getattr(session.page, '_guid', None)
            await websocket.send_json({
                "type": "tabs",
                "tabs": pages,
                "activeId": active_id
            })
            
            while True:
                # 接收前端指令
                data = await websocket.receive_json()
                msg_type = data.get('type')
                
                if msg_type == 'input':
                    # 执行操作
                    event = data.get('event', {})
                    await session.handle_input_event(event)
                    
                    # 录制
                    if is_recording:
                        event_record = event.copy()
                        event_record['timestamp'] = time.time()
                        current_recording.append(event_record)
                        
                elif msg_type == 'control':
                    cmd = data.get('command')
                    if cmd == 'start_record':
                        is_recording = True
                        current_recording = []
                        logger.info(f"Session {session_id} started recording")
                        await websocket.send_json({"type": "status", "message": "Recording started"})
                        
                    elif cmd == 'stop_record':
                        is_recording = False
                        task_name = data.get('taskName', f"task_{int(time.time())}")
                        recorded_tasks[task_name] = current_recording
                        logger.info(f"Session {session_id} stopped recording, saved as {task_name}")
                        await websocket.send_json({
                            "type": "status", 
                            "message": f"Recording saved as {task_name}",
                            "taskName": task_name,
                            "eventCount": len(current_recording)
                        })
                        
                    elif cmd == 'replay':
                        task_name = data.get('taskName')
                        if task_name in recorded_tasks:
                            logger.info(f"Session {session_id} replaying task {task_name}")
                            await websocket.send_json({"type": "status", "message": f"Replaying {task_name}..."})
                            # 异步执行重放，避免阻塞 WebSocket 接收循环
                            asyncio.create_task(session.replay_events(recorded_tasks[task_name]))
                        else:
                            await websocket.send_json({"type": "error", "message": f"Task {task_name} not found"})
                    
                    elif cmd == 'switch_tab':
                        tab_id = data.get('tabId')
                        if tab_id:
                            await session.switch_to_page(tab_id)
                            # 切换后发送新的标签页列表
                            pages = await session.get_pages()
                            active_id = getattr(session.page, '_guid', None)
                            await websocket.send_json({
                                "type": "tabs",
                                "tabs": pages,
                                "activeId": active_id
                            })

                elif msg_type == 'ping':
                    await websocket.send_json({"type": "pong"})
            
            # 定时推送标签页信息 (简单的轮询机制，或者在 screencast 帧中附带)
            # 在这里我们无法轻松插入循环，只能依赖前端交互或事件触发
            # 改进：修改 _on_new_page 回调机制，允许传入 callback

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session {session_id}")
        except Exception as e:
            logger.error(f"WebSocket loop error: {e}")
        finally:
            # 停止投射
            try:
                await session.stop_screencast()
            except:
                pass

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=1011)
        except:
            pass


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

