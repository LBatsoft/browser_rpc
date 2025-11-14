"""
浏览器 RPC 配置文件
"""

import os
from typing import Optional


class BrowserRPCConfig:
    """RPC 服务配置"""
    
    # 服务器配置
    RPC_HOST: str = '0.0.0.0'
    RPC_PORT: int = 50051
    RPC_MAX_WORKERS: int = 10
    
    # 浏览器池配置
    MAX_SESSIONS: int = 10
    SESSION_TIMEOUT: int = 3600  # 会话超时时间（秒）
    
    # 浏览器配置
    DEFAULT_HEADLESS: bool = True
    DEFAULT_WIDTH: int = 1920
    DEFAULT_HEIGHT: int = 1080
    
    # 日志配置
    LOG_LEVEL: str = 'INFO'
    LOG_DIR: str = 'browser_rpc/log'
    
    # 代理配置（可选）
    PROXY_SERVER: Optional[str] = None
    
    def __init__(self):
        """从环境变量加载配置"""
        # 尝试从 .env 文件加载
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # 转换类型
                        if hasattr(self, key):
                            current_value = getattr(self, key)
                            if isinstance(current_value, bool):
                                value = value.lower() in ('true', '1', 'yes')
                            elif isinstance(current_value, int):
                                value = int(value)
                            setattr(self, key, value)
        
        # 环境变量优先
        for key in dir(self):
            if key.isupper():
                env_value = os.getenv(key)
                if env_value is not None:
                    current_value = getattr(self, key)
                    if isinstance(current_value, bool):
                        env_value = env_value.lower() in ('true', '1', 'yes')
                    elif isinstance(current_value, int):
                        env_value = int(env_value)
                    setattr(self, key, env_value)


# 全局配置实例
config = BrowserRPCConfig()


def get_config() -> BrowserRPCConfig:
    """获取配置实例"""
    return config

