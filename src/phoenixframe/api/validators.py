"""声明式API测试验证器"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from .response import APIResponse

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class BaseValidator(ABC):
    """验证器基类"""
    
    @abstractmethod
    def validate(self, response: APIResponse, config: Dict[str, Any]):
        """执行验证"""
        pass


class StatusCodeValidator(BaseValidator):
    """状态码验证器"""
    
    def validate(self, response: APIResponse, config: Dict[str, Any]):
        expected_code = config.get('expected', 200)
        response.assert_status_code(expected_code)


class ContainsValidator(BaseValidator):
    """包含文本验证器"""
    
    def validate(self, response: APIResponse, config: Dict[str, Any]):
        text = config.get('text', '')
        response.assert_text_contains(text)


class JsonPathValidator(BaseValidator):
    """JSONPath验证器"""
    
    def validate(self, response: APIResponse, config: Dict[str, Any]):
        path = config.get('path', '')
        expected = config.get('expected')
        response.assert_json_path(path, expected)


class HasKeysValidator(BaseValidator):
    """JSON键存在验证器"""
    
    def validate(self, response: APIResponse, config: Dict[str, Any]):
        keys = config.get('keys', [])
        response.assert_json_has_keys(*keys)


class HeaderValidator(BaseValidator):
    """响应头验证器"""
    
    def validate(self, response: APIResponse, config: Dict[str, Any]):
        name = config.get('name', '')
        expected = config.get('expected', '')
        response.assert_header(name, expected)


class ResponseTimeValidator(BaseValidator):
    """响应时间验证器"""
    
    def validate(self, response: APIResponse, config: Dict[str, Any]):
        max_seconds = config.get('max_seconds', 5.0)
        response.assert_response_time_less_than(max_seconds)


class JsonSchemaValidator(BaseValidator):
    """JSON Schema验证器"""

    def validate(self, response: APIResponse, config: Dict[str, Any]):
        if not HAS_JSONSCHEMA:
            raise ImportError("jsonschema is required for JSON Schema validation. Install with: pip install jsonschema")

        schema = config.get('schema', {})
        try:
            jsonschema.validate(response.json_data, schema)
        except jsonschema.ValidationError as e:
            raise AssertionError(f"JSON Schema validation failed: {e.message}")


class LessThanValidator(BaseValidator):
    """数值小于验证器"""
    
    def validate(self, response: APIResponse, config: Dict[str, Any]):
        path = config.get('path', '')
        max_value = config.get('max_value', 0)
        
        actual_value = response.get_json_value(path)
        if not isinstance(actual_value, (int, float)):
            raise AssertionError(f"Value at path '{path}' is not numeric: {actual_value}")
        
        if actual_value >= max_value:
            raise AssertionError(f"Value {actual_value} is not less than {max_value}")


class GreaterThanValidator(BaseValidator):
    """数值大于验证器"""
    
    def validate(self, response: APIResponse, config: Dict[str, Any]):
        path = config.get('path', '')
        min_value = config.get('min_value', 0)
        
        actual_value = response.get_json_value(path)
        if not isinstance(actual_value, (int, float)):
            raise AssertionError(f"Value at path '{path}' is not numeric: {actual_value}")
        
        if actual_value <= min_value:
            raise AssertionError(f"Value {actual_value} is not greater than {min_value}")


class ValidatorRegistry:
    """验证器注册表"""
    
    def __init__(self):
        self.validators = {
            'status_code': StatusCodeValidator(),
            'contains': ContainsValidator(),
            'jsonpath': JsonPathValidator(),
            'has_keys': HasKeysValidator(),
            'header': HeaderValidator(),
            'response_time': ResponseTimeValidator(),
            'json_schema': JsonSchemaValidator(),
            'less_than': LessThanValidator(),
            'greater_than': GreaterThanValidator(),
        }
    
    def register_validator(self, name: str, validator: BaseValidator):
        """注册新的验证器"""
        self.validators[name] = validator
    
    def get_validator(self, name: str) -> BaseValidator:
        """获取验证器"""
        return self.validators.get(name)
    
    def list_validators(self) -> list:
        """列出所有可用的验证器"""
        return list(self.validators.keys())
