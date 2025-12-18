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
    
    # HTTP 服务器配置
    HTTP_HOST: str = '0.0.0.0'
    HTTP_PORT: int = 8000
    
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
    
    # Redis 配置
    REDIS_URL: str = 'redis://localhost:6379/0'
    
    # 安全配置
    CLUSTER_SECRET: str = "browser-rpc-secret-key-change-me"  # 内部通信密钥
    API_KEY: Optional[str] = None  # 客户端访问密钥 (可选)

    def __init__(self):
        """从环境变量加载配置"""
        # 尝试从 .env 文件加载 (如果 python-dotenv 已安装)
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
            
        # 环境变量优先
        for key in dir(self):
            if key.isupper():
                env_value = os.getenv(key)
                if env_value is not None:
                    current_value = getattr(self, key)
                    # 类型转换
                    if isinstance(current_value, bool):
                        env_value = env_value.lower() in ('true', '1', 'yes')
                    elif isinstance(current_value, int):
                        try:
                            env_value = int(env_value)
                        except ValueError:
                            # 如果无法转换为 int，保持原值或忽略
                            continue
                    setattr(self, key, env_value)


# 全局配置实例
config = BrowserRPCConfig()


def get_config() -> BrowserRPCConfig:
    """获取配置实例"""
    return config

