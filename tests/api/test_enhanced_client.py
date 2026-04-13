"""增强 API 客户端测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from phoenixframe.api.enhanced_client import EnhancedAPIClient, APIResponse


class TestEnhancedAPIClient:
    """增强 API 客户端测试"""
    
    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        return EnhancedAPIClient("https://api.example.com")
    
    def test_client_initialization(self, client):
        """测试客户端初始化"""
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.enable_idempotency is True
    
    def test_request_with_retry(self, client):
        """测试请求重试机制"""
        with patch.object(client.session, 'request') as mock_request:
            # 模拟第一次失败，第二次成功
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_response.content = b'{"data": "test"}'
            
            mock_request.side_effect = [Exception("Network error"), mock_response]
            
            response = client.request("GET", "/test")
            
            assert mock_request.call_count == 2
            assert response.status_code == 200
    
    def test_idempotency_key_generation(self, client):
        """测试幂等性键生成"""
        with patch.object(client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_response.content = b'{"data": "test"}'
            mock_request.return_value = mock_response
            
            client.request("POST", "/test", json={"data": "test"})
            
            # 检查是否添加了 Idempotency-Key 头
            call_args = mock_request.call_args
            headers = call_args[1].get('headers', {})
            assert 'Idempotency-Key' in headers
            assert headers['Idempotency-Key'] is not None
    
    def test_request_id_generation(self, client):
        """测试请求 ID 生成"""
        with patch.object(client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_response.content = b'{"data": "test"}'
            mock_request.return_value = mock_response
            
            client.request("GET", "/test")
            
            # 检查是否添加了 X-Request-ID 头
            call_args = mock_request.call_args
            headers = call_args[1].get('headers', {})
            assert 'X-Request-ID' in headers
            assert headers['X-Request-ID'] is not None
    
    def test_http_methods(self, client):
        """测试 HTTP 方法"""
        with patch.object(client, 'request') as mock_request:
            mock_response = Mock()
            mock_request.return_value = mock_response
            
            # 测试各种 HTTP 方法
            client.get("/test")
            client.post("/test", json={"data": "test"})
            client.put("/test", json={"data": "test"})
            client.patch("/test", json={"data": "test"})
            client.delete("/test")
            client.head("/test")
            client.options("/test")
            
            assert mock_request.call_count == 7
    
    def test_set_auth(self, client):
        """测试设置认证"""
        auth = ("username", "password")
        client.set_auth(auth)
        assert client.session.auth == auth
    
    def test_set_headers(self, client):
        """测试设置请求头"""
        headers = {"Authorization": "Bearer token"}
        client.set_headers(headers)
        assert client.session.headers["Authorization"] == "Bearer token"
    
    def test_set_cookies(self, client):
        """测试设置 Cookie"""
        cookies = {"session_id": "abc123"}
        client.set_cookies(cookies)
        assert client.session.cookies["session_id"] == "abc123"
    
    def test_set_proxies(self, client):
        """测试设置代理"""
        proxies = {"http": "http://proxy:8080"}
        client.set_proxies(proxies)
        assert client.session.proxies["http"] == "http://proxy:8080"
    
    def test_get_stats(self, client):
        """测试获取统计信息"""
        # 模拟一些请求
        client._request_count = 10
        client._success_count = 8
        client._error_count = 2
        
        stats = client.get_stats()
        
        assert stats["total_requests"] == 10
        assert stats["successful_requests"] == 8
        assert stats["failed_requests"] == 2
        assert stats["success_rate"] == 0.8
    
    def test_reset_stats(self, client):
        """测试重置统计信息"""
        client._request_count = 10
        client._success_count = 8
        client._error_count = 2
        
        client.reset_stats()
        
        assert client._request_count == 0
        assert client._success_count == 0
        assert client._error_count == 0
    
    def test_context_manager(self, client):
        """测试上下文管理器"""
        with patch.object(client, 'close') as mock_close:
            with client:
                pass
            mock_close.assert_called_once()


class TestAPIResponse:
    """API 响应包装器测试"""
    
    @pytest.fixture
    def response(self):
        """创建响应对象"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.json.return_value = {"data": "test", "user": {"name": "John"}}
        mock_response.text = '{"data": "test"}'
        mock_response.content = b'{"data": "test"}'
        
        return APIResponse(mock_response)
    
    def test_status_code_assertion(self, response):
        """测试状态码断言"""
        result = response.status_code(200)
        assert result is response  # 支持链式调用
        assert "status_code == 200" in response.get_assertions()
    
    def test_status_code_in_assertion(self, response):
        """测试状态码范围断言"""
        result = response.status_code_in([200, 201])
        assert result is response
        assert "status_code in [200, 201]" in response.get_assertions()
    
    def test_header_assertion(self, response):
        """测试响应头断言"""
        result = response.header("Content-Type", "application/json")
        assert result is response
        assert "header Content-Type == application/json" in response.get_assertions()
    
    def test_header_assertion_list(self, response):
        """测试响应头列表断言"""
        result = response.header("Content-Type", ["application/json", "text/json"])
        assert result is response
        assert "header Content-Type == ['application/json', 'text/json']" in response.get_assertions()
    
    def test_json_path_assertion(self, response):
        """测试 JSON 路径断言"""
        result = response.json_path("data", "test")
        assert result is response
        assert "json_path data == test" in response.get_assertions()
    
    def test_json_path_nested_assertion(self, response):
        """测试嵌套 JSON 路径断言"""
        result = response.json_path("user.name", "John")
        assert result is response
        assert "json_path user.name == John" in response.get_assertions()
    
    def test_response_time_assertion(self, response):
        """测试响应时间断言"""
        result = response.response_time(1.0)
        assert result is response
        assert "response_time <= 1.0" in response.get_assertions()
    
    def test_content_type_assertion(self, response):
        """测试内容类型断言"""
        result = response.content_type("application/json")
        assert result is response
        assert "content_type contains 'application/json'" in response.get_assertions()
    
    def test_json_method(self, response):
        """测试 JSON 方法"""
        data = response.json()
        assert data == {"data": "test", "user": {"name": "John"}}
    
    def test_text_method(self, response):
        """测试文本方法"""
        text = response.text()
        assert text == '{"data": "test"}'
    
    def test_content_method(self, response):
        """测试内容方法"""
        content = response.content()
        assert content == b'{"data": "test"}'
    
    def test_get_assertions(self, response):
        """测试获取断言列表"""
        response.status_code(200).header("Content-Type", "application/json")
        
        assertions = response.get_assertions()
        assert len(assertions) == 2
        assert "status_code == 200" in assertions
        assert "header Content-Type == application/json" in assertions
    
    def test_str_representation(self, response):
        """测试字符串表示"""
        str_repr = str(response)
        assert "APIResponse" in str_repr
        assert "status=200" in str_repr
    
    def test_repr_representation(self, response):
        """测试详细字符串表示"""
        repr_str = repr(response)
        assert "APIResponse" in repr_str
        assert "status=200" in repr_str
        assert "assertions=0" in repr_str
    
    def test_assertion_failure(self, response):
        """测试断言失败"""
        with pytest.raises(AssertionError):
            response.status_code(404)
    
    def test_json_schema_assertion(self, response):
        """测试 JSON Schema 断言"""
        schema = {
            "type": "object",
            "properties": {
                "data": {"type": "string"}
            },
            "required": ["data"]
        }
        
        with patch('phoenixframe.api.enhanced_client.validate') as mock_validate:
            result = response.json_schema(schema)
            assert result is response
            mock_validate.assert_called_once()
            assert "json_schema validation passed" in response.get_assertions()
    
    def test_json_schema_import_error(self, response):
        """测试 JSON Schema 导入错误"""
        schema = {"type": "object"}
        
        with patch('phoenixframe.api.enhanced_client.validate', side_effect=ImportError):
            with pytest.raises(ImportError, match="jsonschema is required"):
                response.json_schema(schema)
