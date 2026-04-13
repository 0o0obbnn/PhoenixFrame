"""测试数据处理工具模块"""
import pytest
import re
from unittest.mock import patch
from src.phoenixframe.utils.data_utils import DataUtil


def test_generate_random_string():
    """测试生成随机字符串"""
    # 测试默认参数
    result = DataUtil.generate_random_string()
    assert len(result) == 10
    assert all(c.isalnum() for c in result)
    
    # 测试自定义长度和字符集
    result = DataUtil.generate_random_string(5, "abc")
    assert len(result) == 5
    assert all(c in "abc" for c in result)


def test_generate_random_email():
    """测试生成随机邮箱"""
    # 测试默认域名
    email = DataUtil.generate_random_email()
    assert "@example.com" in email
    assert len(email.split("@")[0]) == 8
    
    # 测试自定义域名
    email = DataUtil.generate_random_email("test.com")
    assert "@test.com" in email


def test_generate_random_phone():
    """测试生成随机手机号"""
    # 测试中国手机号
    phone = DataUtil.generate_random_phone("+86")
    assert phone.startswith("+86")
    assert len(phone) == 14  # +86 + 3位前缀 + 8位数字
    
    # 测试其他国家代码
    phone = DataUtil.generate_random_phone("+1")
    assert phone.startswith("+1")
    assert len(phone) == 12  # +1 + 10位数字


def test_generate_uuid():
    """测试生成UUID"""
    uuid1 = DataUtil.generate_uuid()
    uuid2 = DataUtil.generate_uuid()
    
    assert len(uuid1) == 36  # UUID标准长度
    assert len(uuid2) == 36
    assert uuid1 != uuid2  # 应该是不同的UUID
    assert "-" in uuid1  # UUID包含连字符


def test_generate_timestamp():
    """测试生成时间戳"""
    timestamp = DataUtil.generate_timestamp()
    assert len(timestamp) > 0
    
    # 测试自定义格式
    timestamp = DataUtil.generate_timestamp("%Y-%m-%d")
    assert re.match(r"\d{4}-\d{2}-\d{2}", timestamp)


def test_generate_future_date():
    """测试生成未来日期"""
    future_date = DataUtil.generate_future_date(30)
    assert len(future_date) > 0
    assert re.match(r"\d{4}-\d{2}-\d{2}", future_date)


def test_generate_past_date():
    """测试生成过去日期"""
    past_date = DataUtil.generate_past_date(30)
    assert len(past_date) > 0
    assert re.match(r"\d{4}-\d{2}-\d{2}", past_date)


def test_generate_random_number():
    """测试生成随机数字"""
    # 测试默认范围
    number = DataUtil.generate_random_number()
    assert 1 <= number <= 100
    
    # 测试自定义范围
    number = DataUtil.generate_random_number(10, 20)
    assert 10 <= number <= 20


def test_generate_random_float():
    """测试生成随机浮点数"""
    # 测试默认范围
    number = DataUtil.generate_random_float()
    assert 0.0 <= number <= 1.0
    assert isinstance(number, float)
    
    # 测试自定义范围和精度
    number = DataUtil.generate_random_float(1.0, 2.0, 3)
    assert 1.0 <= number <= 2.0
    assert len(str(number).split('.')[1]) <= 3


def test_generate_random_choice():
    """测试随机选择"""
    choices = ["apple", "banana", "orange"]
    choice = DataUtil.generate_random_choice(choices)
    assert choice in choices


def test_generate_test_data():
    """测试根据模板生成测试数据"""
    template = {
        "name": {"type": "string", "length": 5},
        "email": {"type": "email", "domain": "test.com"},
        "age": {"type": "number", "min": 18, "max": 65},
        "score": {"type": "float", "min": 0.0, "max": 100.0, "precision": 1},
        "status": {"type": "choice", "choices": ["active", "inactive"]},
        "id": {"type": "uuid"},
        "created": {"type": "timestamp", "format": "%Y-%m-%d"},
        "static_field": "static_value"
    }
    
    data = DataUtil.generate_test_data(template)
    
    assert len(data["name"]) == 5
    assert "@test.com" in data["email"]
    assert 18 <= data["age"] <= 65
    assert 0.0 <= data["score"] <= 100.0
    assert data["status"] in ["active", "inactive"]
    assert len(data["id"]) == 36  # UUID长度
    assert re.match(r"\d{4}-\d{2}-\d{2}", data["created"])
    assert data["static_field"] == "static_value"


def test_generate_test_data_with_date_types():
    """测试生成包含日期类型的测试数据"""
    template = {
        "future_date": {"type": "date", "days": 30},
        "past_date": {"type": "date", "days": -30},
        "current_date": {"type": "date", "days": 0}
    }
    
    data = DataUtil.generate_test_data(template)
    
    assert re.match(r"\d{4}-\d{2}-\d{2}", data["future_date"])
    assert re.match(r"\d{4}-\d{2}-\d{2}", data["past_date"])
    assert re.match(r"\d{4}-\d{2}-\d{2}", data["current_date"])


def test_mask_sensitive_data():
    """测试遮蔽敏感数据"""
    # 测试默认参数
    masked = DataUtil.mask_sensitive_data("1234567890")
    assert masked == "12******90"
    
    # 测试自定义参数
    masked = DataUtil.mask_sensitive_data("1234567890", "#", 3, 1)
    assert masked == "123######0"
    
    # 测试短数据
    masked = DataUtil.mask_sensitive_data("123", "*", 2, 2)
    assert masked == "***"


def test_validate_email():
    """测试邮箱格式验证"""
    # 有效邮箱
    assert DataUtil.validate_email("test@example.com") is True
    assert DataUtil.validate_email("user.name@domain.co.uk") is True
    
    # 无效邮箱
    assert DataUtil.validate_email("invalid-email") is False
    assert DataUtil.validate_email("@example.com") is False
    assert DataUtil.validate_email("test@") is False


def test_validate_phone():
    """测试手机号格式验证"""
    # 中国手机号验证
    assert DataUtil.validate_phone("+8613012345678") is True
    assert DataUtil.validate_phone("+8615987654321") is True
    
    # 无效中国手机号
    assert DataUtil.validate_phone("+8612012345678") is False  # 120开头无效
    assert DataUtil.validate_phone("+86130123456") is False   # 位数不够
    
    # 其他国家手机号
    assert DataUtil.validate_phone("+11234567890", "+1") is True
    assert DataUtil.validate_phone("+1123456789", "+1") is False  # 位数不够


def test_generate_test_data_unknown_type():
    """测试未知数据类型的处理"""
    template = {
        "unknown_field": {"type": "unknown_type", "default": "default_value"}
    }
    
    data = DataUtil.generate_test_data(template)
    assert data["unknown_field"] == "default_value"


def test_generate_test_data_empty_choices():
    """测试空选择列表的处理"""
    template = {
        "empty_choice": {"type": "choice", "choices": []}
    }
    
    data = DataUtil.generate_test_data(template)
    assert "empty_choice" not in data or data["empty_choice"] is None
