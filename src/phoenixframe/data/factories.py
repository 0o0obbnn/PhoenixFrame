"""数据工厂和构建器具体实现"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid
import random

from . import DataFactory, DataBuilder, TestDataset, get_fake_generator
from ..observability.logger import get_logger


@dataclass
class User:
    """用户数据模型"""
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass 
class Product:
    """产品数据模型"""
    id: str
    sku: str
    name: str
    description: str
    price: float
    category: str
    stock_quantity: int = 0
    is_active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "category": self.category,
            "stock_quantity": self.stock_quantity,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class Order:
    """订单数据模型"""
    id: str
    order_number: str
    customer_id: str
    status: str
    total_amount: float
    currency: str = "USD"
    items: List[Dict[str, Any]] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.items is None:
            self.items = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "order_number": self.order_number,
            "customer_id": self.customer_id,
            "status": self.status,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "items": self.items,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class UserBuilder(DataBuilder[User]):
    """用户数据构建器"""
    
    def __init__(self):
        super().__init__()
        self.fake = get_fake_generator()
        
        # 设置默认值
        self._data = {
            "id": str(uuid.uuid4()),
            "username": None,
            "email": None,
            "first_name": None,
            "last_name": None,
            "phone": None,
            "is_active": True,
            "created_at": datetime.now()
        }
    
    def with_random_data(self) -> 'UserBuilder':
        """使用随机数据"""
        if self.fake.fake:
            self._data.update({
                "username": self.fake.fake.user_name(),
                "email": self.fake.fake.email(),
                "first_name": self.fake.fake.first_name(),
                "last_name": self.fake.fake.last_name(),
                "phone": self.fake.fake.phone_number()
            })
        else:
            self._data.update({
                "username": f"user_{random.randint(1000, 9999)}",
                "email": f"user{random.randint(1000, 9999)}@example.com",
                "first_name": f"FirstName{random.randint(100, 999)}",
                "last_name": f"LastName{random.randint(100, 999)}",
                "phone": f"+1-555-{random.randint(1000, 9999)}"
            })
        return self
    
    def with_admin_role(self) -> 'UserBuilder':
        """设置为管理员"""
        self._data["username"] = "admin_" + self._data.get("username", "user")
        self._data["email"] = "admin." + self._data.get("email", "admin@example.com")
        return self
    
    def with_inactive_status(self) -> 'UserBuilder':
        """设置为非活跃状态"""
        self._data["is_active"] = False
        return self
    
    def created_days_ago(self, days: int) -> 'UserBuilder':
        """设置创建时间为几天前"""
        self._data["created_at"] = datetime.now() - timedelta(days=days)
        return self
    
    def build(self) -> User:
        """构建用户对象"""
        return User(**self._data)


class ProductBuilder(DataBuilder[Product]):
    """产品数据构建器"""
    
    def __init__(self):
        super().__init__()
        self.fake = get_fake_generator()
        
        # 设置默认值
        self._data = {
            "id": str(uuid.uuid4()),
            "sku": f"SKU-{random.randint(10000, 99999)}",
            "name": None,
            "description": None,
            "price": 0.0,
            "category": "general",
            "stock_quantity": 0,
            "is_active": True,
            "created_at": datetime.now()
        }
    
    def with_random_data(self) -> 'ProductBuilder':
        """使用随机数据"""
        if self.fake.fake:
            self._data.update({
                "name": self.fake.fake.catch_phrase(),
                "description": self.fake.fake.text(max_nb_chars=200),
                "price": round(self.fake.fake.random_number(digits=3, fix_len=False) * 0.99, 2),
                "category": self.fake.fake.word()
            })
        else:
            self._data.update({
                "name": f"Product {random.randint(1000, 9999)}",
                "description": f"Description for product {random.randint(1000, 9999)}",
                "price": round(random.uniform(10.0, 999.99), 2),
                "category": random.choice(["electronics", "clothing", "books", "home", "sports"])
            })
        return self
    
    def with_electronics_category(self) -> 'ProductBuilder':
        """设置为电子产品类别"""
        self._data["category"] = "electronics"
        if not self._data["name"]:
            self._data["name"] = f"Electronic Device {random.randint(1000, 9999)}"
        return self
    
    def with_high_price(self) -> 'ProductBuilder':
        """设置为高价商品"""
        self._data["price"] = round(random.uniform(500.0, 2000.0), 2)
        return self
    
    def with_stock(self, quantity: int) -> 'ProductBuilder':
        """设置库存数量"""
        self._data["stock_quantity"] = quantity
        return self
    
    def with_out_of_stock(self) -> 'ProductBuilder':
        """设置为缺货"""
        self._data["stock_quantity"] = 0
        self._data["is_active"] = False
        return self
    
    def build(self) -> Product:
        """构建产品对象"""
        return Product(**self._data)


class OrderBuilder(DataBuilder[Order]):
    """订单数据构建器"""
    
    def __init__(self):
        super().__init__()
        self.fake = get_fake_generator()
        
        # 设置默认值
        self._data = {
            "id": str(uuid.uuid4()),
            "order_number": f"ORD-{random.randint(100000, 999999)}",
            "customer_id": str(uuid.uuid4()),
            "status": "pending",
            "total_amount": 0.0,
            "currency": "USD",
            "items": [],
            "created_at": datetime.now()
        }
    
    def with_random_customer(self) -> 'OrderBuilder':
        """使用随机客户"""
        self._data["customer_id"] = str(uuid.uuid4())
        return self
    
    def with_status(self, status: str) -> 'OrderBuilder':
        """设置订单状态"""
        self._data["status"] = status
        return self
    
    def with_completed_status(self) -> 'OrderBuilder':
        """设置为已完成状态"""
        self._data["status"] = "completed"
        return self
    
    def with_cancelled_status(self) -> 'OrderBuilder':
        """设置为已取消状态"""
        self._data["status"] = "cancelled"
        return self
    
    def add_item(self, product_id: str, quantity: int, price: float, name: str = None) -> 'OrderBuilder':
        """添加订单项"""
        item = {
            "product_id": product_id,
            "name": name or f"Product {product_id[:8]}",
            "quantity": quantity,
            "price": price,
            "total": round(quantity * price, 2)
        }
        self._data["items"].append(item)
        
        # 更新总金额
        self._data["total_amount"] = sum(item["total"] for item in self._data["items"])
        return self
    
    def add_random_items(self, count: int = None) -> 'OrderBuilder':
        """添加随机订单项"""
        if count is None:
            count = random.randint(1, 5)
        
        for _ in range(count):
            price = round(random.uniform(10.0, 100.0), 2)
            quantity = random.randint(1, 3)
            
            if self.fake.fake:
                name = self.fake.fake.catch_phrase()
            else:
                name = f"Random Product {random.randint(1000, 9999)}"
            
            self.add_item(
                product_id=str(uuid.uuid4()),
                quantity=quantity,
                price=price,
                name=name
            )
        
        return self
    
    def with_currency(self, currency: str) -> 'OrderBuilder':
        """设置货币"""
        self._data["currency"] = currency
        return self
    
    def created_days_ago(self, days: int) -> 'OrderBuilder':
        """设置创建时间为几天前"""
        self._data["created_at"] = datetime.now() - timedelta(days=days)
        return self
    
    def build(self) -> Order:
        """构建订单对象"""
        return Order(**self._data)


class TestDataFactory(DataFactory[Dict[str, Any]]):
    """测试数据工厂"""
    
    def __init__(self):
        super().__init__("test_data")
        self._register_default_builders()
    
    def _register_default_builders(self):
        """注册默认构建器"""
        self.register_builder("user", self._create_user_data)
        self.register_builder("product", self._create_product_data)
        self.register_builder("order", self._create_order_data)
        self.register_builder("users_batch", self._create_users_batch)
        self.register_builder("products_batch", self._create_products_batch)
        self.register_builder("orders_batch", self._create_orders_batch)
    
    def _create_user_data(self, **kwargs) -> Dict[str, Any]:
        """创建用户数据"""
        builder = UserBuilder()
        
        if kwargs.get("random", True):
            builder.with_random_data()
        
        if kwargs.get("admin", False):
            builder.with_admin_role()
        
        if kwargs.get("inactive", False):
            builder.with_inactive_status()
        
        if "days_ago" in kwargs:
            builder.created_days_ago(kwargs["days_ago"])
        
        # 应用自定义字段
        for key, value in kwargs.items():
            if key not in ["random", "admin", "inactive", "days_ago"]:
                builder.with_field(key, value)
        
        return builder.build().to_dict()
    
    def _create_product_data(self, **kwargs) -> Dict[str, Any]:
        """创建产品数据"""
        builder = ProductBuilder()
        
        if kwargs.get("random", True):
            builder.with_random_data()
        
        if kwargs.get("electronics", False):
            builder.with_electronics_category()
        
        if kwargs.get("high_price", False):
            builder.with_high_price()
        
        if "stock" in kwargs:
            builder.with_stock(kwargs["stock"])
        
        if kwargs.get("out_of_stock", False):
            builder.with_out_of_stock()
        
        # 应用自定义字段
        for key, value in kwargs.items():
            if key not in ["random", "electronics", "high_price", "stock", "out_of_stock"]:
                builder.with_field(key, value)
        
        return builder.build().to_dict()
    
    def _create_order_data(self, **kwargs) -> Dict[str, Any]:
        """创建订单数据"""
        builder = OrderBuilder()
        
        if kwargs.get("random_customer", True):
            builder.with_random_customer()
        
        if "status" in kwargs:
            builder.with_status(kwargs["status"])
        
        if kwargs.get("completed", False):
            builder.with_completed_status()
        
        if kwargs.get("cancelled", False):
            builder.with_cancelled_status()
        
        if kwargs.get("random_items", True):
            item_count = kwargs.get("item_count", None)
            builder.add_random_items(item_count)
        
        if "currency" in kwargs:
            builder.with_currency(kwargs["currency"])
        
        if "days_ago" in kwargs:
            builder.created_days_ago(kwargs["days_ago"])
        
        # 应用自定义字段
        excluded_keys = ["random_customer", "status", "completed", "cancelled", 
                        "random_items", "item_count", "currency", "days_ago"]
        for key, value in kwargs.items():
            if key not in excluded_keys:
                builder.with_field(key, value)
        
        return builder.build().to_dict()
    
    def _create_users_batch(self, **kwargs) -> List[Dict[str, Any]]:
        """批量创建用户数据"""
        count = kwargs.get("count", 10)
        users = []
        
        for i in range(count):
            user_kwargs = kwargs.copy()
            user_kwargs.pop("count", None)
            
            # 为每个用户添加索引
            if "username_prefix" in kwargs:
                user_kwargs["username"] = f"{kwargs['username_prefix']}_{i+1}"
            
            users.append(self._create_user_data(**user_kwargs))
        
        return users
    
    def _create_products_batch(self, **kwargs) -> List[Dict[str, Any]]:
        """批量创建产品数据"""
        count = kwargs.get("count", 10)
        products = []
        
        for i in range(count):
            product_kwargs = kwargs.copy()
            product_kwargs.pop("count", None)
            
            # 为每个产品添加索引
            if "name_prefix" in kwargs:
                product_kwargs["name"] = f"{kwargs['name_prefix']} {i+1}"
            
            products.append(self._create_product_data(**product_kwargs))
        
        return products
    
    def _create_orders_batch(self, **kwargs) -> List[Dict[str, Any]]:
        """批量创建订单数据"""
        count = kwargs.get("count", 10)
        orders = []
        
        for i in range(count):
            order_kwargs = kwargs.copy()
            order_kwargs.pop("count", None)
            orders.append(self._create_order_data(**order_kwargs))
        
        return orders


def create_test_dataset(name: str, data_type: str, count: int = 10, **kwargs) -> TestDataset:
    """创建测试数据集的便捷函数"""
    factory = TestDataFactory()
    
    if data_type.endswith("_batch"):
        data = factory.create(data_type, count=count, **kwargs)
    else:
        data = [factory.create(data_type, **kwargs) for _ in range(count)]
    
    return TestDataset(
        name=name,
        description=f"Generated {data_type} dataset with {len(data)} records",
        data=data,
        tags=[data_type, "generated"],
        metadata={"generator": "TestDataFactory", "data_type": data_type}
    )


# 全局工厂实例
_test_data_factory: Optional[TestDataFactory] = None


def get_test_data_factory() -> TestDataFactory:
    """获取测试数据工厂实例"""
    global _test_data_factory
    if _test_data_factory is None:
        _test_data_factory = TestDataFactory()
    return _test_data_factory


__all__ = [
    "User",
    "Product", 
    "Order",
    "UserBuilder",
    "ProductBuilder",
    "OrderBuilder",
    "TestDataFactory",
    "create_test_dataset",
    "get_test_data_factory"
]