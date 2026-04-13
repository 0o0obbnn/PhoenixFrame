"""测试数据工具函数"""
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def load_test_data(file_path: Union[str, Path], format: Optional[str] = None) -> Any:
    """
    加载测试数据文件
    
    Args:
        file_path: 文件路径
        format: 文件格式 ('json', 'yaml', 'yml')，如果不指定则根据扩展名自动判断
    
    Returns:
        解析后的数据
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Test data file not found: {file_path}")
    
    # 自动判断格式
    if format is None:
        suffix = file_path.suffix.lower()
        if suffix == '.json':
            format = 'json'
        elif suffix in ['.yaml', '.yml']:
            format = 'yaml'
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        if format == 'json':
            return json.load(f)
        elif format == 'yaml':
            return yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported format: {format}")


def generate_test_data(template: Dict[str, Any], count: int = 1) -> List[Dict[str, Any]]:
    """
    根据模板生成测试数据
    
    Args:
        template: 数据模板
        count: 生成数量
    
    Returns:
        生成的测试数据列表
    """
    import random
    import uuid
    from datetime import datetime, timedelta
    
    def generate_value(field_type: str, **kwargs) -> Any:
        """根据类型生成值"""
        if field_type == 'string':
            length = kwargs.get('length', 10)
            return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=length))
        elif field_type == 'integer':
            min_val = kwargs.get('min', 1)
            max_val = kwargs.get('max', 100)
            return random.randint(min_val, max_val)
        elif field_type == 'float':
            min_val = kwargs.get('min', 0.0)
            max_val = kwargs.get('max', 100.0)
            return round(random.uniform(min_val, max_val), 2)
        elif field_type == 'boolean':
            return random.choice([True, False])
        elif field_type == 'uuid':
            return str(uuid.uuid4())
        elif field_type == 'email':
            username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))
            domain = random.choice(['gmail.com', 'yahoo.com', 'hotmail.com', 'example.com'])
            return f"{username}@{domain}"
        elif field_type == 'datetime':
            base = datetime.now()
            offset_days = kwargs.get('offset_days', 0)
            return (base + timedelta(days=offset_days)).isoformat()
        elif field_type == 'choice':
            choices = kwargs.get('choices', ['option1', 'option2', 'option3'])
            return random.choice(choices)
        else:
            return kwargs.get('default', None)
    
    results = []
    for i in range(count):
        data = {}
        for field_name, field_config in template.items():
            if isinstance(field_config, dict):
                field_type = field_config.get('type', 'string')
                field_kwargs = {k: v for k, v in field_config.items() if k != 'type'}
                # 如果有序号，添加到kwargs中
                field_kwargs['index'] = i + 1
                data[field_name] = generate_value(field_type, **field_kwargs)
            else:
                # 简单类型
                data[field_name] = field_config
        results.append(data)
    
    return results


def save_test_data(data: Any, file_path: Union[str, Path], format: Optional[str] = None) -> None:
    """
    保存测试数据到文件
    
    Args:
        data: 要保存的数据
        file_path: 文件路径
        format: 文件格式 ('json', 'yaml')，如果不指定则根据扩展名自动判断
    """
    file_path = Path(file_path)
    
    # 确保目录存在
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 自动判断格式
    if format is None:
        suffix = file_path.suffix.lower()
        if suffix == '.json':
            format = 'json'
        elif suffix in ['.yaml', '.yml']:
            format = 'yaml'
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        if format == 'json':
            json.dump(data, f, indent=2, ensure_ascii=False)
        elif format == 'yaml':
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported format: {format}")


def merge_test_data(*data_sources: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个测试数据源
    
    Args:
        *data_sources: 数据源字典
    
    Returns:
        合并后的数据
    """
    result = {}
    for source in data_sources:
        if isinstance(source, dict):
            result.update(source)
    return result


def filter_test_data(data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    过滤测试数据
    
    Args:
        data: 测试数据列表
        filters: 过滤条件
    
    Returns:
        过滤后的数据
    """
    def matches_filter(item: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if key not in item:
                return False
            if item[key] != value:
                return False
        return True
    
    return [item for item in data if matches_filter(item, filters)]


def validate_test_data(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    验证测试数据
    
    Args:
        data: 测试数据
        schema: 数据模式
    
    Returns:
        验证错误列表
    """
    errors = []
    
    for field_name, field_schema in schema.items():
        if field_name not in data:
            if field_schema.get('required', False):
                errors.append(f"Required field '{field_name}' is missing")
            continue
        
        value = data[field_name]
        expected_type = field_schema.get('type')
        
        if expected_type:
            if expected_type == 'string' and not isinstance(value, str):
                errors.append(f"Field '{field_name}' should be string, got {type(value).__name__}")
            elif expected_type == 'integer' and not isinstance(value, int):
                errors.append(f"Field '{field_name}' should be integer, got {type(value).__name__}")
            elif expected_type == 'float' and not isinstance(value, (int, float)):
                errors.append(f"Field '{field_name}' should be float, got {type(value).__name__}")
            elif expected_type == 'boolean' and not isinstance(value, bool):
                errors.append(f"Field '{field_name}' should be boolean, got {type(value).__name__}")
        
        # 检查值范围
        if 'min' in field_schema and value < field_schema['min']:
            errors.append(f"Field '{field_name}' value {value} is below minimum {field_schema['min']}")
        if 'max' in field_schema and value > field_schema['max']:
            errors.append(f"Field '{field_name}' value {value} is above maximum {field_schema['max']}")
        
        # 检查长度
        if 'min_length' in field_schema and len(str(value)) < field_schema['min_length']:
            errors.append(f"Field '{field_name}' length is below minimum {field_schema['min_length']}")
        if 'max_length' in field_schema and len(str(value)) > field_schema['max_length']:
            errors.append(f"Field '{field_name}' length is above maximum {field_schema['max_length']}")
    
    return errors