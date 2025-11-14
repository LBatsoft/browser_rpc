"""
HTTP API 测试脚本
测试浏览器 RPC HTTP 服务的各项功能
"""

import asyncio
import sys
from http_client import BrowserHTTPClient


async def test_basic_operations():
    """测试基础操作"""
    print("=" * 60)
    print("测试 1: 基础操作")
    print("=" * 60)
    
    client = BrowserHTTPClient(base_url='http://localhost:8000')
    
    try:
        # 创建会话
        print("\n1. 创建浏览器会话...")
        session_id = await client.create_session(headless=True)
        print(f"   ✅ 会话创建成功: {session_id}")
        
        # 导航到页面
        print("\n2. 导航到页面...")
        final_url = await client.navigate('https://www.example.com', timeout=30)
        print(f"   ✅ 导航成功: {final_url}")
        
        # 获取页面内容
        print("\n3. 获取页面内容...")
        html = await client.get_page_content()
        print(f"   ✅ 获取成功: {len(html)} 字节")
        print(f"   页面标题: {html[:100]}...")
        
        # 执行脚本
        print("\n4. 执行 JavaScript...")
        title = await client.execute_script("document.title")
        print(f"   ✅ 脚本执行成功: {title}")
        
        # 截图
        print("\n5. 页面截图...")
        image_data = await client.take_screenshot(full_page=False)
        print(f"   ✅ 截图成功: {len(image_data)} 字节")
        
        print("\n✅ 基础操作测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()


async def test_element_operations():
    """测试元素操作"""
    print("\n" + "=" * 60)
    print("测试 2: 元素操作")
    print("=" * 60)
    
    client = BrowserHTTPClient(base_url='http://localhost:8000')
    
    try:
        # 创建会话并导航
        print("\n1. 创建会话并导航...")
        await client.create_session(headless=True)
        await client.navigate('https://www.example.com')
        print("   ✅ 页面加载完成")
        
        # 等待元素（测试一个不存在的元素，应该会超时）
        print("\n2. 测试等待元素（应该超时）...")
        try:
            await client.wait_for_element('nonexistent-element', timeout=2)
            print("   ⚠️  元素找到了（不应该）")
        except Exception as e:
            print(f"   ✅ 正确超时: {str(e)[:50]}...")
        
        # 等待存在的元素
        print("\n3. 等待存在的元素...")
        await client.wait_for_element('body', timeout=5)
        print("   ✅ body 元素找到")
        
        print("\n✅ 元素操作测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()


async def test_headers_and_cookies():
    """测试请求头和 Cookie"""
    print("\n" + "=" * 60)
    print("测试 3: 请求头和 Cookie")
    print("=" * 60)
    
    client = BrowserHTTPClient(base_url='http://localhost:8000')
    
    try:
        # 创建会话
        print("\n1. 创建会话...")
        await client.create_session(headless=True)
        print("   ✅ 会话创建成功")
        
        # 设置请求头
        print("\n2. 设置请求头...")
        await client.set_headers({
            'X-Custom-Header': 'test-value',
            'User-Agent': 'Test-Agent/1.0'
        })
        print("   ✅ 请求头设置成功")
        
        # 导航到页面（设置 Cookie 前需要先导航）
        print("\n3. 导航到页面...")
        await client.navigate('https://www.example.com')
        print("   ✅ 页面导航成功")
        
        # 设置 Cookie
        print("\n4. 设置 Cookie...")
        await client.set_cookies([{
            'name': 'test_cookie',
            'value': 'test_value',
            'domain': 'example.com'
        }])
        print("   ✅ Cookie 设置成功")
        
        # 获取 Cookie
        print("\n5. 获取 Cookie...")
        cookies = await client.get_cookies()
        print(f"   ✅ 获取到 {len(cookies)} 个 Cookie")
        
        print("\n✅ 请求头和 Cookie 测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()


async def test_network_interception():
    """测试网络拦截"""
    print("\n" + "=" * 60)
    print("测试 4: 网络拦截")
    print("=" * 60)
    
    client = BrowserHTTPClient(base_url='http://localhost:8000')
    
    try:
        # 创建会话并导航
        print("\n1. 创建会话并导航...")
        await client.create_session(headless=True)
        await client.navigate('https://www.example.com', timeout=30)
        print("   ✅ 页面加载完成")
        
        # 获取网络请求
        print("\n2. 获取网络请求...")
        requests = await client.get_network_requests()
        print(f"   ✅ 获取到 {len(requests)} 个网络请求")
        
        if requests:
            print("\n   前 3 个请求:")
            for i, req in enumerate(requests[:3], 1):
                print(f"   {i}. {req['method']} {req['url']}")
                if req.get('response'):
                    print(f"      状态码: {req['response'].get('status_code')}")
        
        # 使用 URL 模式过滤
        print("\n3. 使用 URL 模式过滤...")
        filtered = await client.get_network_requests(url_pattern=r'example')
        print(f"   ✅ 过滤后: {len(filtered)} 个请求")
        
        print("\n✅ 网络拦截测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()


async def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试 5: 错误处理")
    print("=" * 60)
    
    client = BrowserHTTPClient(base_url='http://localhost:8000')
    
    try:
        # 测试未创建会话时的操作
        print("\n1. 测试未创建会话时的操作...")
        try:
            await client.navigate('https://www.example.com')
            print("   ❌ 应该抛出错误")
            return False
        except RuntimeError as e:
            print(f"   ✅ 正确抛出错误: {str(e)[:50]}...")
        
        # 创建会话
        await client.create_session(headless=True)
        
        # 测试无效的会话 ID（通过关闭会话后操作）
        print("\n2. 测试关闭会话后的操作...")
        await client.close_session()
        try:
            await client.navigate('https://www.example.com')
            print("   ❌ 应该抛出错误")
            return False
        except Exception as e:
            print(f"   ✅ 正确抛出错误: {str(e)[:50]}...")
        
        print("\n✅ 错误处理测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Browser RPC HTTP API 测试")
    print("=" * 60)
    print("\n确保 HTTP 服务器正在运行: python http_server.py")
    print("或运行: ./scripts/start_http_server.sh\n")
    
    # 检查服务器是否运行
    import httpx
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get('http://localhost:8000/')
            if response.status_code != 200:
                print("❌ HTTP 服务器未运行或响应异常")
                sys.exit(1)
    except Exception as e:
        print(f"❌ 无法连接到 HTTP 服务器: {e}")
        print("请先启动服务器: python http_server.py")
        sys.exit(1)
    
    print("✅ HTTP 服务器连接正常\n")
    
    # 运行测试
    tests = [
        ("基础操作", test_basic_operations),
        ("元素操作", test_element_operations),
        ("请求头和 Cookie", test_headers_and_cookies),
        ("网络拦截", test_network_interception),
        ("错误处理", test_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 异常: {e}")
            results.append((name, False))
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

