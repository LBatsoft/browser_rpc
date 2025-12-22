#!/usr/bin/env python3
"""
K8s 环境测试脚本
在 Kubernetes 集群内或通过端口转发测试 Browser RPC
"""
import requests
import os
import sys
import time
import subprocess
import json

# 配置
NAMESPACE = "browser-rpc"
GATEWAY_SVC = "gateway-service"
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

def run_kubectl(cmd):
    """运行 kubectl 命令"""
    try:
        result = subprocess.run(
            ["kubectl"] + cmd.split(),
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_cluster():
    """检查集群连接"""
    print("检查 Kubernetes 集群连接...")
    success, output, error = run_kubectl("cluster-info")
    if success:
        print("✅ 集群连接正常")
        return True
    else:
        print(f"❌ 集群连接失败: {error}")
        return False

def check_namespace():
    """检查命名空间"""
    print(f"\n检查命名空间 {NAMESPACE}...")
    success, output, error = run_kubectl(f"get namespace {NAMESPACE}")
    if success:
        print(f"✅ 命名空间 {NAMESPACE} 存在")
        return True
    else:
        print(f"❌ 命名空间 {NAMESPACE} 不存在")
        print("   请先运行: kubectl apply -f k8s/")
        return False

def get_pods():
    """获取 Pod 状态"""
    print(f"\n检查 Pod 状态...")
    success, output, error = run_kubectl(f"get pods -n {NAMESPACE} -o json")
    if not success:
        print(f"❌ 无法获取 Pod 状态: {error}")
        return []
    
    try:
        data = json.loads(output)
        pods = data.get("items", [])
        for pod in pods:
            name = pod["metadata"]["name"]
            status = pod["status"]["phase"]
            ready = "Ready" if any(
                condition["type"] == "Ready" and condition["status"] == "True"
                for condition in pod["status"].get("conditions", [])
            ) else "NotReady"
            print(f"  - {name}: {status} ({ready})")
        return pods
    except Exception as e:
        print(f"❌ 解析 Pod 信息失败: {e}")
        return []

def get_api_key():
    """从 Secret 获取 API Key"""
    print(f"\n获取 API Key...")
    success, output, error = run_kubectl(
        f"get secret browser-rpc-secrets -n {NAMESPACE} -o jsonpath='{{.data.API_KEY}}'"
    )
    if success and output:
        import base64
        try:
            api_key = base64.b64decode(output).decode('utf-8')
            print(f"✅ API Key 获取成功")
            return api_key
        except:
            pass
    
    print("⚠️  无法从 Secret 获取 API Key，使用环境变量或默认值")
    return API_KEY or "dev-test-key"

def test_gateway_api():
    """测试 Gateway API"""
    print(f"\n测试 Gateway API ({GATEWAY_URL})...")
    
    try:
        response = requests.get(f"{GATEWAY_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ Gateway 响应正常")
            return True
        else:
            print(f"❌ Gateway 返回错误状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到 {GATEWAY_URL}")
        print("   提示: 如果使用端口转发，请先运行:")
        print(f"   kubectl port-forward svc/{GATEWAY_SVC} 8000:8000 -n {NAMESPACE}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_create_session(api_key):
    """测试创建会话"""
    print(f"\n测试创建会话...")
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{GATEWAY_URL}/api/sessions",
            json={"headless": True, "width": 1280, "height": 720},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            print(f"✅ 会话创建成功: {session_id}")
            return session_id
        else:
            print(f"❌ 创建会话失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建会话异常: {e}")
        return None

def test_metrics():
    """测试 Metrics 端点"""
    print(f"\n测试 Metrics 端点...")
    
    try:
        response = requests.get(f"{GATEWAY_URL}/metrics", timeout=5)
        if response.status_code == 200:
            metrics_text = response.text
            count = metrics_text.count("gateway_requests_total")
            if count > 0:
                print(f"✅ Metrics 端点正常 (找到 {count} 个指标)")
                return True
            else:
                print("⚠️  Metrics 端点响应正常，但未找到预期指标")
                return False
        else:
            print(f"❌ Metrics 端点返回错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Metrics 测试失败: {e}")
        return False

def test_region_preference(api_key):
    """测试地域偏好"""
    print(f"\n测试地域偏好...")
    
    headers = {
        "X-API-Key": api_key,
        "X-Preferred-Region": "us-west",
        "X-Preferred-Zone": "us-west-2a",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{GATEWAY_URL}/api/sessions",
            json={"headless": True},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ 地域偏好请求成功")
            return True
        else:
            print(f"⚠️  地域偏好请求: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 地域偏好测试失败: {e}")
        return False

def main():
    print("=" * 60)
    print("Kubernetes 环境测试")
    print("=" * 60)
    
    # 检查集群
    if not check_cluster():
        sys.exit(1)
    
    # 检查命名空间
    if not check_namespace():
        sys.exit(1)
    
    # 获取 Pod 状态
    pods = get_pods()
    
    # 获取 API Key
    api_key = get_api_key()
    
    # 测试 Gateway API
    if not test_gateway_api():
        print("\n⚠️  Gateway API 测试失败，请检查:")
        print("   1. Pod 是否运行正常")
        print("   2. 是否启动了端口转发")
        print("   3. GATEWAY_URL 环境变量是否正确")
        sys.exit(1)
    
    # 测试创建会话
    session_id = test_create_session(api_key)
    
    # 测试 Metrics
    test_metrics()
    
    # 测试地域偏好
    test_region_preference(api_key)
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"集群连接: ✅")
    print(f"命名空间: ✅")
    print(f"Pod 数量: {len(pods)}")
    print(f"Gateway API: {'✅' if session_id else '❌'}")
    print(f"会话创建: {'✅' if session_id else '❌'}")
    
    if session_id:
        print(f"\n✅ 测试通过！会话 ID: {session_id}")
    else:
        print(f"\n❌ 部分测试失败，请检查日志")
        sys.exit(1)

if __name__ == "__main__":
    main()

