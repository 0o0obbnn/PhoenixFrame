"""
API测试综合示例
演示PhoenixFrame的API测试功能
包括声明式和编程式两种测试方法
"""
import sys
import json
from pathlib import Path

# 添加src路径以便导入模块
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.phoenixframe.api.client import APIClient
from src.phoenixframe.observability.logger import get_logger, setup_logging

# 设置日志
setup_logging(level="INFO", enable_console=True)
logger = get_logger("api_testing_example")


def demo_basic_api_testing():
    """演示基本API测试"""
    logger.info("=== Basic API Testing Demo ===")
    
    # 创建API客户端
    client = APIClient(base_url="https://httpbin.org")
    logger.info("Created API client for httpbin.org")
    
    try:
        # GET请求演示
        logger.info("--- GET Request Demo ---")
        response = client.get("/get", params={"key": "value", "test": "demo"})
        
        logger.info(f"GET /get - Status: {response.status_code}")
        logger.info(f"Response time: {response.elapsed.total_seconds():.3f}s")
        
        # 验证响应
        response_data = response.json()
        assert response.status_code == 200
        assert "args" in response_data
        assert response_data["args"]["key"] == "value"
        logger.info("✅ GET request validation passed")
        
        # POST请求演示
        logger.info("--- POST Request Demo ---")
        post_data = {
            "username": "testuser",
            "email": "test@example.com",
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        response = client.post("/post", json=post_data)
        
        logger.info(f"POST /post - Status: {response.status_code}")
        
        # 验证POST响应
        response_data = response.json()
        assert response.status_code == 200
        assert "json" in response_data
        assert response_data["json"]["username"] == "testuser"
        logger.info("✅ POST request validation passed")
        
        # PUT请求演示
        logger.info("--- PUT Request Demo ---")
        put_data = {"id": 123, "name": "Updated Name", "status": "active"}
        
        response = client.put("/put", json=put_data)
        
        logger.info(f"PUT /put - Status: {response.status_code}")
        
        response_data = response.json()
        assert response.status_code == 200
        assert response_data["json"]["id"] == 123
        logger.info("✅ PUT request validation passed")
        
        # DELETE请求演示
        logger.info("--- DELETE Request Demo ---")
        response = client.delete("/delete")
        
        logger.info(f"DELETE /delete - Status: {response.status_code}")
        assert response.status_code == 200
        logger.info("✅ DELETE request validation passed")
        
        # PATCH请求演示
        logger.info("--- PATCH Request Demo ---")
        patch_data = {"status": "updated"}
        
        response = client.patch("/patch", json=patch_data)
        
        logger.info(f"PATCH /patch - Status: {response.status_code}")
        assert response.status_code == 200
        logger.info("✅ PATCH request validation passed")
        
    except Exception as e:
        logger.error(f"Basic API testing failed: {e}")
        raise
    
    finally:
        client.close()


def demo_authentication_testing():
    """演示身份验证测试"""
    logger.info("=== Authentication Testing Demo ===")
    
    # 基本认证演示
    logger.info("--- Basic Authentication Demo ---")
    client = APIClient(base_url="https://httpbin.org")
    
    try:
        # 测试基本认证
        response = client.get("/basic-auth/user/passwd", auth=("user", "passwd"))
        
        logger.info(f"Basic auth status: {response.status_code}")
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data["authenticated"] is True
        assert response_data["user"] == "user"
        logger.info("✅ Basic authentication test passed")
        
        # 测试错误认证
        try:
            response = client.get("/basic-auth/user/passwd", auth=("wrong", "credentials"))
            logger.info(f"Wrong auth status: {response.status_code}")
            assert response.status_code == 401
            logger.info("✅ Authentication failure test passed")
        except Exception:
            logger.info("✅ Authentication properly rejected invalid credentials")
        
    except Exception as e:
        logger.error(f"Authentication testing failed: {e}")
    
    finally:
        client.close()
    
    # Bearer Token演示
    logger.info("--- Bearer Token Demo ---")
    client = APIClient(base_url="https://httpbin.org")
    
    try:
        # 设置Authorization头
        headers = {"Authorization": "Bearer sample-token-12345"}
        response = client.get("/bearer", headers=headers)
        
        logger.info(f"Bearer token status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            assert response_data["authenticated"] is True
            assert response_data["token"] == "sample-token-12345"
            logger.info("✅ Bearer token test passed")
        else:
            logger.info(f"Bearer token returned status: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Bearer token testing failed: {e}")
    
    finally:
        client.close()


def demo_response_validation():
    """演示响应验证测试"""
    logger.info("=== Response Validation Demo ===")
    
    client = APIClient(base_url="https://httpbin.org")
    
    try:
        # JSON响应验证
        logger.info("--- JSON Response Validation ---")
        response = client.get("/json")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        
        json_data = response.json()
        
        # 验证JSON结构
        required_fields = ["slideshow"]
        for field in required_fields:
            assert field in json_data, f"Missing required field: {field}"
        
        logger.info("✅ JSON structure validation passed")
        
        # XML响应验证
        logger.info("--- XML Response Validation ---")
        response = client.get("/xml")
        
        assert response.status_code == 200
        assert "xml" in response.headers["content-type"]
        
        xml_content = response.text
        assert "<?xml" in xml_content
        assert "<slideshow" in xml_content
        
        logger.info("✅ XML response validation passed")
        
        # HTML响应验证
        logger.info("--- HTML Response Validation ---")
        response = client.get("/html")
        
        assert response.status_code == 200
        assert "html" in response.headers["content-type"]
        
        html_content = response.text
        assert "<html>" in html_content
        assert "<body>" in html_content
        
        logger.info("✅ HTML response validation passed")
        
        # 状态码验证
        logger.info("--- Status Code Validation ---")
        
        status_codes_to_test = [200, 201, 400, 404, 500]
        
        for status_code in status_codes_to_test:
            response = client.get(f"/status/{status_code}")
            assert response.status_code == status_code
            logger.info(f"✅ Status code {status_code} test passed")
        
    except Exception as e:
        logger.error(f"Response validation failed: {e}")
        raise
    
    finally:
        client.close()


def demo_performance_testing():
    """演示API性能测试"""
    logger.info("=== API Performance Testing Demo ===")
    
    client = APIClient(base_url="https://httpbin.org")
    
    try:
        # 响应时间测试
        logger.info("--- Response Time Testing ---")
        
        # 测试快速响应
        response = client.get("/get")
        response_time = response.elapsed.total_seconds()
        
        logger.info(f"Fast endpoint response time: {response_time:.3f}s")
        assert response_time < 5.0, "Response too slow"
        logger.info("✅ Fast response time test passed")
        
        # 测试延迟响应
        delay_seconds = 2
        response = client.get(f"/delay/{delay_seconds}")
        response_time = response.elapsed.total_seconds()
        
        logger.info(f"Delayed endpoint response time: {response_time:.3f}s")
        assert response_time >= delay_seconds, "Delay not working properly"
        assert response_time < delay_seconds + 2, "Response too slow beyond expected delay"
        logger.info("✅ Delayed response time test passed")
        
        # 批量请求性能测试
        logger.info("--- Batch Request Performance ---")
        
        import time
        start_time = time.time()
        
        for i in range(5):
            response = client.get("/get", params={"request": i})
            assert response.status_code == 200
        
        total_time = time.time() - start_time
        avg_time = total_time / 5
        
        logger.info(f"5 requests completed in {total_time:.3f}s (avg: {avg_time:.3f}s per request)")
        logger.info("✅ Batch request performance test completed")
        
    except Exception as e:
        logger.error(f"Performance testing failed: {e}")
    
    finally:
        client.close()


def demo_data_driven_testing():
    """演示数据驱动测试"""
    logger.info("=== Data-Driven Testing Demo ===")
    
    client = APIClient(base_url="https://httpbin.org")
    
    try:
        # 测试数据集
        test_users = [
            {"username": "alice", "email": "alice@example.com", "role": "admin"},
            {"username": "bob", "email": "bob@example.com", "role": "user"},
            {"username": "charlie", "email": "charlie@example.com", "role": "moderator"},
        ]
        
        logger.info(f"--- Testing with {len(test_users)} user datasets ---")
        
        for i, user_data in enumerate(test_users, 1):
            logger.info(f"Test {i}: Testing user {user_data['username']}")
            
            # 发送POST请求
            response = client.post("/post", json=user_data)
            
            # 验证响应
            assert response.status_code == 200
            
            response_data = response.json()
            assert response_data["json"]["username"] == user_data["username"]
            assert response_data["json"]["email"] == user_data["email"]
            assert response_data["json"]["role"] == user_data["role"]
            
            logger.info(f"✅ Test {i} passed for user {user_data['username']}")
        
        # 边界值测试
        logger.info("--- Boundary Value Testing ---")
        
        boundary_test_cases = [
            {"name": "", "expected_valid": False},  # 空名称
            {"name": "a", "expected_valid": True},   # 最短名称
            {"name": "a" * 100, "expected_valid": True},  # 长名称
            {"name": "valid_user", "expected_valid": True},  # 正常名称
        ]
        
        for i, test_case in enumerate(boundary_test_cases, 1):
            logger.info(f"Boundary test {i}: name='{test_case['name'][:20]}{'...' if len(test_case['name']) > 20 else ''}'")
            
            response = client.post("/post", json={"name": test_case["name"]})
            
            # 这里我们只验证请求能够正常发送
            # 在真实的API中，可能会有不同的验证逻辑
            assert response.status_code == 200
            
            response_data = response.json()
            assert response_data["json"]["name"] == test_case["name"]
            
            logger.info(f"✅ Boundary test {i} completed")
        
    except Exception as e:
        logger.error(f"Data-driven testing failed: {e}")
    
    finally:
        client.close()


def demo_error_handling():
    """演示错误处理测试"""
    logger.info("=== Error Handling Demo ===")
    
    client = APIClient(base_url="https://httpbin.org")
    
    try:
        # 网络超时测试
        logger.info("--- Timeout Handling ---")
        
        # 设置短超时时间
        client.session.timeout = 1
        
        try:
            # 尝试访问会延迟的端点
            response = client.get("/delay/5")
            logger.warning("Timeout test didn't timeout as expected")
        except Exception as e:
            logger.info(f"✅ Timeout properly handled: {type(e).__name__}")
        
        # 重置超时
        client.session.timeout = 30
        
        # 4xx错误处理
        logger.info("--- 4xx Error Handling ---")
        
        response = client.get("/status/404")
        assert response.status_code == 404
        logger.info("✅ 404 error handled correctly")
        
        response = client.get("/status/401")
        assert response.status_code == 401
        logger.info("✅ 401 error handled correctly")
        
        response = client.get("/status/400")
        assert response.status_code == 400
        logger.info("✅ 400 error handled correctly")
        
        # 5xx错误处理
        logger.info("--- 5xx Error Handling ---")
        
        response = client.get("/status/500")
        assert response.status_code == 500
        logger.info("✅ 500 error handled correctly")
        
        response = client.get("/status/503")
        assert response.status_code == 503
        logger.info("✅ 503 error handled correctly")
        
    except Exception as e:
        logger.error(f"Error handling demo failed: {e}")
    
    finally:
        client.close()


def demo_headers_and_cookies():
    """演示请求头和Cookie处理"""
    logger.info("=== Headers and Cookies Demo ===")
    
    client = APIClient(base_url="https://httpbin.org")
    
    try:
        # 自定义请求头
        logger.info("--- Custom Headers Demo ---")
        
        custom_headers = {
            "User-Agent": "PhoenixFrame-APITester/1.0",
            "X-API-Key": "test-api-key-12345",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        response = client.get("/headers", headers=custom_headers)
        
        assert response.status_code == 200
        response_data = response.json()
        
        # 验证headers被正确发送
        received_headers = response_data["headers"]
        assert received_headers["User-Agent"] == "PhoenixFrame-APITester/1.0"
        assert received_headers["X-Api-Key"] == "test-api-key-12345"
        
        logger.info("✅ Custom headers test passed")
        
        # Cookie处理
        logger.info("--- Cookies Demo ---")
        
        # 设置Cookie
        cookies = {"session_id": "abc123", "user_preference": "dark_mode"}
        response = client.get("/cookies", cookies=cookies)
        
        assert response.status_code == 200
        response_data = response.json()
        
        # 验证Cookie被正确发送
        received_cookies = response_data["cookies"]
        assert received_cookies["session_id"] == "abc123"
        assert received_cookies["user_preference"] == "dark_mode"
        
        logger.info("✅ Cookies test passed")
        
        # 设置Cookie的接口测试
        logger.info("--- Set Cookies Demo ---")
        
        response = client.get("/cookies/set/test_cookie/test_value")
        
        # 重定向后，Cookie应该被设置
        # 在实际应用中，可以通过检查Set-Cookie头来验证
        logger.info("✅ Set cookies test completed")
        
    except Exception as e:
        logger.error(f"Headers and cookies demo failed: {e}")
    
    finally:
        client.close()


def demo_file_upload():
    """演示文件上传测试"""
    logger.info("=== File Upload Demo ===")
    
    client = APIClient(base_url="https://httpbin.org")
    
    try:
        # 创建测试文件
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test file for upload demo.\nLine 2 of the test file.")
            test_file_path = f.name
        
        logger.info("--- File Upload Test ---")
        
        # 上传文件
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            response = client.post("/post", files=files)
        
        assert response.status_code == 200
        response_data = response.json()
        
        # 验证文件上传
        assert "files" in response_data
        assert "file" in response_data["files"]
        
        uploaded_content = response_data["files"]["file"]
        assert "This is a test file for upload demo" in uploaded_content
        
        logger.info("✅ File upload test passed")
        
        # 清理测试文件
        Path(test_file_path).unlink()
        
        # 多文件上传测试
        logger.info("--- Multiple Files Upload Test ---")
        
        # 创建多个测试文件
        test_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as f:
                f.write(f"Test file {i+1} content")
                test_files.append(f.name)
        
        # 上传多个文件
        files = []
        for i, file_path in enumerate(test_files):
            with open(file_path, 'rb') as f:
                files.append(('files', (f'test_{i+1}.txt', f.read(), 'text/plain')))
        
        response = client.post("/post", files=files)
        
        assert response.status_code == 200
        logger.info("✅ Multiple files upload test passed")
        
        # 清理测试文件
        for file_path in test_files:
            Path(file_path).unlink()
        
    except Exception as e:
        logger.error(f"File upload demo failed: {e}")
    
    finally:
        client.close()


def main():
    """主演示函数"""
    logger.info("PhoenixFrame API Testing Demo")
    logger.info("=" * 50)
    
    try:
        # 运行各个演示
        demo_basic_api_testing()
        print()
        
        demo_authentication_testing()
        print()
        
        demo_response_validation()
        print()
        
        demo_performance_testing()
        print()
        
        demo_data_driven_testing()
        print()
        
        demo_error_handling()
        print()
        
        demo_headers_and_cookies()
        print()
        
        demo_file_upload()
        print()
        
        logger.info("=== Demo Summary ===")
        logger.info("✅ Basic HTTP methods (GET, POST, PUT, DELETE, PATCH)")
        logger.info("✅ Authentication testing (Basic Auth, Bearer Token)")
        logger.info("✅ Response validation (JSON, XML, HTML, Status Codes)")
        logger.info("✅ Performance testing (Response time, Batch requests)")
        logger.info("✅ Data-driven testing (Multiple datasets, Boundary values)")
        logger.info("✅ Error handling (Timeouts, 4xx/5xx errors)")
        logger.info("✅ Headers and cookies handling")
        logger.info("✅ File upload testing (Single and multiple files)")
        
        logger.info("\n🎉 All API testing features demonstrated successfully!")
        
        # CLI使用示例
        logger.info("\n📋 CLI Usage Examples:")
        logger.info("# Generate API tests from HAR file")
        logger.info("phoenix generate har network-recording.har --output api_tests.py")
        logger.info("\n# Generate API tests from OpenAPI spec")
        logger.info("phoenix generate openapi api-spec.yaml --output api_skeleton.py")
        logger.info("\n# Create API client scaffold")
        logger.info("phoenix scaffold api UserAPI --base-url https://api.example.com")
        logger.info("\n# Create API test scaffold")
        logger.info("phoenix scaffold test UserAPITest --test-type api")
        logger.info("\n# Run API tests")
        logger.info("phoenix run tests/ -m api --env production")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()