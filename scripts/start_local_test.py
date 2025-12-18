#!/usr/bin/env python3
"""
本地测试启动脚本
用于在非 Docker 环境中快速启动 Gateway + Worker + Redis
"""
import subprocess
import sys
import os
import time
import signal
import requests

processes = []

def cleanup():
    """清理进程"""
    print("\n清理进程...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except:
            try:
                p.kill()
            except:
                pass
    print("清理完成")

def check_redis():
    """检查 Redis 是否运行"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        return True
    except:
        return False

def start_redis():
    """启动 Redis（如果未运行）"""
    if check_redis():
        print("✅ Redis 已在运行")
        return None
    
    print("启动 Redis...")
    # 尝试使用本地 redis-server
    try:
        p = subprocess.Popen(
            ['redis-server', '--port', '6379'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)
        if check_redis():
            print("✅ Redis 启动成功")
            return p
        else:
            print("❌ Redis 启动失败，请手动启动: redis-server")
            return None
    except FileNotFoundError:
        print("⚠️  redis-server 未找到，请手动启动 Redis:")
        print("   macOS: brew install redis && brew services start redis")
        print("   Linux: sudo apt-get install redis-server && sudo systemctl start redis")
        return None

def start_worker(port, node_name):
    """启动 Worker 节点"""
    env = os.environ.copy()
    env.update({
        'HTTP_PORT': str(port),
        'MAX_SESSIONS': '5',
        'REDIS_URL': 'redis://localhost:6379/0',
        'CLUSTER_SECRET': 'dev-cluster-secret',
        'NODE_HOST': 'localhost'  # 本地环境使用 localhost
    })
    
    print(f"启动 Worker {node_name} (端口 {port})...")
    p = subprocess.Popen(
        [sys.executable, 'http_server.py'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return p

def start_gateway():
    """启动 Gateway"""
    env = os.environ.copy()
    env.update({
        'REDIS_URL': 'redis://localhost:6379/0',
        'API_KEY': 'dev-test-key',
        'CLUSTER_SECRET': 'dev-cluster-secret'
    })
    
    print("启动 Gateway (端口 8000)...")
    p = subprocess.Popen(
        [sys.executable, 'gateway.py'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return p

def wait_for_service(url, name, timeout=30):
    """等待服务启动"""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code < 500:
                print(f"✅ {name} 已就绪")
                return True
        except:
            pass
        time.sleep(1)
    print(f"❌ {name} 启动超时")
    return False

def test_gateway():
    """测试 Gateway"""
    print("\n" + "="*50)
    print("测试 Gateway API...")
    print("="*50)
    
    headers = {
        "X-API-Key": "dev-test-key",
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(
            "http://localhost:8000/api/sessions",
            json={"headless": True},
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ 创建会话成功: {data.get('session_id')}")
            return True
        else:
            print(f"❌ 创建会话失败: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    print("="*50)
    print("Browser RPC - 本地测试环境启动")
    print("="*50)
    
    # 注册清理函数
    signal.signal(signal.SIGINT, lambda s, f: cleanup() or sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: cleanup() or sys.exit(0))
    
    # 1. 启动 Redis
    redis_proc = start_redis()
    if redis_proc:
        processes.append(redis_proc)
    
    if not check_redis():
        print("❌ Redis 未运行，无法继续")
        print("请先启动 Redis，然后重新运行此脚本")
        sys.exit(1)
    
    # 2. 启动 Worker 节点
    worker1 = start_worker(8001, "Worker-1")
    processes.append(worker1)
    
    worker2 = start_worker(8002, "Worker-2")
    processes.append(worker2)
    
    # 3. 启动 Gateway
    gateway = start_gateway()
    processes.append(gateway)
    
    # 4. 等待服务启动
    print("\n等待服务启动...")
    time.sleep(5)
    
    wait_for_service("http://localhost:8001/", "Worker-1")
    wait_for_service("http://localhost:8002/", "Worker-2")
    wait_for_service("http://localhost:8000/", "Gateway")
    
    # 5. 测试
    print("\n" + "="*50)
    print("服务启动完成！")
    print("="*50)
    print("\n访问地址:")
    print("  - Gateway: http://localhost:8000")
    print("  - 远程控制: http://localhost:8000/static/remote.html")
    print("  - API 文档: http://localhost:8000/docs")
    print("\n按 Ctrl+C 停止所有服务\n")
    
    # 运行测试
    time.sleep(3)
    test_gateway()
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()

