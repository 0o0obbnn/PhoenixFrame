"""API响应测试"""
import pytest
from unittest.mock import Mock
import json
from src.phoenixframe.api.response import APIResponse


@pytest.fixture
def mock_response():
    """模拟HTTP响应"""
    response = Mock()
    response.status_code = 200
    response.headers = {
        'Content-Type': 'application/json',
        'Server': 'nginx'
    }
    response.text = '{"id": 1, "name": "test", "email": "test@example.com"}'
    response.json.return_value = {"id": 1, "name": "test", "email": "test@example.com"}
    response.content = b'{"id": 1, "name": "test", "email": "test@example.com"}'
    
    # 创建elapsed mock
    elapsed_mock = Mock()
    elapsed_mock.total_seconds.return_value = 0.5
    response.elapsed = elapsed_mock
    
    return response


@pytest.fixture
def api_response(mock_response):
    """API响应实例"""
    return APIResponse(mock_response)


def test_api_response_properties(api_response):
    """测试API响应属性"""
    assert api_response.status_code == 200
    assert api_response.headers['Content-Type'] == 'application/json'
    assert api_response.text == '{"id": 1, "name": "test", "email": "test@example.com"}'
    assert api_response.json_data == {"id": 1, "name": "test", "email": "test@example.com"}


def test_api_response_assert_status_code_success(api_response):
    """测试状态码断言成功"""
    result = api_response.assert_status_code(200)
    assert result is api_response  # 链式调用返回自身


def test_api_response_assert_status_code_failure(api_response):
    """测试状态码断言失败"""
    with pytest.raises(AssertionError, match="Expected status code 404, got 200"):
        api_response.assert_status_code(404)


def test_api_response_assert_header_success(api_response):
    """测试响应头断言成功"""
    result = api_response.assert_header('Content-Type', 'application/json')
    assert result is api_response


def test_api_response_assert_header_failure(api_response):
    """测试响应头断言失败"""
    with pytest.raises(AssertionError, match="Expected header 'Content-Type' to be 'text/plain', got 'application/json'"):
        api_response.assert_header('Content-Type', 'text/plain')


def test_api_response_assert_header_not_found(api_response):
    """测试响应头不存在的情况"""
    with pytest.raises(AssertionError, match="Expected header 'X-Custom-Header' to be 'value', got 'None'"):
        api_response.assert_header('X-Custom-Header', 'value')


def test_api_response_assert_json_contains_success(api_response):
    """测试JSON包含键断言成功"""
    result = api_response.assert_json_contains('name')
    assert result is api_response
    
    # 测试带值的断言
    result = api_response.assert_json_contains('name', 'test')
    assert result is api_response


def test_api_response_assert_json_contains_key_failure(api_response):
    """测试JSON包含键断言失败"""
    with pytest.raises(AssertionError, match="Key 'nonexistent' not found in JSON response"):
        api_response.assert_json_contains('nonexistent')


def test_api_response_assert_json_contains_value_failure(api_response):
    """测试JSON包含键值断言失败"""
    with pytest.raises(AssertionError, match="Key 'name' expected 'wrong', got 'test'"):
        api_response.assert_json_contains('name', 'wrong')


def test_api_response_assert_json_has_keys_success(api_response):
    """测试JSON包含所有键断言成功"""
    result = api_response.assert_json_has_keys('id', 'name', 'email')
    assert result is api_response


def test_api_response_assert_json_has_keys_failure(api_response):
    """测试JSON包含所有键断言失败"""
    with pytest.raises(AssertionError, match=r"Missing keys in JSON response: \['nonexistent1', 'nonexistent2'\]"):
        api_response.assert_json_has_keys('id', 'nonexistent1', 'nonexistent2')


def test_api_response_assert_text_contains_success(api_response):
    """测试文本包含断言成功"""
    result = api_response.assert_text_contains('test@example.com')
    assert result is api_response


def test_api_response_assert_text_contains_failure(api_response):
    """测试文本包含断言失败"""
    with pytest.raises(AssertionError, match="Text 'nonexistent' not found in response"):
        api_response.assert_text_contains('nonexistent')


def test_api_response_assert_response_time_less_than_success(api_response):
    """测试响应时间断言成功"""
    result = api_response.assert_response_time_less_than(1.0)
    assert result is api_response


def test_api_response_assert_response_time_less_than_failure(api_response):
    """测试响应时间断言失败"""
    with pytest.raises(AssertionError, match="Response time 0.5s exceeds maximum 0.1s"):
        api_response.assert_response_time_less_than(0.1)


def test_api_response_get_json_value(api_response):
    """测试获取JSON值"""
    # 由于我们没有安装jsonpath_ng，这部分测试会引发ImportError
    try:
        import jsonpath_ng
        value = api_response.get_json_value('$.name')
        assert value == 'test'
    except ImportError:
        with pytest.raises(ImportError, match="jsonpath_ng is required for JSONPath operations"):
            api_response.get_json_value('$.name')


def test_api_response_chained_assertions(api_response):
    """测试链式断言"""
    result = (api_response
              .assert_status_code(200)
              .assert_header('Content-Type', 'application/json')
              .assert_json_contains('name', 'test')
              .assert_text_contains('test@example.com')
              .assert_response_time_less_than(1.0))
    
    assert result is api_response


def test_api_response_json_decode_error():
    """测试JSON解码错误"""
    response = Mock()
    response.status_code = 200
    response.text = 'not a json'
    response.json.side_effect = json.JSONDecodeError("Expecting value", "not a json", 0)
    
    api_response = APIResponse(response)
    
    with pytest.raises(ValueError, match="Response is not valid JSON"):
        _ = api_response.json_data