"""
测试数据管理综合示例
演示PhoenixFrame的测试数据管理功能
"""
import sys
from pathlib import Path

# 添加src路径以便导入模块
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.phoenixframe.data import (
    TestDataset, DataMask,
    get_data_repository, get_data_masker, get_fake_generator
)
from src.phoenixframe.data.factories import (
    create_test_dataset, UserBuilder, ProductBuilder, OrderBuilder
)
from src.phoenixframe.data.database import (
    get_database_manager, get_setup_manager,
    DatabaseConnection, TableSetup, DataSetupPlan
)
from src.phoenixframe.data.version import get_version_control
from src.phoenixframe.data.dependencies import (
    get_dependency_manager, DataDependency, DependencyType
)
from src.phoenixframe.observability.logger import get_logger

# 设置日志
logger = get_logger("data_management_example")


def demo_data_factories():
    """演示数据工厂和构建器"""
    logger.info("=== Data Factories and Builders Demo ===")
    
    # 使用构建器创建单个用户
    user = UserBuilder().with_random_data().with_admin_role().build()
    logger.info(f"Created admin user: {user.username} ({user.email})")
    
    # 批量创建产品
    products_dataset = create_test_dataset("electronics", "product", 5, 
                                          electronics=True, high_price=True)
    logger.info(f"Created {len(products_dataset.data)} high-end electronics products")
    
    # 创建订单数据
    order = (OrderBuilder()
             .with_random_customer()
             .add_random_items(3)
             .with_completed_status()
             .build())
    logger.info(f"Created order {order.order_number} with total ${order.total_amount:.2f}")
    
    return products_dataset


def demo_data_repository():
    """演示数据仓库功能"""
    logger.info("=== Data Repository Demo ===")
    
    repository = get_data_repository()
    
    # 创建用户数据集
    users_dataset = create_test_dataset("test_users", "user", 10)
    dataset_id = repository.save_dataset(users_dataset)
    logger.info(f"Saved users dataset: {dataset_id}")
    
    # 列出所有数据集
    datasets = repository.list_datasets()
    logger.info(f"Total datasets in repository: {len(datasets)}")
    
    # 搜索数据集
    search_results = repository.search_datasets("user")
    logger.info(f"Found {len(search_results)} datasets matching 'user'")
    
    # 加载数据集
    loaded_dataset = repository.load_dataset(dataset_id)
    logger.info(f"Loaded dataset: {loaded_dataset.name} with {len(loaded_dataset.data)} records")
    
    return dataset_id


def demo_data_masking():
    """演示数据脱敏功能"""
    logger.info("=== Data Masking Demo ===")
    
    repository = get_data_repository()
    masker = get_data_masker()
    
    # 创建包含敏感信息的数据集
    users_dataset = create_test_dataset("sensitive_users", "user", 5)
    dataset_id = repository.save_dataset(users_dataset)
    
    # 应用脱敏
    masks = [
        masker.default_masks["email"],
        masker.default_masks["phone"]
    ]
    
    masked_dataset = masker.mask_dataset(users_dataset, masks)
    masked_id = repository.save_dataset(masked_dataset)
    
    logger.info(f"Original dataset: {dataset_id}")
    logger.info(f"Masked dataset: {masked_id}")
    
    # 比较原始和脱敏后的数据
    if users_dataset.data and masked_dataset.data:
        original_user = users_dataset.data[0]
        masked_user = masked_dataset.data[0]
        
        logger.info(f"Original email: {original_user.get('email', 'N/A')}")
        logger.info(f"Masked email: {masked_user.get('email', 'N/A')}")
        logger.info(f"Original phone: {original_user.get('phone', 'N/A')}")
        logger.info(f"Masked phone: {masked_user.get('phone', 'N/A')}")
    
    return masked_id


def demo_version_control():
    """演示版本控制功能"""
    logger.info("=== Version Control Demo ===")
    
    repository = get_data_repository()
    vc = get_version_control()
    
    # 创建初始数据集
    dataset = create_test_dataset("versioned_products", "product", 3)
    dataset_id = repository.save_dataset(dataset)
    
    # 提交初始版本
    version1 = vc.commit(dataset, "Initial product dataset", "demo_user")
    logger.info(f"Committed version 1: {version1}")
    
    # 修改数据集并提交新版本
    dataset.data.append({
        "id": "product_4",
        "name": "New Product",
        "price": 199.99,
        "category": "electronics"
    })
    
    version2 = vc.commit(dataset, "Added new product", "demo_user")
    logger.info(f"Committed version 2: {version2}")
    
    # 查看版本历史
    history = vc.get_version_history("versioned_products")
    logger.info(f"Version history: {len(history)} versions")
    
    for version in history:
        logger.info(f"  {version.version}: {version.message} ({version.record_count} records)")
    
    # 比较版本
    comparison = vc.compare_versions("versioned_products", version1, version2)
    logger.info(f"Version comparison: {comparison['record_count_diff']} records added")
    
    return version2


def demo_dependency_management():
    """演示依赖关系管理"""
    logger.info("=== Dependency Management Demo ===")
    
    repository = get_data_repository()
    dependency_manager = get_dependency_manager()
    
    # 创建相关数据集
    users_dataset = create_test_dataset("users", "user", 5)
    orders_dataset = create_test_dataset("orders", "order", 10)
    
    repository.save_dataset(users_dataset)
    repository.save_dataset(orders_dataset)
    
    # 添加依赖关系：订单依赖于用户
    dependency = DataDependency(
        source_dataset="users",
        target_dataset="orders",
        dependency_type=DependencyType.REFERENCE,
        description="Orders reference users via customer_id",
        mapping={"id": "customer_id"}
    )
    
    dependency_manager.add_dependency(dependency)
    logger.info("Added dependency: users -> orders")
    
    # 获取构建顺序
    build_order = dependency_manager.get_build_order(["users", "orders"])
    logger.info(f"Build order: {' -> '.join(build_order)}")
    
    # 影响分析
    impact = dependency_manager.get_impact_analysis("users")
    logger.info(f"Impact analysis for users: {impact['impact_level']} impact")
    logger.info(f"Affected datasets: {impact['affected_datasets']}")
    
    # 验证依赖关系
    validation_results = dependency_manager.validate_dependencies(repository)
    if validation_results:
        logger.warning(f"Dependency validation found {len(validation_results)} issues")
    else:
        logger.info("All dependencies are valid")
    
    return dependency


def demo_fake_data_generation():
    """演示假数据生成功能"""
    logger.info("=== Fake Data Generation Demo ===")
    
    generator = get_fake_generator()
    
    if not generator.fake:
        logger.warning("Faker not available, skipping fake data demo")
        return
    
    # 生成用户数据
    users = generator.generate_user_data(3)
    logger.info(f"Generated {len(users)} fake users")
    
    # 生成订单数据
    orders = generator.generate_order_data(2)
    logger.info(f"Generated {len(orders)} fake orders")
    
    # 根据自定义模式生成数据
    custom_schema = {
        "employee_id": {"type": "uuid"},
        "name": {"type": "string"},
        "salary": {"type": "integer", "min": 30000, "max": 150000},
        "department": {"type": "string"},
        "hire_date": {"type": "date"}
    }
    
    employees = generator.generate_custom_data(custom_schema, 3)
    logger.info(f"Generated {len(employees)} employees with custom schema")
    
    # 创建并保存假数据集
    fake_dataset = TestDataset(
        name="fake_employees",
        description="Fake employee data for testing",
        data=employees,
        tags=["fake", "employees", "testing"]
    )
    
    repository = get_data_repository()
    dataset_id = repository.save_dataset(fake_dataset)
    logger.info(f"Saved fake dataset: {dataset_id}")
    
    return dataset_id


def demo_database_setup():
    """演示数据库设置功能"""
    logger.info("=== Database Setup Demo ===")
    
    try:
        db_manager = get_database_manager()
        setup_manager = get_setup_manager()
        
        # 创建SQLite连接
        connection = DatabaseConnection(
            name="test_db",
            connection_string="sqlite:///test_data.db",
            driver="sqlite"
        )
        
        db_manager.add_connection(connection)
        logger.info("Added SQLite database connection")
        
        # 创建表设置
        users_table = TableSetup(
            table_name="test_users",
            schema={
                "id": {"type": "string", "required": True},
                "username": {"type": "string", "required": True},
                "email": {"type": "string", "required": True},
                "created_at": {"type": "datetime", "default": "CURRENT_TIMESTAMP"}
            },
            data=[
                {"id": "user1", "username": "testuser1", "email": "test1@example.com"},
                {"id": "user2", "username": "testuser2", "email": "test2@example.com"}
            ],
            primary_key="id",
            indexes=["username", "email"]
        )
        
        # 创建表
        db_manager.create_table("test_db", users_table)
        logger.info("Created test_users table")
        
        # 插入数据
        inserted_count = db_manager.insert_data("test_db", "test_users", users_table.data)
        logger.info(f"Inserted {inserted_count} records")
        
        # 查询数据
        results = db_manager.execute_sql("test_db", "SELECT COUNT(*) FROM test_users")
        logger.info(f"Query result: {results}")
        
        # 清理
        db_manager.clear_table("test_db", "test_users")
        db_manager.drop_table("test_db", "test_users")
        logger.info("Cleaned up test table")
        
    except Exception as e:
        logger.error(f"Database demo failed: {e}")
        logger.info("Database functionality may require additional dependencies")


def main():
    """主演示函数"""
    logger.info("PhoenixFrame Test Data Management Demo")
    logger.info("=" * 50)
    
    try:
        # 演示各个功能模块
        demo_data_factories()
        print()
        
        dataset_id = demo_data_repository()
        print()
        
        masked_id = demo_data_masking()
        print()
        
        version = demo_version_control()
        print()
        
        dependency = demo_dependency_management()
        print()
        
        fake_dataset_id = demo_fake_data_generation()
        print()
        
        demo_database_setup()
        print()
        
        logger.info("=== Demo Summary ===")
        logger.info("✅ Data factories and builders")
        logger.info("✅ Data repository management") 
        logger.info("✅ Data masking and privacy protection")
        logger.info("✅ Version control and history tracking")
        logger.info("✅ Dependency relationship management")
        logger.info("✅ Fake data generation")
        logger.info("✅ Database setup and management")
        
        logger.info("\n🎉 All test data management features demonstrated successfully!")
        
        # CLI使用示例
        logger.info("\n📋 CLI Usage Examples:")
        logger.info("# Create a dataset")
        logger.info("phoenix data dataset create my_users --data-type user --count 100")
        logger.info("\n# List datasets")
        logger.info("phoenix data dataset list")
        logger.info("\n# Apply data masking")
        logger.info("phoenix data mask apply my_users_v1.0 --email --phone")
        logger.info("\n# Commit a version")
        logger.info("phoenix data version commit my_users_v1.0 -m 'Initial user dataset'")
        logger.info("\n# Add dependency")
        logger.info("phoenix data dependency add users orders --type reference")
        logger.info("\n# Show dependency tree")
        logger.info("phoenix data dependency tree orders")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()