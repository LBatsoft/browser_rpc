import asyncio
import json
import logging
import socket
import time
import uuid
import os
from typing import Dict, List, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

class NodeRegistry:
    """节点注册与发现"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.node_id = str(uuid.uuid4())
        self.host = self._get_local_ip()
        self.port = int(os.getenv('HTTP_PORT', 8000))
        self.max_sessions = int(os.getenv('MAX_SESSIONS', 10))
        self.is_running = False
        
    def _get_local_ip(self):
        """获取本机 IP 或容器名（Docker 环境）"""
        # 优先使用环境变量（Docker Compose 可以设置）
        node_host = os.getenv('NODE_HOST')
        if node_host:
            return node_host
        
        # 在 Docker 环境中，尝试使用容器名（hostname）
        # 这样 Gateway 可以通过容器名访问 Worker
        try:
            hostname = socket.gethostname()
            # 检查是否在 Docker 中（hostname 通常是容器名）
            # 如果 hostname 不是 localhost 或 127.0.0.1，很可能是容器名
            if hostname and hostname not in ('localhost', '127.0.0.1'):
                # 尝试解析，如果失败则直接使用 hostname（容器名）
                try:
                    ip = socket.gethostbyname(hostname)
                    # 如果解析出的是 127.0.0.1，说明不在 Docker 网络中，使用 hostname
                    if ip == '127.0.0.1':
                        return hostname
                    return ip
                except:
                    # 解析失败，直接使用 hostname（容器名）
                    return hostname
            else:
                # 非 Docker 环境，使用 IP
                return socket.gethostbyname(hostname) if hostname else '127.0.0.1'
        except:
            return '127.0.0.1'

    async def connect(self):
        """连接 Redis"""
        if not self.redis:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Connected to Redis: {self.redis_url}")

    async def register_node(self):
        """注册节点"""
        await self.connect()
        self.is_running = True
        asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Node registered: {self.node_id} ({self.host}:{self.port})")

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.is_running:
            try:
                # 更新节点信息
                node_info = {
                    'id': self.node_id,
                    'host': self.host,
                    'port': self.port,
                    'max_sessions': self.max_sessions,
                    'last_seen': time.time()
                }
                
                # 使用 Hash 存储节点信息
                await self.redis.hset('nodes', self.node_id, json.dumps(node_info))
                
                # 设置过期时间（例如 10 秒后过期，心跳每 5 秒一次）
                # 注意：Redis Hash 的字段不能单独设置过期，所以我们可以在应用层过滤
                # 或者使用单独的 key: node:{id} 并设置 expire
                await self.redis.set(f"node_heartbeat:{self.node_id}", "1", ex=15)
                
                logger.debug(f"Heartbeat sent for {self.node_id}")
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
            
            await asyncio.sleep(5)

    async def update_load(self, active_sessions: int):
        """更新负载信息"""
        if not self.redis: return
        try:
            await self.redis.hset(f"node_load:{self.node_id}", "active", active_sessions)
        except Exception as e:
            logger.error(f"Failed to update load: {e}")

    async def get_best_node(self, exclude_nodes: List[str] = None) -> Optional[Dict]:
        """获取最佳可用节点 (简单的最少连接数策略)"""
        await self.connect()
        exclude_nodes = exclude_nodes or []
        try:
            nodes = await self.redis.hgetall('nodes')
            best_node = None
            min_load = float('inf')
            
            for node_id, info_str in nodes.items():
                if node_id in exclude_nodes:
                    continue
                    
                # 检查心跳
                if not await self.redis.exists(f"node_heartbeat:{node_id}"):
                    # 清理过期节点
                    await self.redis.hdel('nodes', node_id)
                    continue
                
                info = json.loads(info_str)
                
                # 获取负载
                load = await self.redis.hget(f"node_load:{node_id}", "active")
                current_load = int(load) if load else 0
                
                if current_load < info['max_sessions']:
                    if current_load < min_load:
                        min_load = current_load
                        best_node = info
            
            return best_node
        except Exception as e:
            logger.error(f"Failed to get best node: {e}")
            return None

    async def register_session(self, session_id: str, node_id: str):
        """注册会话位置"""
        await self.connect()
        # session -> node_id
        await self.redis.set(f"session_route:{session_id}", node_id, ex=3600)

    async def get_session_node(self, session_id: str) -> Optional[Dict]:
        """获取会话所在的节点信息"""
        await self.connect()
        node_id = await self.redis.get(f"session_route:{session_id}")
        if not node_id:
            return None
            
        info_str = await self.redis.hget('nodes', node_id)
        if info_str:
            return json.loads(info_str)
        return None

    async def close(self):
        self.is_running = False
        if self.redis:
            await self.redis.close()

