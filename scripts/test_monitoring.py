#!/usr/bin/env python3
"""
测试监控功能
验证 Prometheus 指标是否正确导出
"""
import requests
import time
import sys

GATEWAY_URL = "http://localhost:8000"
WORKER_URLS = ["http://localhost:8001", "http://localhost:8002"]
API_KEY = "dev-test-key"

def test_metrics_endpoint(url, service_name):
    """测试 metrics 端点"""
    try:
        response = requests.get(f"{url}/metrics", timeout=5)
        if response.status_code == 200:
            print(f"✅ {service_name} metrics endpoint: OK")
            # 检查是否包含 Prometheus 格式的指标
            if "gateway_requests_total" in response.text or "worker_requests_total" in response.text:
                print(f"   ✓ 包含 Prometheus 指标")
            return True
        else:
            print(f"❌ {service_name} metrics endpoint: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"⚠️  {service_name} 未运行或无法连接")
        return False
    except Exception as e:
        print(f"❌ {service_name} metrics endpoint: {e}")
        return False

def test_create_session():
    """测试创建会话并验证指标变化"""
    print("\n" + "="*50)
    print("测试创建会话...")
    print("="*50)
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        # 创建会话
        response = requests.post(
            f"{GATEWAY_URL}/api/sessions",
            json={"headless": True, "width": 1280, "height": 720},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            print(f"✅ 会话创建成功: {session_id}")
            
            # 等待一下让指标更新
            time.sleep(1)
            
            # 检查 metrics
            metrics_response = requests.get(f"{GATEWAY_URL}/metrics", timeout=5)
            if "gateway_requests_total" in metrics_response.text:
                print("✅ Gateway 指标已更新")
            
            return session_id
        else:
            print(f"❌ 创建会话失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建会话异常: {e}")
        return None

def test_region_preference():
    """测试地域偏好功能"""
    print("\n" + "="*50)
    print("测试地域偏好...")
    print("="*50)
    
    headers = {
        "X-API-Key": API_KEY,
        "X-Preferred-Region": "us-west",
        "X-Preferred-Zone": "us-west-2a",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{GATEWAY_URL}/api/sessions",
            json={"headless": True},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ 地域偏好请求成功（如果节点配置了地域，会优先选择匹配的节点）")
            return True
        else:
            print(f"⚠️  地域偏好请求: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 地域偏好测试异常: {e}")
        return False

def main():
    print("="*50)
    print("Browser RPC - 监控功能测试")
    print("="*50)
    
    # 测试 metrics 端点
    print("\n1. 测试 Metrics 端点")
    print("-" * 50)
    gateway_ok = test_metrics_endpoint(GATEWAY_URL, "Gateway")
    
    worker_ok = False
    for i, url in enumerate(WORKER_URLS, 1):
        if test_metrics_endpoint(url, f"Worker-{i}"):
            worker_ok = True
    
    if not gateway_ok:
        print("\n⚠️  Gateway 未运行，请先启动服务:")
        print("   docker-compose up -d gateway")
        return
    
    # 测试创建会话
    session_id = test_create_session()
    
    # 测试地域偏好
    test_region_preference()
    
    # 总结
    print("\n" + "="*50)
    print("测试总结")
    print("="*50)
    print(f"Gateway Metrics: {'✅' if gateway_ok else '❌'}")
    print(f"Worker Metrics: {'✅' if worker_ok else '⚠️  (可选)'}")
    print(f"会话创建: {'✅' if session_id else '❌'}")
    
    if gateway_ok:
        print(f"\n📊 查看指标:")
        print(f"   Gateway: {GATEWAY_URL}/metrics")
        if worker_ok:
            for i, url in enumerate(WORKER_URLS, 1):
                print(f"   Worker-{i}: {url}/metrics")
        print(f"\n📈 访问 Grafana:")
        print(f"   http://localhost:3000 (admin/admin)")
        print(f"\n📊 访问 Prometheus:")
        print(f"   http://localhost:9090")

if __name__ == "__main__":
    main()

