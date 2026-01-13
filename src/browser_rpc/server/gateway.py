import logging
import os
import sys
import asyncio  # Added missing import
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, Security, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security.api_key import APIKeyHeader
import httpx
import websockets
from websockets.client import connect as ws_connect

from browser_rpc.core.registry import NodeRegistry
from browser_rpc.core.metrics import (
    gateway_requests_total, gateway_request_duration_seconds,
    gateway_retry_total, gateway_node_selection_total,
    get_metrics, get_metrics_content_type
)
from browser_rpc.core.config import get_config
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Browser RPC Gateway",
    description="Unified Gateway for Browser RPC Cluster",
    version="1.0.0"
)

# 挂载静态文件 (用于远程控制前端)
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
static_dir = BASE_DIR / 'static'
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

config = get_config()
registry: Optional[NodeRegistry] = None
# Disable SSL verification for sandbox compatibility
http_client = httpx.AsyncClient(verify=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_client_auth(
    request: Request,
    api_key: str = Security(api_key_header)
):
    """验证客户端 API Key (支持 Header 和 Query Param)"""
    # 如果未配置 API_KEY，则跳过验证（本地开发模式）
    if not config.API_KEY:
        logger.debug("API_KEY not configured, skipping authentication")
        return
        
    # 1. 优先检查 Header (由 Security 自动提取，若无则 api_key 为 None)
    if api_key == config.API_KEY:
        return

    # 2. 检查 Query Param (针对 WebSocket 等无法设置 Header 的场景)
    query_token = request.query_params.get("token")
    if query_token == config.API_KEY:
        return
        
    # 3. 验证失败 - 不泄露实际 API Key
    logger.warning(f"API Key validation failed. Header provided: {bool(api_key)}, Query provided: {bool(query_token)}")
    raise HTTPException(
        status_code=403, 
        detail="Invalid API Key. Please provide 'X-API-Key' header or 'token' query parameter."
    )

def get_upstream_headers(original_headers: dict = None) -> dict:
    """构造上游请求头，注入内部通信密钥"""
    headers = dict(original_headers or {})
    headers["X-Cluster-Secret"] = config.CLUSTER_SECRET
    # 移除可能引起冲突的 Header
    headers.pop("host", None)
    headers.pop("content-length", None)
    return headers

@app.on_event("startup")
async def startup_event():
    global registry
    if config.REDIS_URL:
        registry = NodeRegistry(config.REDIS_URL)
        await registry.connect()
        logger.info("Gateway connected to Redis")

@app.on_event("shutdown")
async def shutdown_event():
    if registry:
        await registry.close()
    await http_client.aclose()

@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    from fastapi.responses import Response
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )

@app.post("/api/sessions", dependencies=[Depends(verify_client_auth)])
async def create_session(request: Request):
    """
    创建会话 - 负载均衡路由 (带重试机制)
    
    支持地域调度：
    - 通过 Header: X-Preferred-Region, X-Preferred-Zone
    - 或通过请求体: preferred_region, preferred_zone
    """
    start_time = time.time()
    exclude_nodes = []
    last_exception = None
    
    # 读取一次 body，因为 request.json() 是 async 的且 stream 可能会被消耗
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    # 获取地域偏好（优先从 Header，其次从请求体）
    preferred_region = request.headers.get('X-Preferred-Region') or body.get('preferred_region')
    preferred_zone = request.headers.get('X-Preferred-Zone') or body.get('preferred_zone')
    
    # 从 body 中移除地域偏好（避免传递给 Worker）
    body_clean = {k: v for k, v in body.items() if k not in ('preferred_region', 'preferred_zone')}

    # 最多尝试 3 个不同节点
    for attempt in range(3):
        try:
            # 获取最佳节点（支持地域偏好）
            node = await registry.get_best_node(
                exclude_nodes=exclude_nodes,
                preferred_region=preferred_region,
                preferred_zone=preferred_zone
            )
            if not node:
                break
            
            # 记录节点选择
            gateway_node_selection_total.labels(node_id=node['id'], status='selected').inc()
            
            # 转发请求
            target_url = f"http://{node['host']}:{node['port']}/api/sessions"
            
            logger.info(f"Forwarding create_session to {target_url} (Attempt {attempt+1})")
            
            # 注入内部通信密钥
            headers = get_upstream_headers()
            
            response = await http_client.post(target_url, json=body_clean, headers=headers, timeout=10.0)
            
            if response.status_code >= 500:
                # 如果是服务端错误，可能是该节点有问题，尝试其他节点
                logger.warning(f"Node {node['id']} returned {response.status_code}")
                gateway_node_selection_total.labels(node_id=node['id'], status='failed').inc()
                gateway_retry_total.labels(operation='create_session', reason='server_error').inc()
                exclude_nodes.append(node['id'])
                continue
            
            # 记录成功指标
            duration = time.time() - start_time
            gateway_request_duration_seconds.labels(method='POST', endpoint='/api/sessions').observe(duration)
            gateway_requests_total.labels(method='POST', endpoint='/api/sessions', status='success').inc()
            
            return JSONResponse(content=response.json(), status_code=response.status_code)
            
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError) as e:
            node_id = node.get('id', 'unknown') if node else 'unknown'
            logger.warning(f"Failed to connect to node {node_id}: {e}")
            if node:
                gateway_node_selection_total.labels(node_id=node['id'], status='connection_error').inc()
                gateway_retry_total.labels(operation='create_session', reason='connection_error').inc()
                exclude_nodes.append(node['id'])
            last_exception = e
        except Exception as e:
            logger.error(f"Gateway create session failed: {e}")
            # 记录错误指标
            duration = time.time() - start_time
            gateway_request_duration_seconds.labels(method='POST', endpoint='/api/sessions').observe(duration)
            gateway_requests_total.labels(method='POST', endpoint='/api/sessions', status='error').inc()
            # 非网络错误直接抛出
            raise HTTPException(status_code=500, detail=str(e))
            
    # 记录失败指标
    duration = time.time() - start_time
    gateway_request_duration_seconds.labels(method='POST', endpoint='/api/sessions').observe(duration)
    gateway_requests_total.labels(method='POST', endpoint='/api/sessions', status='failed').inc()
    
    error_msg = f"Failed to create session after 3 attempts. Last error: {last_exception}"
    logger.error(error_msg)
    raise HTTPException(status_code=503, detail=error_msg)

async def get_node_for_session(session_id: str):
    """查找会话所在的节点"""
    node_info = await registry.get_session_node(session_id)
    if not node_info:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return node_info

@app.api_route("/api/sessions/{session_id}/{path:path}", methods=["GET", "POST", "DELETE", "PUT"], dependencies=[Depends(verify_client_auth)])
async def proxy_request(session_id: str, path: str, request: Request):
    """通用请求代理 - 基于 Session ID 路由"""
    start_time = time.time()
    endpoint = f"/api/sessions/{session_id}/{path}"
    
    try:
        node = await get_node_for_session(session_id)
        target_url = f"http://{node['host']}:{node['port']}/api/sessions/{session_id}/{path}"
        
        # 构造请求参数
        headers = get_upstream_headers(request.headers)
        
        params = {
            "method": request.method,
            "url": target_url,
            "headers": headers,
            "params": dict(request.query_params),
            "timeout": 30.0
        }
        
        # 读取 Body
        if request.method not in ["GET", "HEAD"]:
            body = await request.body()
            params["content"] = body
            
        # 重试逻辑 (针对网络波动)
        last_error = None
        for attempt in range(3):
            try:
                logger.info(f"Proxying {request.method} {path} to {target_url} (Attempt {attempt+1})")
                response = await http_client.request(**params)
                
                # 记录成功指标
                duration = time.time() - start_time
                gateway_request_duration_seconds.labels(method=request.method, endpoint=endpoint).observe(duration)
                status = 'success' if response.status_code < 400 else 'client_error' if response.status_code < 500 else 'server_error'
                gateway_requests_total.labels(method=request.method, endpoint=endpoint, status=status).inc()
                
                # 透传响应状态码和内容
                content = response.content
                try:
                     # 尝试解析 JSON，如果不是 JSON 则直接返回内容
                     json_content = response.json()
                     return JSONResponse(content=json_content, status_code=response.status_code)
                except:
                     from fastapi.responses import Response
                     return Response(content=content, status_code=response.status_code)

            except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError) as e:
                logger.warning(f"Proxy request failed (Attempt {attempt+1}): {e}")
                gateway_retry_total.labels(operation='proxy_request', reason='network_error').inc()
                last_error = e
                await asyncio.sleep(0.5)
        
        # 记录失败指标
        duration = time.time() - start_time
        gateway_request_duration_seconds.labels(method=request.method, endpoint=endpoint).observe(duration)
        gateway_requests_total.labels(method=request.method, endpoint=endpoint, status='failed').inc()
        
        raise HTTPException(status_code=504, detail=f"Upstream request failed after 3 attempts: {last_error}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Proxy failed: {e}")
        duration = time.time() - start_time
        gateway_request_duration_seconds.labels(method=request.method, endpoint=endpoint).observe(duration)
        gateway_requests_total.labels(method=request.method, endpoint=endpoint, status='error').inc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}", dependencies=[Depends(verify_client_auth)])
async def close_session(session_id: str):
    """关闭会话代理"""
    # 单独处理 DELETE，因为它是根路径
    return await proxy_request(session_id, "", Request(scope={"method": "DELETE", "type": "http"}))

# WebSocket 代理
# 注意：FastAPI 实现 WebSocket 代理比较复杂，这里使用简化的管道模式
@app.websocket("/ws/sessions/{session_id}")
async def websocket_proxy(client_ws: WebSocket, session_id: str):
    # WebSocket 鉴权需要手动处理，因为 Depends 在 WebSocket 中行为不同
    # 或者是接受后再关闭
    await client_ws.accept()
    
    # 手动验证 token
    token = client_ws.query_params.get("token")
    if config.API_KEY and token != config.API_KEY:
         logger.warning(f"WebSocket auth failed for session {session_id}")
         await client_ws.close(code=1008, reason="Invalid API Key")
         return
    
    try:
        node = await get_node_for_session(session_id)
        target_ws_url = f"ws://{node['host']}:{node['port']}/ws/sessions/{session_id}"
        
        logger.info(f"Connecting proxy to backend: {target_ws_url}")
        
        # 注入内部密钥
        extra_headers = {"X-Cluster-Secret": config.CLUSTER_SECRET}
        
        async with ws_connect(target_ws_url, extra_headers=extra_headers) as node_ws:
            # 双向转发
            async def forward_to_node():
                try:
                    while True:
                        data = await client_ws.receive_text()
                        await node_ws.send(data)
                except WebSocketDisconnect:
                    logger.info(f"Client disconnected for session {session_id}")
                except Exception as e:
                    logger.error(f"Error forwarding to node: {e}")

            async def forward_to_client():
                try:
                    while True:
                        data = await node_ws.recv()
                        await client_ws.send_text(data)
                except websockets.exceptions.ConnectionClosed as e:
                    logger.info(f"Node disconnected for session {session_id}: {e.code}")
                    await client_ws.close(code=1011, reason="Upstream closed")
                except Exception as e:
                    logger.error(f"Error forwarding to client: {e}")

            # 使用 asyncio.wait 等待任一任务结束
            done, pending = await asyncio.wait(
                [asyncio.create_task(forward_to_node()), asyncio.create_task(forward_to_client())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 取消剩余任务
            for task in pending:
                task.cancel()
            
    except HTTPException as e:
        logger.error(f"WebSocket handshake failed: {e.detail}")
        await client_ws.close(code=1008, reason=e.detail)
    except Exception as e:
        logger.error(f"WebSocket proxy error: {e}")
        try:
            await client_ws.close(code=1011, reason="Proxy internal error")
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

