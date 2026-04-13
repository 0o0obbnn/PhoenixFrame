"""增强API客户端测试"""
import pytest
from unittest.mock import Mock, patch
import time
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
def enhanced_api_client():
    """增强的API客户端实例"""
    return APIClient(
        base_url="https://api.example.com",
        max_retries=3,
        retry_delay=0.1,
        pool_connections=5,
        pool_maxsize=10
    )


def test_api_client_enhanced_initialization(enhanced_api_client):
    """测试增强API客户端初始化"""
    assert enhanced_api_client.base_url == "https://api.example.com"
    assert enhanced_api_client.max_retries == 3
    assert enhanced_api_client.retry_delay == 0.1
    
    # 检查会话适配器配置
    adapters = enhanced_api_client.session.adapters
    assert "http://" in adapters
    assert "https://" in adapters


@patch('src.phoenixframe.api.client.requests.Session.request')
def test_api_client_retry_mechanism_success(mock_request, enhanced_api_client, mock_response):
    """测试API客户端重试机制成功"""
    # 模拟前两次失败，第三次成功
    mock_request.side_effect = [
        Exception("Connection error"),
        Exception("Connection error"),
        mock_response
    ]
    
    response = enhanced_api_client.get('/users/1')
    
    assert isinstance(response, APIResponse)
    assert response.status_code == 200
    # 确认调用了3次（2次失败 + 1次成功）
    assert mock_request.call_count == 3


@patch('src.phoenixframe.api.client.requests.Session.request')
def test_api_client_retry_mechanism_failure(mock_request, enhanced_api_client):
    """测试API客户端重试机制失败"""
    # 模拟所有尝试都失败
    mock_request.side_effect = Exception("Connection error")
    
    with pytest.raises(Exception):
        enhanced_api_client.get('/users/1')
    
    # 确认调用了4次（1次初始 + 3次重试）
    assert mock_request.call_count == 4  # 1次初始尝试 + 3次重试


@patch('src.phoenixframe.api.client.requests.Session.request')
def test_api_client_connection_pooling(mock_request, enhanced_api_client, mock_response):
    """测试API客户端连接池"""
    mock_request.return_value = mock_response
    
    # 发送多个请求
    responses = []
    for i in range(3):
        response = enhanced_api_client.get(f'/users/{i}')
        responses.append(response)
    
    # 验证所有请求都成功发送
    assert len(responses) == 3
    assert all(isinstance(r, APIResponse) for r in responses)
    assert mock_request.call_count == 3
    
    # 验证请求参数
    for i, call_args in enumerate(mock_request.call_args_list):
        assert call_args[1]['url'] == f'https://api.example.com/users/{i}'


def test_api_client_custom_retry_settings():
    """测试自定义重试设置"""
    client = APIClient(
        base_url="https://api.example.com",
        max_retries=5,
        retry_delay=0.5
    )
    
    assert client.max_retries == 5
    assert client.retry_delay == 0.5


@patch('src.phoenixframe.api.client.requests.Session.request')
def test_api_client_backoff_retry_delay(mock_request, enhanced_api_client):
    """测试API客户端退避重试延迟"""
    mock_request.side_effect = Exception("Connection error")
    
    with pytest.raises(Exception):
        enhanced_api_client.get('/users/1')
    
    # 验证重试确实发生了
    assert mock_request.call_count == 4  # 1次初始 + 3次重试