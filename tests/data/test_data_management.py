"""测试数据管理功能的单元测试"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.phoenixframe.data import (
    TestDataset, DataMask, DataSource,
    get_data_repository, get_data_masker, get_fake_generator
)
from src.phoenixframe.data.factories import (
    UserBuilder, ProductBuilder, OrderBuilder,
    create_test_dataset, get_test_data_factory
)
from src.phoenixframe.data.database import (
    DatabaseConnection, TableSetup, 
    get_database_manager, get_setup_manager
)
from src.phoenixframe.data.version import get_version_control, ChangeType
from src.phoenixframe.data.dependencies import (
    get_dependency_manager, DataDependency, DependencyType,
    CircularDependencyError
)


class TestDataModels:
    """测试数据模型"""
    
    def test_test_dataset_creation(self):
        """测试数据集创建"""
        data = [{"id": 1, "name": "test"}]
        dataset = TestDataset(
            name="test_dataset",
            description="Test dataset",
            data=data
        )
        
        assert dataset.name == "test_dataset"
        assert dataset.description == "Test dataset"
        assert len(dataset.data) == 1
        assert dataset.schema is not None  # 应该自动推断模式
        assert "id" in dataset.schema
        assert "name" in dataset.schema
    
    def test_data_mask_creation(self):
        """测试数据脱敏配置创建"""
        mask = DataMask("email", "partial", {"pattern": "***@***.***"})
        
        assert mask.field == "email"
        assert mask.mask_type == "partial"
        assert mask.options["pattern"] == "***@***.***"
    
    def test_data_source_creation(self):
        """测试数据源配置创建"""
        source = DataSource(
            name="test_source",
            type="file",
            location="/path/to/file.json",
            format="json"
        )
        
        assert source.name == "test_source"
        assert source.type == "file"
        assert source.location == "/path/to/file.json"
        assert source.format == "json"


class TestDataBuilders:
    """测试数据构建器"""
    
    def test_user_builder(self):
        """测试用户构建器"""
        user = (UserBuilder()
                .with_field("username", "testuser")
                .with_field("email", "test@example.com")
                .with_admin_role()
                .build())
        
        assert user.username == "admin_testuser"
        assert user.email == "admin.test@example.com"
        assert user.is_active is True
    
    def test_product_builder(self):
        """测试产品构建器"""
        product = (ProductBuilder()
                   .with_field("name", "Test Product")
                   .with_field("price", 99.99)
                   .with_electronics_category()
                   .with_stock(10)
                   .build())
        
        assert product.name == "Test Product"
        assert product.price == 99.99
        assert product.category == "electronics"
        assert product.stock_quantity == 10
    
    def test_order_builder(self):
        """测试订单构建器"""
        order = (OrderBuilder()
                 .with_field("customer_id", "cust123")
                 .add_item("prod1", 2, 50.0, "Product 1")
                 .add_item("prod2", 1, 100.0, "Product 2")
                 .with_completed_status()
                 .build())
        
        assert order.customer_id == "cust123"
        assert order.status == "completed"
        assert len(order.items) == 2
        assert order.total_amount == 200.0
    
    def test_data_factory(self):
        """测试数据工厂"""
        factory = get_test_data_factory()
        
        # 测试创建用户数据
        user_data = factory.create("user", username="factoryuser")
        assert user_data["username"] == "factoryuser"
        
        # 测试批量创建
        users_batch = factory.create("users_batch", count=3)
        assert len(users_batch) == 3


class TestDataRepository:
    """测试数据仓库"""
    
    def test_save_and_load_dataset(self):
        """测试保存和加载数据集"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = get_data_repository(temp_dir)
            
            # 创建测试数据集
            dataset = TestDataset(
                name="test_save_load",
                description="Test save and load",
                data=[{"id": 1, "value": "test"}],
                tags=["test"]
            )
            
            # 保存数据集
            dataset_id = repository.save_dataset(dataset)
            assert dataset_id is not None
            
            # 加载数据集
            loaded_dataset = repository.load_dataset(dataset_id)
            assert loaded_dataset.name == dataset.name
            assert loaded_dataset.description == dataset.description
            assert len(loaded_dataset.data) == len(dataset.data)
    
    def test_list_and_search_datasets(self):
        """测试列出和搜索数据集"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = get_data_repository(temp_dir)
            
            # 创建多个数据集
            for i in range(3):
                dataset = TestDataset(
                    name=f"test_dataset_{i}",
                    description=f"Test dataset {i}",
                    data=[{"id": i}],
                    tags=["test", f"group_{i % 2}"]
                )
                repository.save_dataset(dataset)
            
            # 列出所有数据集
            datasets = repository.list_datasets()
            assert len(datasets) == 3
            
            # 按标签过滤
            group_0_datasets = repository.list_datasets(tags=["group_0"])
            assert len(group_0_datasets) == 2
            
            # 搜索数据集
            search_results = repository.search_datasets("test")
            assert len(search_results) >= 3
    
    def test_delete_dataset(self):
        """测试删除数据集"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = get_data_repository(temp_dir)
            
            # 创建和保存数据集
            dataset = TestDataset("test_delete", "Test delete", [{"id": 1}])
            dataset_id = repository.save_dataset(dataset)
            
            # 确认存在
            assert repository.load_dataset(dataset_id) is not None
            
            # 删除数据集
            assert repository.delete_dataset(dataset_id) is True
            
            # 确认不存在
            with pytest.raises(ValueError):
                repository.load_dataset(dataset_id)


class TestDataMasking:
    """测试数据脱敏"""
    
    def test_email_masking(self):
        """测试邮箱脱敏"""
        masker = get_data_masker()
        
        # 测试邮箱脱敏
        email = "user@example.com"
        masked_email = masker._mask_email(email)
        
        assert masked_email != email
        assert "@" in masked_email
        assert "***" in masked_email
    
    def test_phone_masking(self):
        """测试电话脱敏"""
        masker = get_data_masker()
        
        phone = "123-456-7890"
        masked_phone = masker._mask_phone(phone)
        
        assert masked_phone != phone
        assert "***" in masked_phone
    
    def test_dataset_masking(self):
        """测试数据集脱敏"""
        masker = get_data_masker()
        
        # 创建包含敏感数据的数据集
        dataset = TestDataset(
            name="sensitive_data",
            description="Data with sensitive info",
            data=[
                {"id": 1, "email": "user1@example.com", "phone": "123-456-7890"},
                {"id": 2, "email": "user2@example.com", "phone": "098-765-4321"}
            ]
        )
        
        # 应用脱敏
        masks = [
            DataMask("email", "partial"),
            DataMask("phone", "partial")
        ]
        
        masked_dataset = masker.mask_dataset(dataset, masks)
        
        assert masked_dataset.name == "sensitive_data_masked"
        assert len(masked_dataset.data) == 2
        
        # 检查脱敏效果
        for original, masked in zip(dataset.data, masked_dataset.data):
            assert original["email"] != masked["email"]
            assert original["phone"] != masked["phone"]
            assert original["id"] == masked["id"]  # ID不应该被脱敏


class TestVersionControl:
    """测试版本控制"""
    
    def test_commit_and_checkout(self):
        """测试提交和检出版本"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vc = get_version_control(temp_dir)
            
            # 创建数据集
            dataset = TestDataset(
                name="versioned_data",
                description="Test versioning",
                data=[{"id": 1, "value": "v1"}]
            )
            
            # 提交版本
            version1 = vc.commit(dataset, "Initial version", "test_user")
            assert version1 is not None
            
            # 修改数据集
            dataset.data.append({"id": 2, "value": "v2"})
            version2 = vc.commit(dataset, "Added record", "test_user")
            assert version2 != version1
            
            # 检出旧版本
            old_dataset = vc.checkout("versioned_data", version1)
            assert len(old_dataset.data) == 1
            
            # 检出新版本
            new_dataset = vc.checkout("versioned_data", version2)
            assert len(new_dataset.data) == 2
    
    def test_version_history(self):
        """测试版本历史"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vc = get_version_control(temp_dir)
            
            dataset = TestDataset("history_test", "Test history", [{"id": 1}])
            
            # 创建多个版本
            versions = []
            for i in range(3):
                dataset.data.append({"id": i + 2})
                version = vc.commit(dataset, f"Version {i + 1}", "test_user")
                versions.append(version)
            
            # 获取版本历史
            history = vc.get_version_history("history_test")
            assert len(history) >= 3
            
            # 检查版本顺序（应该按时间倒序）
            timestamps = [v.timestamp for v in history]
            assert timestamps == sorted(timestamps, reverse=True)
    
    def test_branch_operations(self):
        """测试分支操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vc = get_version_control(temp_dir)
            
            # 创建初始数据
            dataset = TestDataset("branch_test", "Test branches", [{"id": 1}])
            main_version = vc.commit(dataset, "Main version", "test_user")
            
            # 创建分支
            branch = vc.create_branch("feature_branch", main_version, "Feature branch", "test_user")
            assert branch.name == "feature_branch"
            
            # 切换到分支
            vc.switch_branch("feature_branch")
            assert vc.get_current_branch() == "feature_branch"
            
            # 在分支上提交
            dataset.data.append({"id": 2})
            branch_version = vc.commit(dataset, "Feature update", "test_user")
            
            # 合并分支
            merged_versions = vc.merge_branch("feature_branch", "main", "Merge feature", "test_user")
            assert len(merged_versions) >= 0


class TestDependencyManagement:
    """测试依赖关系管理"""
    
    def test_add_and_remove_dependency(self):
        """测试添加和删除依赖"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = get_dependency_manager(str(Path(temp_dir) / "deps.json"))
            
            # 添加依赖
            dependency = DataDependency(
                source_dataset="users",
                target_dataset="orders",
                dependency_type=DependencyType.REFERENCE,
                description="Orders reference users"
            )
            
            manager.add_dependency(dependency)
            
            # 检查依赖
            dependencies = manager.get_dependencies("orders")
            assert len(dependencies) == 1
            assert dependencies[0].source_dataset == "users"
            
            # 删除依赖
            removed = manager.remove_dependency("users", "orders")
            assert removed is True
            
            # 确认删除
            dependencies = manager.get_dependencies("orders")
            assert len(dependencies) == 0
    
    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = get_dependency_manager(str(Path(temp_dir) / "deps.json"))
            
            # 添加依赖：A -> B
            dep1 = DataDependency("A", "B", DependencyType.REQUIRED)
            manager.add_dependency(dep1)
            
            # 添加依赖：B -> C  
            dep2 = DataDependency("B", "C", DependencyType.REQUIRED)
            manager.add_dependency(dep2)
            
            # 尝试添加循环依赖：C -> A
            dep3 = DataDependency("C", "A", DependencyType.REQUIRED)
            
            with pytest.raises(CircularDependencyError):
                manager.add_dependency(dep3)
    
    def test_build_order(self):
        """测试构建顺序"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = get_dependency_manager(str(Path(temp_dir) / "deps.json"))
            
            # 创建依赖链：A -> B -> C
            manager.add_dependency(DataDependency("A", "B", DependencyType.REQUIRED))
            manager.add_dependency(DataDependency("B", "C", DependencyType.REQUIRED))
            
            # 获取构建顺序
            build_order = manager.get_build_order(["A", "B", "C"])
            
            # A应该在B之前，B应该在C之前
            assert build_order.index("A") < build_order.index("B")
            assert build_order.index("B") < build_order.index("C")
    
    def test_impact_analysis(self):
        """测试影响分析"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = get_dependency_manager(str(Path(temp_dir) / "deps.json"))
            
            # 创建依赖：users -> orders -> shipping
            manager.add_dependency(DataDependency("users", "orders", DependencyType.REFERENCE))
            manager.add_dependency(DataDependency("orders", "shipping", DependencyType.REFERENCE))
            
            # 分析users的影响
            impact = manager.get_impact_analysis("users")
            
            assert impact["dataset"] == "users"
            assert impact["direct_dependents"] == 1
            assert "orders" in impact["affected_datasets"]
            assert "shipping" in impact["affected_datasets"]


class TestFakeDataGeneration:
    """测试假数据生成"""
    
    def test_fake_data_availability(self):
        """测试假数据生成器可用性"""
        generator = get_fake_generator()
        
        # 检查是否可用
        from src.phoenixframe.data import FAKER_AVAILABLE
        
        if FAKER_AVAILABLE:
            assert generator.fake is not None
        else:
            assert generator.fake is None
    
    @pytest.mark.skipif(not pytest.importorskip("faker", reason="Faker not available"), reason="Faker required")
    def test_user_data_generation(self):
        """测试用户数据生成"""
        generator = get_fake_generator()
        
        users = generator.generate_user_data(5)
        assert len(users) == 5
        
        for user in users:
            assert "id" in user
            assert "username" in user
            assert "email" in user
            assert "@" in user["email"]
    
    @pytest.mark.skipif(not pytest.importorskip("faker", reason="Faker not available"), reason="Faker required")
    def test_custom_schema_generation(self):
        """测试自定义模式数据生成"""
        generator = get_fake_generator()
        
        schema = {
            "employee_id": {"type": "uuid"},
            "salary": {"type": "integer", "min": 30000, "max": 100000},
            "active": {"type": "boolean"}
        }
        
        employees = generator.generate_custom_data(schema, 3)
        assert len(employees) == 3
        
        for employee in employees:
            assert "employee_id" in employee
            assert "salary" in employee
            assert "active" in employee
            assert 30000 <= employee["salary"] <= 100000
            assert isinstance(employee["active"], bool)


class TestDatabaseManagement:
    """测试数据库管理"""
    
    def test_database_connection(self):
        """测试数据库连接"""
        manager = get_database_manager()
        
        # 添加SQLite连接
        connection = DatabaseConnection(
            name="test_conn",
            connection_string="sqlite:///:memory:",
            driver="sqlite"
        )
        
        manager.add_connection(connection)
        
        # 测试连接是否工作
        assert "test_conn" in manager._connections
    
    def test_table_operations(self):
        """测试表操作"""
        manager = get_database_manager()
        
        # 添加内存数据库连接
        connection = DatabaseConnection(
            name="memory_db",
            connection_string="sqlite:///:memory:",
            driver="sqlite"
        )
        
        manager.add_connection(connection)
        
        # 创建表
        table_setup = TableSetup(
            table_name="test_table",
            schema={
                "id": {"type": "string", "required": True},
                "name": {"type": "string", "required": True},
                "value": {"type": "integer", "default": 0}
            },
            primary_key="id"
        )
        
        manager.create_table("memory_db", table_setup)
        
        # 检查表是否存在
        assert manager.table_exists("memory_db", "test_table")
        
        # 插入数据
        test_data = [
            {"id": "1", "name": "Test 1", "value": 100},
            {"id": "2", "name": "Test 2", "value": 200}
        ]
        
        inserted_count = manager.insert_data("memory_db", "test_table", test_data)
        assert inserted_count == 2
        
        # 查询数据
        results = manager.execute_sql("memory_db", "SELECT COUNT(*) FROM test_table")
        assert len(results) > 0
        
        # 清理表
        cleared_count = manager.clear_table("memory_db", "test_table")
        assert cleared_count == 2
        
        # 删除表
        manager.drop_table("memory_db", "test_table")
        assert not manager.table_exists("memory_db", "test_table")


@pytest.mark.integration
class TestDataManagementIntegration:
    """数据管理集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 初始化组件
            repository = get_data_repository(temp_dir)
            vc = get_version_control(str(Path(temp_dir) / "versions"))
            masker = get_data_masker()
            
            # 1. 创建数据集
            dataset = create_test_dataset("integration_test", "user", 5)
            dataset_id = repository.save_dataset(dataset)
            
            # 2. 提交版本
            version1 = vc.commit(dataset, "Initial version", "integration_test")
            
            # 3. 应用脱敏
            masks = [masker.default_masks["email"]]
            masked_dataset = masker.mask_dataset(dataset, masks)
            masked_id = repository.save_dataset(masked_dataset)
            
            # 4. 提交脱敏版本
            version2 = vc.commit(masked_dataset, "Masked version", "integration_test")
            
            # 5. 验证所有操作
            assert dataset_id != masked_id
            assert version1 != version2
            
            # 检查数据集列表
            datasets = repository.list_datasets()
            assert len(datasets) >= 2
            
            # 检查版本历史
            history = vc.get_version_history("integration_test")
            assert len(history) >= 1
            
            logger.info("Integration test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])