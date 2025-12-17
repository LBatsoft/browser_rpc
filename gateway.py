import logging
import os
import sys
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse
import httpx
import websockets
from websockets.client import connect as ws_connect

from core.registry import NodeRegistry
from config import get_config

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

config = get_config()
registry: Optional[NodeRegistry] = None
# Disable SSL verification for sandbox compatibility
http_client = httpx.AsyncClient(verify=False)

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

@app.post("/api/sessions")
async def create_session(request: Request):
    """创建会话 - 负载均衡路由"""
    try:
        # 获取最佳节点
        node = await registry.get_best_node()
        if not node:
            raise HTTPException(status_code=503, detail="No available browser nodes")
        
        # 转发请求
        target_url = f"http://{node['host']}:{node['port']}/api/sessions"
        body = await request.json()
        
        logger.info(f"Forwarding create_session to {target_url}")
        response = await http_client.post(target_url, json=body, timeout=30.0)
        
        return JSONResponse(content=response.json(), status_code=response.status_code)
        
    except Exception as e:
        logger.error(f"Gateway create session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_node_for_session(session_id: str):
    """查找会话所在的节点"""
    node_info = await registry.get_session_node(session_id)
    if not node_info:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return node_info

@app.api_route("/api/sessions/{session_id}/{path:path}", methods=["GET", "POST", "DELETE", "PUT"])
async def proxy_request(session_id: str, path: str, request: Request):
    """通用请求代理 - 基于 Session ID 路由"""
    try:
        node = await get_node_for_session(session_id)
        target_url = f"http://{node['host']}:{node['port']}/api/sessions/{session_id}/{path}"
        
        # 构造请求参数
        params = {
            "method": request.method,
            "url": target_url,
            "headers": dict(request.headers),
            "params": dict(request.query_params),
            "timeout": 60.0
        }
        
        # 读取 Body
        if request.method not in ["GET", "HEAD"]:
            body = await request.body()
            params["content"] = body
            
        # 移除 Host header 避免冲突
        if "host" in params["headers"]:
            del params["headers"]["host"]
            
        logger.info(f"Proxying {request.method} {path} to {target_url}")
        response = await http_client.request(**params)
        
        return JSONResponse(content=response.json(), status_code=response.status_code)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Proxy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def close_session(session_id: str):
    """关闭会话代理"""
    # 单独处理 DELETE，因为它是根路径
    return await proxy_request(session_id, "", Request(scope={"method": "DELETE", "type": "http"}))

# WebSocket 代理
# 注意：FastAPI 实现 WebSocket 代理比较复杂，这里使用简化的管道模式
@app.websocket("/ws/sessions/{session_id}")
async def websocket_proxy(client_ws: WebSocket, session_id: str):
    await client_ws.accept()
    node_ws = None
    
    try:
        node = await get_node_for_session(session_id)
        target_ws_url = f"ws://{node['host']}:{node['port']}/ws/sessions/{session_id}"
        
        logger.info(f"Connecting proxy to backend: {target_ws_url}")
        
        async with ws_connect(target_ws_url) as node_ws:
            # 双向转发
            async def forward_to_node():
                try:
                    while True:
                        data = await client_ws.receive_text()
                        await node_ws.send(data)
                except Exception:
                    pass

            async def forward_to_client():
                try:
                    while True:
                        data = await node_ws.recv()
                        await client_ws.send_text(data)
                except Exception:
                    pass

            # 并发运行
            await asyncio.gather(forward_to_node(), forward_to_client())
            
    except Exception as e:
        logger.error(f"WebSocket proxy error: {e}")
        try:
            await client_ws.close(code=1011)
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

