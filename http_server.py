#!/usr/bin/env python3
"""
HTTP Server 入口脚本（向后兼容）
从新包结构导入并启动 HTTP Server
"""
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / 'src'))

# 导入并运行 HTTP Server
if __name__ == '__main__':
    # 直接运行模块的 __main__ 块
    import browser_rpc.server.http_server
