"""API响应封装类，支持链式断言"""
import json
from typing import Any, Dict, Optional
from requests import Response

try:
    import jsonpath_ng
    HAS_JSONPATH = True
except ImportError:
    HAS_JSONPATH = False


class APIResponse:
    """API响应封装类，提供链式断言功能"""
    
    def __init__(self, response: Response):
        self.response = response
        self._json_data: Optional[Dict[str, Any]] = None
    
    @property
    def status_code(self) -> int:
        """获取状态码"""
        return self.response.status_code
    
    @property
    def headers(self) -> Dict[str, str]:
        """获取响应头"""
        return dict(self.response.headers)
    
    @property
    def text(self) -> str:
        """获取响应文本"""
        return self.response.text
    
    @property
    def json_data(self) -> Dict[str, Any]:
        """获取JSON数据"""
        if self._json_data is None:
            try:
                self._json_data = self.response.json()
            except json.JSONDecodeError:
                raise ValueError("Response is not valid JSON")
        return self._json_data
    
    def assert_status_code(self, expected_code: int) -> 'APIResponse':
        """断言状态码"""
        assert self.status_code == expected_code, \
            f"Expected status code {expected_code}, got {self.status_code}"
        return self
    
    def assert_header(self, name: str, expected_value: str) -> 'APIResponse':
        """断言响应头"""
        actual_value = self.headers.get(name)
        assert actual_value == expected_value, \
            f"Expected header '{name}' to be '{expected_value}', got '{actual_value}'"
        return self
    
    def assert_json_path(self, path: str, expected_value: Any) -> 'APIResponse':
        """使用JSONPath断言JSON数据"""
        if not HAS_JSONPATH:
            raise ImportError("jsonpath_ng is required for JSONPath assertions. Install with: pip install jsonpath-ng")

        jsonpath_expr = jsonpath_ng.parse(path)
        matches = jsonpath_expr.find(self.json_data)

        if not matches:
            raise AssertionError(f"JSONPath '{path}' not found in response")

        actual_value = matches[0].value
        assert actual_value == expected_value, \
            f"JSONPath '{path}' expected '{expected_value}', got '{actual_value}'"
        return self
    
    def assert_json_contains(self, key: str, expected_value: Any = None) -> 'APIResponse':
        """断言JSON包含指定键"""
        assert key in self.json_data, f"Key '{key}' not found in JSON response"
        
        if expected_value is not None:
            actual_value = self.json_data[key]
            assert actual_value == expected_value, \
                f"Key '{key}' expected '{expected_value}', got '{actual_value}'"
        return self
    
    def assert_json_has_keys(self, *keys: str) -> 'APIResponse':
        """断言JSON包含所有指定键"""
        missing_keys = [key for key in keys if key not in self.json_data]
        assert not missing_keys, f"Missing keys in JSON response: {missing_keys}"
        return self
    
    def assert_text_contains(self, text: str) -> 'APIResponse':
        """断言响应文本包含指定内容"""
        assert text in self.text, f"Text '{text}' not found in response"
        return self
    
    def assert_response_time_less_than(self, max_seconds: float) -> 'APIResponse':
        """断言响应时间小于指定值"""
        response_time = self.response.elapsed.total_seconds()
        assert response_time < max_seconds, \
            f"Response time {response_time}s exceeds maximum {max_seconds}s"
        return self
    
    def get_json_value(self, path: str) -> Any:
        """获取JSONPath指定的值"""
        if not HAS_JSONPATH:
            raise ImportError("jsonpath_ng is required for JSONPath operations. Install with: pip install jsonpath-ng")

        jsonpath_expr = jsonpath_ng.parse(path)
        matches = jsonpath_expr.find(self.json_data)

        if not matches:
            raise ValueError(f"JSONPath '{path}' not found in response")

        return matches[0].value
