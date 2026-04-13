"""数据处理工具模块"""
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union


class DataUtil:
    """数据处理工具类"""
    
    @staticmethod
    def generate_random_string(length: int = 10, 
                             charset: str = string.ascii_letters + string.digits) -> str:
        """
        生成随机字符串
        
        Args:
            length: 字符串长度
            charset: 字符集
            
        Returns:
            str: 随机字符串
        """
        return ''.join(random.choice(charset) for _ in range(length))
    
    @staticmethod
    def generate_random_email(domain: str = "example.com") -> str:
        """
        生成随机邮箱地址
        
        Args:
            domain: 邮箱域名
            
        Returns:
            str: 随机邮箱地址
        """
        username = DataUtil.generate_random_string(8, string.ascii_lowercase + string.digits)
        return f"{username}@{domain}"
    
    @staticmethod
    def generate_random_phone(country_code: str = "+86") -> str:
        """
        生成随机手机号
        
        Args:
            country_code: 国家代码
            
        Returns:
            str: 随机手机号
        """
        if country_code == "+86":
            # 中国手机号格式
            prefixes = ["130", "131", "132", "133", "134", "135", "136", "137", "138", "139",
                       "150", "151", "152", "153", "155", "156", "157", "158", "159",
                       "180", "181", "182", "183", "184", "185", "186", "187", "188", "189"]
            prefix = random.choice(prefixes)
            suffix = ''.join(random.choice(string.digits) for _ in range(8))
            return f"{country_code}{prefix}{suffix}"
        else:
            # 通用格式
            number = ''.join(random.choice(string.digits) for _ in range(10))
            return f"{country_code}{number}"
    
    @staticmethod
    def generate_uuid() -> str:
        """
        生成UUID
        
        Returns:
            str: UUID字符串
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_timestamp(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        生成当前时间戳
        
        Args:
            format_str: 时间格式
            
        Returns:
            str: 格式化的时间字符串
        """
        return datetime.now().strftime(format_str)
    
    @staticmethod
    def generate_future_date(days: int = 30, format_str: str = "%Y-%m-%d") -> str:
        """
        生成未来日期
        
        Args:
            days: 未来天数
            format_str: 日期格式
            
        Returns:
            str: 格式化的日期字符串
        """
        future_date = datetime.now() + timedelta(days=days)
        return future_date.strftime(format_str)
    
    @staticmethod
    def generate_past_date(days: int = 30, format_str: str = "%Y-%m-%d") -> str:
        """
        生成过去日期
        
        Args:
            days: 过去天数
            format_str: 日期格式
            
        Returns:
            str: 格式化的日期字符串
        """
        past_date = datetime.now() - timedelta(days=days)
        return past_date.strftime(format_str)
    
    @staticmethod
    def generate_random_number(min_val: int = 1, max_val: int = 100) -> int:
        """
        生成随机数字
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            int: 随机数字
        """
        return random.randint(min_val, max_val)
    
    @staticmethod
    def generate_random_float(min_val: float = 0.0, max_val: float = 1.0, 
                            precision: int = 2) -> float:
        """
        生成随机浮点数
        
        Args:
            min_val: 最小值
            max_val: 最大值
            precision: 精度（小数位数）
            
        Returns:
            float: 随机浮点数
        """
        value = random.uniform(min_val, max_val)
        return round(value, precision)
    
    @staticmethod
    def generate_random_choice(choices: List[Any]) -> Any:
        """
        从列表中随机选择一个元素
        
        Args:
            choices: 选择列表
            
        Returns:
            Any: 随机选择的元素
        """
        return random.choice(choices)
    
    @staticmethod
    def generate_test_data(template: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据模板生成测试数据
        
        Args:
            template: 数据模板
            
        Returns:
            Dict[str, Any]: 生成的测试数据
        """
        result = {}
        
        for key, value in template.items():
            if isinstance(value, dict):
                data_type = value.get("type", "string")
                
                if data_type == "string":
                    length = value.get("length", 10)
                    result[key] = DataUtil.generate_random_string(length)
                
                elif data_type == "email":
                    domain = value.get("domain", "example.com")
                    result[key] = DataUtil.generate_random_email(domain)
                
                elif data_type == "phone":
                    country_code = value.get("country_code", "+86")
                    result[key] = DataUtil.generate_random_phone(country_code)
                
                elif data_type == "number":
                    min_val = value.get("min", 1)
                    max_val = value.get("max", 100)
                    result[key] = DataUtil.generate_random_number(min_val, max_val)
                
                elif data_type == "float":
                    min_val = value.get("min", 0.0)
                    max_val = value.get("max", 1.0)
                    precision = value.get("precision", 2)
                    result[key] = DataUtil.generate_random_float(min_val, max_val, precision)
                
                elif data_type == "choice":
                    choices = value.get("choices", [])
                    if choices:
                        result[key] = DataUtil.generate_random_choice(choices)
                
                elif data_type == "uuid":
                    result[key] = DataUtil.generate_uuid()
                
                elif data_type == "timestamp":
                    format_str = value.get("format", "%Y-%m-%d %H:%M:%S")
                    result[key] = DataUtil.generate_timestamp(format_str)
                
                elif data_type == "date":
                    format_str = value.get("format", "%Y-%m-%d")
                    days = value.get("days", 0)
                    if days > 0:
                        result[key] = DataUtil.generate_future_date(days, format_str)
                    elif days < 0:
                        result[key] = DataUtil.generate_past_date(abs(days), format_str)
                    else:
                        result[key] = DataUtil.generate_timestamp(format_str)
                
                else:
                    result[key] = value.get("default", "")
            
            else:
                # 直接使用值
                result[key] = value
        
        return result
    
    @staticmethod
    def mask_sensitive_data(data: str, mask_char: str = "*", 
                          keep_start: int = 2, keep_end: int = 2) -> str:
        """
        遮蔽敏感数据
        
        Args:
            data: 原始数据
            mask_char: 遮蔽字符
            keep_start: 保留开头字符数
            keep_end: 保留结尾字符数
            
        Returns:
            str: 遮蔽后的数据
        """
        if len(data) <= keep_start + keep_end:
            return mask_char * len(data)
        
        start = data[:keep_start]
        end = data[-keep_end:] if keep_end > 0 else ""
        middle = mask_char * (len(data) - keep_start - keep_end)
        
        return start + middle + end
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            bool: 是否为有效邮箱格式
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str, country_code: str = "+86") -> bool:
        """
        验证手机号格式
        
        Args:
            phone: 手机号
            country_code: 国家代码
            
        Returns:
            bool: 是否为有效手机号格式
        """
        import re
        
        if country_code == "+86":
            # 中国手机号验证
            pattern = r'^\+86(130|131|132|133|134|135|136|137|138|139|150|151|152|153|155|156|157|158|159|180|181|182|183|184|185|186|187|188|189)\d{8}$'
            return bool(re.match(pattern, phone))
        else:
            # 通用手机号验证（国家代码+10位数字）
            pattern = rf'^{re.escape(country_code)}\d{{10}}$'
            return bool(re.match(pattern, phone))
