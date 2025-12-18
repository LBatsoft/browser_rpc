#!/usr/bin/env python3
"""
本地测试脚本 - 演示如何正确调用 Gateway API
"""
import requests
import sys

# 配置
GATEWAY_URL = "http://localhost:8000"
API_KEY = "dev-test-key"  # 对应 docker-compose.yml 中的配置

def test_create_session():
    """测试创建会话"""
    print(f"Testing: POST {GATEWAY_URL}/api/sessions")
    print(f"API Key: {API_KEY}")
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(
            f"{GATEWAY_URL}/api/sessions",
            json={"headless": True, "width": 1280, "height": 720},
            headers=headers
        )
        
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Success! Session ID: {data.get('session_id')}")
            return data.get('session_id')
        else:
            print(f"❌ Failed: {resp.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Cannot connect to {GATEWAY_URL}")
        print("   Make sure Gateway is running: docker compose up -d gateway")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_without_auth():
    """测试不带 API Key 的情况（应该失败）"""
    print("\n" + "="*50)
    print("Testing without API Key (should fail):")
    print("="*50)
    
    try:
        resp = requests.post(
            f"{GATEWAY_URL}/api/sessions",
            json={"headless": True}
        )
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("="*50)
    print("Browser RPC Gateway - Local Test")
    print("="*50)
    
    # 测试带认证的请求
    session_id = test_create_session()
    
    # 测试不带认证的请求（演示错误）
    if len(sys.argv) > 1 and sys.argv[1] == "--show-error":
        test_without_auth()
    
    if session_id:
        print(f"\n✅ Test passed! You can now use session_id: {session_id}")
        print(f"\nNext steps:")
        print(f"  1. Navigate: POST {GATEWAY_URL}/api/sessions/{session_id}/navigate")
        print(f"  2. Screenshot: POST {GATEWAY_URL}/api/sessions/{session_id}/screenshot")
        print(f"  3. Close: DELETE {GATEWAY_URL}/api/sessions/{session_id}")
    else:
        print("\n❌ Test failed. Check the error messages above.")
        sys.exit(1)

