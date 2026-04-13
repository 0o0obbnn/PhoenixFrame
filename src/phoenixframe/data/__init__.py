"""测试数据管理模块"""
import os
import json
import yaml
import csv
import sqlite3
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, TypeVar, Generic, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager
from abc import ABC, abstractmethod
import threading
import uuid

# 检查可选依赖
try:
    from faker import Faker
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False
    Faker = None

try:
    import sqlalchemy
    from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime, Text
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    sqlalchemy = None

from ..observability.logger import get_logger
from ..observability.tracer import get_tracer
from ..observability.metrics import record_test_metric

T = TypeVar('T')


@dataclass
class DataSource:
    """数据源配置"""
    name: str
    type: str  # file, database, api, generator
    location: str  # 文件路径、数据库连接字符串、API端点等
    format: str = "json"  # json, yaml, csv, sql等
    encoding: str = "utf-8"
    options: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestDataset:
    """测试数据集"""
    name: str
    description: str
    data: List[Dict[str, Any]]
    schema: Optional[Dict[str, Any]] = None
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.schema is None:
            self.schema = self._infer_schema()
    
    def _infer_schema(self) -> Dict[str, Any]:
        """推断数据模式"""
        if not self.data:
            return {}
        
        sample = self.data[0]
        schema = {}
        
        for key, value in sample.items():
            if isinstance(value, str):
                schema[key] = {"type": "string", "max_length": max(len(str(item.get(key, ""))) for item in self.data)}
            elif isinstance(value, int):
                schema[key] = {"type": "integer", "min": min(item.get(key, 0) for item in self.data), 
                             "max": max(item.get(key, 0) for item in self.data)}
            elif isinstance(value, float):
                schema[key] = {"type": "float"}
            elif isinstance(value, bool):
                schema[key] = {"type": "boolean"}
            elif isinstance(value, list):
                schema[key] = {"type": "array"}
            elif isinstance(value, dict):
                schema[key] = {"type": "object"}
            else:
                schema[key] = {"type": "unknown"}
        
        return schema


@dataclass
class DataMask:
    """数据脱敏配置"""
    field: str
    mask_type: str  # partial, hash, replace, anonymize
    options: Dict[str, Any] = field(default_factory=dict)


class DataMasker:
    """数据脱敏器"""
    
    def __init__(self):
        self.logger = get_logger("phoenixframe.data.masker")
        
        # 预定义脱敏规则
        self.default_masks = {
            "email": DataMask("email", "partial", {"pattern": "***@***.***"}),
            "phone": DataMask("phone", "partial", {"pattern": "***-***-****"}),
            "ssn": DataMask("ssn", "hash", {}),
            "credit_card": DataMask("credit_card", "partial", {"pattern": "****-****-****-****"}),
            "password": DataMask("password", "replace", {"value": "***MASKED***"}),
            "id_number": DataMask("id_number", "partial", {"pattern": "****"}),
        }
    
    def mask_data(self, data: Dict[str, Any], masks: List[DataMask]) -> Dict[str, Any]:
        """对数据进行脱敏"""
        masked_data = data.copy()
        
        for mask in masks:
            if mask.field in masked_data:
                masked_data[mask.field] = self._apply_mask(masked_data[mask.field], mask)
        
        return masked_data
    
    def mask_dataset(self, dataset: TestDataset, masks: List[DataMask]) -> TestDataset:
        """对数据集进行脱敏"""
        masked_data = []
        for item in dataset.data:
            masked_item = self.mask_data(item, masks)
            masked_data.append(masked_item)
        
        return TestDataset(
            name=f"{dataset.name}_masked",
            description=f"Masked version of {dataset.description}",
            data=masked_data,
            schema=dataset.schema,
            version=dataset.version,
            tags=dataset.tags + ["masked"],
            metadata=dataset.metadata
        )
    
    def _apply_mask(self, value: Any, mask: DataMask) -> Any:
        """应用脱敏规则"""
        if value is None:
            return None
            
        str_value = str(value)
        
        if mask.mask_type == "partial":
            pattern = mask.options.get("pattern", "***")
            if "email" in mask.field.lower():
                return self._mask_email(str_value)
            elif "phone" in mask.field.lower():
                return self._mask_phone(str_value)
            else:
                return pattern
                
        elif mask.mask_type == "hash":
            return hashlib.sha256(str_value.encode()).hexdigest()[:8]
            
        elif mask.mask_type == "replace":
            return mask.options.get("value", "***MASKED***")
            
        elif mask.mask_type == "anonymize":
            # 使用Faker生成同类型的假数据
            if FAKER_AVAILABLE:
                fake = Faker()
                if "email" in mask.field.lower():
                    return fake.email()
                elif "name" in mask.field.lower():
                    return fake.name()
                elif "address" in mask.field.lower():
                    return fake.address()
                elif "phone" in mask.field.lower():
                    return fake.phone_number()
                else:
                    return fake.word()
            else:
                return "***ANONYMIZED***"
        
        return value
    
    def _mask_email(self, email: str) -> str:
        """脱敏邮箱地址"""
        if "@" not in email:
            return "***@***.***"
        
        parts = email.split("@")
        if len(parts[0]) <= 2:
            masked_user = "***"
        else:
            masked_user = parts[0][0] + "***" + parts[0][-1]
        
        domain_parts = parts[1].split(".")
        if len(domain_parts) >= 2:
            masked_domain = "***." + domain_parts[-1]
        else:
            masked_domain = "***"
        
        return f"{masked_user}@{masked_domain}"
    
    def _mask_phone(self, phone: str) -> str:
        """脱敏电话号码"""
        digits_only = ''.join(filter(str.isdigit, phone))
        if len(digits_only) >= 8:
            return digits_only[:3] + "***" + digits_only[-2:]
        return "***-***-****"


class DataFactory(Generic[T]):
    """数据工厂基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"phoenixframe.data.factory.{name}")
        self.tracer = get_tracer(f"phoenixframe.data.factory.{name}")
        self._builders: Dict[str, Callable] = {}
    
    def register_builder(self, data_type: str, builder: Callable[..., T]) -> None:
        """注册数据构建器"""
        self._builders[data_type] = builder
        self.logger.info(f"Registered builder for {data_type}")
    
    def create(self, data_type: str, **kwargs) -> T:
        """创建数据"""
        if data_type not in self._builders:
            raise ValueError(f"No builder registered for {data_type}")
        
        with self.tracer.trace_test_case(f"data_factory_create_{data_type}", "", "running"):
            try:
                result = self._builders[data_type](**kwargs)
                self.logger.info(f"Created {data_type} data")
                return result
            except Exception as e:
                self.logger.error(f"Failed to create {data_type} data: {e}")
                raise
    
    def get_available_types(self) -> List[str]:
        """获取可用的数据类型"""
        return list(self._builders.keys())


class DataBuilder(Generic[T]):
    """数据构建器基类"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
    
    def with_field(self, field: str, value: Any) -> 'DataBuilder[T]':
        """设置字段值"""
        self._data[field] = value
        return self
    
    def with_fields(self, **fields) -> 'DataBuilder[T]':
        """批量设置字段"""
        self._data.update(fields)
        return self
    
    @abstractmethod
    def build(self) -> T:
        """构建数据对象"""
        pass
    
    def reset(self) -> 'DataBuilder[T]':
        """重置构建器"""
        self._data.clear()
        return self


class FakeDataGenerator:
    """假数据生成器"""
    
    def __init__(self, locale: str = "en_US"):
        self.logger = get_logger("phoenixframe.data.generator")
        
        if not FAKER_AVAILABLE:
            self.logger.warning("Faker not available. Install with: pip install faker")
            self.fake = None
        else:
            self.fake = Faker(locale)
    
    def generate_user_data(self, count: int = 1) -> List[Dict[str, Any]]:
        """生成用户数据"""
        if not self.fake:
            return [{"error": "Faker not available"}] * count
        
        users = []
        for _ in range(count):
            user = {
                "id": self.fake.uuid4(),
                "username": self.fake.user_name(),
                "email": self.fake.email(),
                "first_name": self.fake.first_name(),
                "last_name": self.fake.last_name(),
                "phone": self.fake.phone_number(),
                "address": {
                    "street": self.fake.street_address(),
                    "city": self.fake.city(),
                    "state": self.fake.state(),
                    "zip_code": self.fake.zipcode(),
                    "country": self.fake.country()
                },
                "birth_date": self.fake.date_of_birth().isoformat(),
                "created_at": self.fake.date_time_this_year().isoformat(),
                "is_active": self.fake.boolean(),
                "profile": {
                    "bio": self.fake.text(max_nb_chars=200),
                    "avatar_url": self.fake.image_url(),
                    "website": self.fake.url()
                }
            }
            users.append(user)
        
        self.logger.info(f"Generated {count} user records")
        return users
    
    def generate_order_data(self, count: int = 1) -> List[Dict[str, Any]]:
        """生成订单数据"""
        if not self.fake:
            return [{"error": "Faker not available"}] * count
        
        orders = []
        for _ in range(count):
            order = {
                "id": self.fake.uuid4(),
                "order_number": self.fake.numerify("ORD-######"),
                "customer_id": self.fake.uuid4(),
                "status": self.fake.random_element(["pending", "processing", "shipped", "delivered", "cancelled"]),
                "total_amount": round(self.fake.random_number(digits=3, fix_len=False) * 0.99, 2),
                "currency": self.fake.currency_code(),
                "items": [
                    {
                        "product_id": self.fake.uuid4(),
                        "name": self.fake.catch_phrase(),
                        "quantity": self.fake.random_int(min=1, max=5),
                        "price": round(self.fake.random_number(digits=2, fix_len=False) * 0.99, 2)
                    }
                    for _ in range(self.fake.random_int(min=1, max=3))
                ],
                "shipping_address": {
                    "name": self.fake.name(),
                    "street": self.fake.street_address(),
                    "city": self.fake.city(),
                    "state": self.fake.state(),
                    "zip_code": self.fake.zipcode()
                },
                "created_at": self.fake.date_time_this_month().isoformat(),
                "updated_at": self.fake.date_time_this_week().isoformat()
            }
            orders.append(order)
        
        self.logger.info(f"Generated {count} order records")
        return orders
    
    def generate_product_data(self, count: int = 1) -> List[Dict[str, Any]]:
        """生成产品数据"""
        if not self.fake:
            return [{"error": "Faker not available"}] * count
        
        products = []
        for _ in range(count):
            product = {
                "id": self.fake.uuid4(),
                "sku": self.fake.numerify("SKU-########"),
                "name": self.fake.catch_phrase(),
                "description": self.fake.text(max_nb_chars=500),
                "category": self.fake.word(),
                "price": round(self.fake.random_number(digits=3, fix_len=False) * 0.99, 2),
                "cost": round(self.fake.random_number(digits=2, fix_len=False) * 0.99, 2),
                "currency": self.fake.currency_code(),
                "stock_quantity": self.fake.random_int(min=0, max=1000),
                "weight": round(self.fake.random_number(digits=2, fix_len=False) * 0.1, 2),
                "dimensions": {
                    "length": round(self.fake.random_number(digits=2, fix_len=False) * 0.1, 2),
                    "width": round(self.fake.random_number(digits=2, fix_len=False) * 0.1, 2),
                    "height": round(self.fake.random_number(digits=2, fix_len=False) * 0.1, 2)
                },
                "images": [self.fake.image_url() for _ in range(self.fake.random_int(min=1, max=4))],
                "tags": [self.fake.word() for _ in range(self.fake.random_int(min=1, max=5))],
                "is_active": self.fake.boolean(),
                "created_at": self.fake.date_time_this_year().isoformat(),
                "updated_at": self.fake.date_time_this_month().isoformat()
            }
            products.append(product)
        
        self.logger.info(f"Generated {count} product records")
        return products
    
    def generate_custom_data(self, schema: Dict[str, Any], count: int = 1) -> List[Dict[str, Any]]:
        """根据模式生成自定义数据"""
        if not self.fake:
            return [{"error": "Faker not available"}] * count
        
        data = []
        for _ in range(count):
            record = {}
            for field, field_schema in schema.items():
                record[field] = self._generate_field_value(field, field_schema)
            data.append(record)
        
        self.logger.info(f"Generated {count} custom records")
        return data
    
    def _generate_field_value(self, field_name: str, field_schema: Dict[str, Any]) -> Any:
        """根据字段模式生成值"""
        field_type = field_schema.get("type", "string")
        
        if field_type == "string":
            max_length = field_schema.get("max_length", 50)
            if "email" in field_name.lower():
                return self.fake.email()
            elif "name" in field_name.lower():
                return self.fake.name()
            elif "phone" in field_name.lower():
                return self.fake.phone_number()
            elif "address" in field_name.lower():
                return self.fake.address()
            elif "url" in field_name.lower():
                return self.fake.url()
            else:
                return self.fake.text(max_nb_chars=max_length)
        
        elif field_type == "integer":
            min_val = field_schema.get("min", 0)
            max_val = field_schema.get("max", 1000)
            return self.fake.random_int(min=min_val, max=max_val)
        
        elif field_type == "float":
            return round(self.fake.random.uniform(0, 1000), 2)
        
        elif field_type == "boolean":
            return self.fake.boolean()
        
        elif field_type == "date":
            return self.fake.date().isoformat()
        
        elif field_type == "datetime":
            return self.fake.date_time().isoformat()
        
        elif field_type == "uuid":
            return self.fake.uuid4()
        
        else:
            return self.fake.word()


class DataRepository:
    """数据仓库 - 管理测试数据的存储和检索"""
    
    def __init__(self, storage_path: str = "test_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("phoenixframe.data.repository")
        self.tracer = get_tracer("phoenixframe.data.repository")
        
        # 元数据存储
        self.metadata_file = self.storage_path / "metadata.json"
        self._metadata = self._load_metadata()
        
        # 线程锁
        self._lock = threading.Lock()
    
    def save_dataset(self, dataset: TestDataset, overwrite: bool = False) -> str:
        """保存数据集"""
        with self._lock:
            dataset_id = self._generate_dataset_id(dataset.name, dataset.version)
            dataset_path = self.storage_path / f"{dataset_id}.json"
            # 确保存储目录存在（即使外部传入的临时目录被替换或未创建）
            dataset_path.parent.mkdir(parents=True, exist_ok=True)
            
            if dataset_path.exists() and not overwrite:
                raise ValueError(f"Dataset {dataset_id} already exists. Use overwrite=True to replace.")
            
            # 保存数据集
            dataset_dict = {
                "name": dataset.name,
                "description": dataset.description,
                "data": dataset.data,
                "schema": dataset.schema,
                "version": dataset.version,
                "tags": dataset.tags,
                "created_at": dataset.created_at.isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": dataset.metadata
            }
            
            with open(dataset_path, 'w', encoding='utf-8') as f:
                json.dump(dataset_dict, f, indent=2, ensure_ascii=False)
            
            # 更新元数据
            self._metadata[dataset_id] = {
                "name": dataset.name,
                "version": dataset.version,
                "tags": dataset.tags,
                "file_path": str(dataset_path),
                "created_at": dataset.created_at.isoformat(),
                "updated_at": datetime.now().isoformat(),
                "record_count": len(dataset.data)
            }
            
            self._save_metadata()
            
            self.logger.info(f"Saved dataset: {dataset_id}")
            return dataset_id
    
    def load_dataset(self, dataset_id: str) -> TestDataset:
        """加载数据集"""
        if dataset_id not in self._metadata:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        dataset_path = Path(self._metadata[dataset_id]["file_path"])
        
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
        
        with open(dataset_path, 'r', encoding='utf-8') as f:
            dataset_dict = json.load(f)
        
        dataset = TestDataset(
            name=dataset_dict["name"],
            description=dataset_dict["description"],
            data=dataset_dict["data"],
            schema=dataset_dict.get("schema"),
            version=dataset_dict["version"],
            tags=dataset_dict.get("tags", []),
            created_at=datetime.fromisoformat(dataset_dict["created_at"]),
            updated_at=datetime.fromisoformat(dataset_dict["updated_at"]),
            metadata=dataset_dict.get("metadata", {})
        )
        
        self.logger.info(f"Loaded dataset: {dataset_id}")
        return dataset
    
    def list_datasets(self, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """列出数据集"""
        datasets = []
        
        for dataset_id, metadata in self._metadata.items():
            if tags:
                if not any(tag in metadata.get("tags", []) for tag in tags):
                    continue
            
            datasets.append({
                "id": dataset_id,
                "name": metadata["name"],
                "version": metadata["version"],
                "tags": metadata["tags"],
                "record_count": metadata["record_count"],
                "created_at": metadata["created_at"],
                "updated_at": metadata["updated_at"]
            })
        
        return sorted(datasets, key=lambda x: x["updated_at"], reverse=True)
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """删除数据集"""
        with self._lock:
            if dataset_id not in self._metadata:
                return False
            
            dataset_path = Path(self._metadata[dataset_id]["file_path"])
            
            if dataset_path.exists():
                dataset_path.unlink()
            
            del self._metadata[dataset_id]
            self._save_metadata()
            
            self.logger.info(f"Deleted dataset: {dataset_id}")
            return True
    
    def search_datasets(self, query: str) -> List[Dict[str, Any]]:
        """搜索数据集"""
        results = []
        query_lower = query.lower()
        
        for dataset_id, metadata in self._metadata.items():
            if (query_lower in metadata["name"].lower() or 
                any(query_lower in tag.lower() for tag in metadata.get("tags", []))):
                results.append({
                    "id": dataset_id,
                    "name": metadata["name"],
                    "version": metadata["version"],
                    "tags": metadata["tags"],
                    "record_count": metadata["record_count"],
                    "relevance_score": self._calculate_relevance(query_lower, metadata)
                })
        
        return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    
    def _generate_dataset_id(self, name: str, version: str) -> str:
        """生成数据集ID"""
        clean_name = "".join(c for c in name if c.isalnum() or c in "._-").lower()
        return f"{clean_name}_v{version}"
    
    def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self) -> None:
        """保存元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self._metadata, f, indent=2, ensure_ascii=False)
    
    def _calculate_relevance(self, query: str, metadata: Dict[str, Any]) -> float:
        """计算相关性分数"""
        score = 0.0
        
        # 名称匹配
        if query in metadata["name"].lower():
            score += 10.0
        
        # 标签匹配
        for tag in metadata.get("tags", []):
            if query in tag.lower():
                score += 5.0
        
        return score


# 全局实例
_data_repository: Optional[DataRepository] = None
_data_masker: Optional[DataMasker] = None
_fake_generator: Optional[FakeDataGenerator] = None


def get_data_repository(storage_path: str = "test_data") -> DataRepository:
    """获取数据仓库实例"""
    global _data_repository
    if _data_repository is None:
        _data_repository = DataRepository(storage_path)
    return _data_repository


def get_data_masker() -> DataMasker:
    """获取数据脱敏器实例"""
    global _data_masker
    if _data_masker is None:
        _data_masker = DataMasker()
    return _data_masker


def get_fake_generator(locale: str = "en_US") -> FakeDataGenerator:
    """获取假数据生成器实例"""
    global _fake_generator
    if _fake_generator is None:
        _fake_generator = FakeDataGenerator(locale)
    return _fake_generator


__all__ = [
    "DataSource",
    "TestDataset", 
    "DataMask",
    "DataMasker",
    "DataFactory",
    "DataBuilder",
    "FakeDataGenerator",
    "DataRepository",
    "get_data_repository",
    "get_data_masker", 
    "get_fake_generator",
    "FAKER_AVAILABLE",
    "SQLALCHEMY_AVAILABLE"
]