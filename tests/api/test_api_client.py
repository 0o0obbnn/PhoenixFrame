"""API客户端测试"""
import pytest
from unittest.mock import Mock, patch
from src.phoenixframe.api.client import APIClient
from src.phoenixframe.api.response import APIResponse


@pytest.fixture
def mock_response():
    """模拟HTTP响应"""
    response = Mock()
    response.status_code = 200
    response.headers = {'Content-Type': 'application/json'}
    response.text = '{"message": "success"}'
    response.json.return_value = {"message": "success"}
    response.content = b'{"message": "success"}'

    # 创建elapsed mock
    elapsed_mock = Mock()
    elapsed_mock.total_seconds.return_value = 0.5
    response.elapsed = elapsed_mock

    return response


@pytest.fixture
def api_client():
    """API客户端实例"""
    return APIClient(base_url="https://api.example.com")


def test_api_client_initialization(api_client):
    """测试API客户端初始化"""
    assert api_client.base_url == "https://api.example.com"
    assert 'PhoenixFrame' in api_client.session.headers['User-Agent']
    assert api_client.session.headers['Accept'] == 'application/json'


@patch('src.phoenixframe.api.client.requests.Session.request')
def test_api_client_get_request(mock_request, api_client, mock_response):
    """测试GET请求"""
    mock_request.return_value = mock_response
    
    response = api_client.get('/users/1')
    
    assert isinstance(response, APIResponse)
    assert response.status_code == 200
    mock_request.assert_called_once()
    
    # 验证请求参数
    call_args = mock_request.call_args
    assert call_args[1]['method'] == 'GET'
    assert call_args[1]['url'] == 'https://api.example.com/users/1'


@patch('src.phoenixframe.api.client.requests.Session.request')
def test_api_client_post_request(mock_request, api_client, mock_response):
    """测试POST请求"""
    mock_request.return_value = mock_response
    
    test_data = {"name": "John", "email": "john@example.com"}
    response = api_client.post('/users', json=test_data)
    
    assert isinstance(response, APIResponse)
    assert response.status_code == 200
    mock_request.assert_called_once()
    
    # 验证请求参数
    call_args = mock_request.call_args
    assert call_args[1]['method'] == 'POST'
    assert call_args[1]['json'] == test_data


@patch('src.phoenixframe.api.client.requests.Session.request')
def test_api_client_with_headers(mock_request, api_client, mock_response):
    """测试带自定义头的请求"""
    mock_request.return_value = mock_response
    
    custom_headers = {"Authorization": "Bearer token123"}
    response = api_client.get('/protected', headers=custom_headers)
    
    assert response.status_code == 200
    
    # 验证请求头包含自定义头和追踪ID
    call_args = mock_request.call_args
    headers = call_args[1]['headers']
    assert 'Authorization' in headers
    assert 'X-Trace-ID' in headers


def test_api_client_url_preparation(api_client):
    """测试URL准备逻辑"""
    # 测试相对路径
    url = api_client._prepare_url('/users')
    assert url == 'https://api.example.com/users'
    
    # 测试绝对路径
    url = api_client._prepare_url('https://other.example.com/api')
    assert url == 'https://other.example.com/api'
    
    # 测试路径前缀处理
    url = api_client._prepare_url('users')
    assert url == 'https://api.example.com/users'


def test_api_client_auth_strategy():
    """测试认证策略"""
    mock_auth = Mock()
    mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer test-token"}
    
    client = APIClient(base_url="https://api.example.com", auth_strategy=mock_auth)
    headers = client._prepare_headers()
    
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test-token"
    mock_auth.get_auth_headers.assert_called_once()


@patch('src.phoenixframe.api.client.requests.Session.request')
def test_api_client_all_http_methods(mock_request, api_client, mock_response):
    """测试所有HTTP方法"""
    mock_request.return_value = mock_response
    
    # 测试所有方法
    methods_to_test = [
        ('get', '/users'),
        ('post', '/users', {'json': {'name': 'test'}}),
        ('put', '/users/1', {'json': {'name': 'updated'}}),
        ('patch', '/users/1', {'json': {'name': 'patched'}}),
        ('delete', '/users/1')
    ]
    
    for method_data in methods_to_test:
        method = method_data[0]
        endpoint = method_data[1]
        kwargs = method_data[2] if len(method_data) > 2 else {}
        
        response = getattr(api_client, method)(endpoint, **kwargs)
        assert isinstance(response, APIResponse)
        assert response.status_code == 200


def test_api_client_close(api_client):
    """测试客户端关闭"""
    with patch.object(api_client.session, 'close') as mock_close:
        api_client.close()
        mock_close.assert_called_once()
