#!/usr/bin/env python3
"""
Gateway 入口脚本（向后兼容）
从新包结构导入并启动 Gateway
"""
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / 'src'))

# 导入并运行 Gateway
if __name__ == '__main__':
    import uvicorn
    from browser_rpc.server.gateway import app

    # 从环境变量获取配置
    import os
    port = int(os.getenv('HTTP_PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
