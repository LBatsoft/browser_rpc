import asyncio
import os
import signal
import sys
import time
import subprocess
import requests
import json

# 配置
REDIS_PORT = 6379
GATEWAY_PORT = 8000
NODE1_PORT = 8001
NODE2_PORT = 8002

processes = []

def start_process(cmd, name, env=None):
    """启动子进程"""
    print(f"Starting {name}...")
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    
    # 重定向输出到文件
    log_file = open(f"{name}.log", "w")
    p = subprocess.Popen(
        cmd, 
        shell=True, 
        env=full_env,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    processes.append(p)
    return p

def cleanup():
    """清理进程"""
    print("\nCleaning up...")
    for p in processes:
        p.terminate()
        # p.kill() # 如果 terminate 不起作用
    
    # 尝试杀死可能残留的 Python 进程 (通过端口查找更准确，这里简化处理)
    subprocess.run("pkill -f 'python gateway.py'", shell=True)
    subprocess.run("pkill -f 'python http_server.py'", shell=True)
    print("Cleanup complete.")

async def wait_for_port(port, timeout=30):
    """等待端口就绪"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # 尝试连接端口
            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            writer.close()
            await writer.wait_closed()
            return True
        except:
            await asyncio.sleep(0.5)
    return False

async def run_tests():
    """执行测试"""
    print("\n=== Starting Integration Tests ===\n")

    # 1. 测试 Gateway 健康检查 (根路径)
    try:
        resp = requests.get(f"http://127.0.0.1:{GATEWAY_PORT}/")
        print(f"Gateway Root Check: {resp.status_code}")
        if resp.status_code == 200:
            print("  -> SUCCESS")
        else:
            print("  -> FAILED")
    except Exception as e:
        print(f"Gateway Root Check FAILED: {e}")

    # 2. 测试创建会话 (无 Auth - 应该失败)
    try:
        resp = requests.post(f"http://127.0.0.1:{GATEWAY_PORT}/api/sessions", json={"headless": True})
        print(f"\nCreate Session (No Auth): {resp.status_code}")
        # 注意：如果 config.API_KEY 未设置，这可能成功；如果设置了，应该 403
        # 我们默认 config 中 API_KEY 是 None，除非在 test_env 中设置
        # 在本次测试脚本中，我们将设置 API_KEY
        if resp.status_code == 403:
            print("  -> SUCCESS (Auth working)")
        else:
            print(f"  -> UNEXPECTED (Expected 403, got {resp.status_code})")
    except Exception as e:
        print(f"Create Session (No Auth) FAILED: {e}")

    # 3. 测试创建会话 (有 Auth)
    session_id = None
    headers = {"X-API-Key": "test-api-key"}
    try:
        resp = requests.post(
            f"http://127.0.0.1:{GATEWAY_PORT}/api/sessions", 
            json={"headless": True},
            headers=headers
        )
        print(f"\nCreate Session (With Auth): {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            session_id = data.get("session_id")
            print(f"  -> SUCCESS: Session ID {session_id}")
        else:
            print(f"  -> FAILED: {resp.text}")
    except Exception as e:
        print(f"Create Session (With Auth) FAILED: {e}")

    # 4. 如果创建成功，测试导航
    if session_id:
        try:
            resp = requests.post(
                f"http://127.0.0.1:{GATEWAY_PORT}/api/sessions/{session_id}/navigate",
                json={"url": "https://example.com"},
                headers=headers
            )
            print(f"\nNavigate: {resp.status_code}")
            if resp.status_code == 200:
                 print("  -> SUCCESS")
            else:
                 print(f"  -> FAILED: {resp.text}")
        except Exception as e:
            print(f"Navigate FAILED: {e}")

        # 5. 关闭会话
        try:
            resp = requests.delete(
                f"http://127.0.0.1:{GATEWAY_PORT}/api/sessions/{session_id}",
                headers=headers
            )
            print(f"\nClose Session: {resp.status_code}")
            if resp.status_code == 200:
                print("  -> SUCCESS")
            else:
                print(f"  -> FAILED")
        except Exception as e:
            print(f"Close Session FAILED: {e}")

    print("\n=== Tests Completed ===")

async def main():
    # 0. 检查 Redis 是否运行 (本地模拟前提)
    # 如果没有 Redis，这个测试脚本无法完全运行
    # 这里我们假设用户本地可能有 Redis，或者我们可以尝试跳过 Redis 依赖的某些部分？
    # 不，核心逻辑依赖 Redis。
    # 既然 Docker 失败，我们只能寄希望于本地有 Redis 或 python redis 库能连接到某个地方
    # 如果完全没有 Redis，我们只能测试 Gateway 的启动和 Auth 拒绝，无法测试转发
    
    # 设置环境变量
    common_env = {
        "REDIS_URL": "redis://localhost:6379/0", # 假设本地有 Redis
        "CLUSTER_SECRET": "test-secret",
        "API_KEY": "test-api-key"
    }

    # 启动 Gateway
    start_process(
        "python gateway.py", 
        "gateway", 
        env=common_env
    )

    # 启动 Node 1
    start_process(
        "python http_server.py", 
        "node1", 
        env={**common_env, "HTTP_PORT": str(NODE1_PORT)}
    )

    # 启动 Node 2
    start_process(
        "python http_server.py", 
        "node2", 
        env={**common_env, "HTTP_PORT": str(NODE2_PORT)}
    )

    print("Waiting for services to start...")
    
    # 等待端口
    if not await wait_for_port(GATEWAY_PORT):
        print("Gateway failed to start (timeout)")
        cleanup()
        return

    # 等待至少一个 Node 启动 (依赖 Redis 成功连接)
    # 如果本地没有 Redis，Node 启动会报错，Gateway 也会报错
    # 我们可以通过检查日志来确认
    
    await asyncio.sleep(5) # 给一点额外时间
    
    await run_tests()
    
    cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        cleanup()

