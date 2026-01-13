#!/usr/bin/env python3
"""
RPC Client 入口脚本（向后兼容）
从新包结构导入 RPC Client
"""
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / 'src'))

# 导出主要接口
from browser_rpc.client.rpc_client import BrowserRPCClient

__all__ = ['BrowserRPCClient']

# 如果作为脚本运行，执行示例代码
if __name__ == '__main__':
    import asyncio
    
    async def example():
        client = BrowserRPCClient(host='localhost', port=50051)
        await client.connect()
        print("RPC Client connected successfully!")
        await client.close()
    
    asyncio.run(example())
