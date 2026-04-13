"""
BDD集成模块测试
测试BDD功能的核心组件和集成
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from src.phoenixframe.bdd import (
    BDDStepRegistry, BDDFeatureManager, BDDIntegration,
    StepDefinition, FeatureInfo, get_bdd_integration,
    setup_bdd, phoenix_given, phoenix_when, phoenix_then
)


class TestBDDStepRegistry:
    """测试BDD步骤注册表"""
    
    def test_step_registry_initialization(self):
        """测试步骤注册表初始化"""
        registry = BDDStepRegistry()
        
        assert "given" in registry.steps
        assert "when" in registry.steps
        assert "then" in registry.steps
        assert all(isinstance(steps, list) for steps in registry.steps.values())
    
    def test_register_step(self):
        """测试步骤注册功能"""
        registry = BDDStepRegistry()
        
        def test_function():
            pass
        
        registry.register_step(
            step_type="given",
            pattern="I have a test precondition",
            function=test_function,
            description="Test precondition step"
        )
        
        assert len(registry.steps["given"]) == 1
        step_def = registry.steps["given"][0]
        assert step_def.step_type == "given"
        assert step_def.pattern == "I have a test precondition"
        assert step_def.function == test_function
        assert step_def.description == "Test precondition step"
    
    def test_find_step(self):
        """测试步骤查找功能"""
        registry = BDDStepRegistry()
        
        def test_function():
            pass
        
        registry.register_step("given", r"I have (\d+) items", test_function)
        
        # 测试匹配
        found_step = registry.find_step("given", "I have 5 items")
        assert found_step is not None
        assert found_step.function == test_function
        
        # 测试不匹配
        not_found = registry.find_step("given", "I have no items")
        assert not_found is None
    
    def test_get_steps(self):
        """测试获取步骤定义"""
        registry = BDDStepRegistry()
        
        def test_function():
            pass
        
        registry.register_step("given", "test pattern", test_function)
        
        # 获取特定类型步骤
        given_steps = registry.get_steps("given")
        assert "given" in given_steps
        assert len(given_steps["given"]) == 1
        
        # 获取所有步骤
        all_steps = registry.get_steps()
        assert len(all_steps) == 3
        assert "given" in all_steps
        assert "when" in all_steps
        assert "then" in all_steps


class TestBDDFeatureManager:
    """测试Feature文件管理器"""
    
    def test_feature_manager_initialization(self):
        """测试Feature管理器初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BDDFeatureManager(temp_dir)
            assert manager.features_dir == Path(temp_dir)
    
    def test_create_feature_template(self):
        """测试Feature模板创建"""
        manager = BDDFeatureManager()
        
        template = manager.create_feature_template(
            feature_name="User Login",
            scenarios=["Successful login", "Failed login"],
            description="User authentication feature",
            tags=["auth", "critical"]
        )
        
        assert "Feature: User Login" in template
        assert "User authentication feature" in template
        assert "Scenario: Successful login" in template
        assert "Scenario: Failed login" in template
        assert "@auth @critical" in template
        assert "Given I have a precondition" in template
        assert "When I perform an action" in template
        assert "Then I should see the expected result" in template
    
    def test_simple_parse_feature(self):
        """测试简单Feature文件解析"""
        manager = BDDFeatureManager()
        
        feature_content = """@auth @critical
Feature: User Login
  User authentication functionality
  
  Scenario: Successful login
    Given I have valid credentials
    When I submit login form
    Then I should be redirected to dashboard
    
  Scenario: Failed login
    Given I have invalid credentials
    When I submit login form
    Then I should see error message
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write(feature_content)
            feature_file = Path(f.name)
        
        try:
            feature_info = manager._simple_parse_feature(feature_file)
            
            assert feature_info.name == "User Login"
            assert "User authentication functionality" in feature_info.description
            assert len(feature_info.scenarios) == 2
            assert "Successful login" in feature_info.scenarios
            assert "Failed login" in feature_info.scenarios
            assert "auth" in feature_info.tags
            assert "critical" in feature_info.tags
            
        finally:
            feature_file.unlink()
    
    def test_discover_features_empty_directory(self):
        """测试空目录的Feature发现"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BDDFeatureManager(temp_dir)
            features = manager.discover_features()
            assert features == []
    
    def test_discover_features_with_files(self):
        """测试有Feature文件的目录发现"""
        with tempfile.TemporaryDirectory() as temp_dir:
            features_dir = Path(temp_dir)
            
            # 创建测试Feature文件
            feature_file = features_dir / "test.feature"
            feature_file.write_text("""
Feature: Test Feature
  Test description
  
  Scenario: Test scenario
    Given a precondition
    When an action
    Then a result
""")
            
            manager = BDDFeatureManager(temp_dir)
            features = manager.discover_features()
            
            assert len(features) == 1
            assert features[0].name == "Test Feature"


class TestBDDIntegration:
    """测试BDD集成主类"""
    
    def test_bdd_integration_initialization(self):
        """测试BDD集成初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            features_dir = str(Path(temp_dir) / "features")
            steps_dir = str(Path(temp_dir) / "steps")
            
            integration = BDDIntegration(features_dir, steps_dir)
            
            assert integration.features_dir == Path(features_dir)
            assert integration.steps_dir == Path(steps_dir)
            assert isinstance(integration.step_registry, BDDStepRegistry)
            assert isinstance(integration.feature_manager, BDDFeatureManager)
            
            # 检查目录是否被创建
            assert Path(features_dir).exists()
            assert Path(steps_dir).exists()
    
    def test_create_feature_file(self):
        """测试Feature文件创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            integration = BDDIntegration(
                features_dir=str(Path(temp_dir) / "features"),
                steps_dir=str(Path(temp_dir) / "steps")
            )
            
            feature_path = integration.create_feature_file(
                name="Test Feature",
                scenarios=["Test scenario"],
                description="Test description",
                tags=["test"]
            )
            
            assert Path(feature_path).exists()
            content = Path(feature_path).read_text()
            assert "Feature: Test Feature" in content
            assert "Test description" in content
            assert "Scenario: Test scenario" in content
            assert "@test" in content
    
    @patch('src.phoenixframe.bdd.BDD_AVAILABLE', False)
    def test_setup_bdd_environment_without_pytest_bdd(self):
        """测试没有pytest-bdd时的BDD环境设置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            integration = BDDIntegration(
                features_dir=str(Path(temp_dir) / "features"),
                steps_dir=str(Path(temp_dir) / "steps")
            )
            
            # 应该不抛出异常
            integration.setup_bdd_environment()
    
    def test_get_step_coverage_empty(self):
        """测试空项目的步骤覆盖率"""
        with tempfile.TemporaryDirectory() as temp_dir:
            integration = BDDIntegration(
                features_dir=str(Path(temp_dir) / "features"),
                steps_dir=str(Path(temp_dir) / "steps")
            )
            
            coverage = integration.get_step_coverage()
            
            assert coverage["total_steps"] == 0
            assert coverage["implemented_steps"] == 0
            assert coverage["coverage_percent"] == 0
            assert coverage["missing_steps"] == []
            assert coverage["features_count"] == 0


class TestBDDDecorators:
    """测试BDD装饰器"""
    
    def test_phoenix_given_decorator(self):
        """测试phoenix_given装饰器"""
        @phoenix_given("I have a test condition")
        def test_step():
            pass
        
        # 检查步骤是否被注册
        from src.phoenixframe.bdd import step_registry
        given_steps = step_registry.get_steps("given")["given"]
        
        # 找到我们注册的步骤
        matching_steps = [step for step in given_steps 
                         if step.pattern == "I have a test condition"]
        assert len(matching_steps) >= 1
        assert matching_steps[0].function == test_step
    
    def test_phoenix_when_decorator(self):
        """测试phoenix_when装饰器"""
        @phoenix_when("I perform an action")
        def test_action():
            pass
        
        from src.phoenixframe.bdd import step_registry
        when_steps = step_registry.get_steps("when")["when"]
        
        matching_steps = [step for step in when_steps 
                         if step.pattern == "I perform an action"]
        assert len(matching_steps) >= 1
        assert matching_steps[0].function == test_action
    
    def test_phoenix_then_decorator(self):
        """测试phoenix_then装饰器"""
        @phoenix_then("I should see a result")
        def test_result():
            pass
        
        from src.phoenixframe.bdd import step_registry
        then_steps = step_registry.get_steps("then")["then"]
        
        matching_steps = [step for step in then_steps 
                         if step.pattern == "I should see a result"]
        assert len(matching_steps) >= 1
        assert matching_steps[0].function == test_result


class TestBDDGlobalFunctions:
    """测试BDD全局函数"""
    
    def test_get_bdd_integration_singleton(self):
        """测试BDD集成单例模式"""
        integration1 = get_bdd_integration()
        integration2 = get_bdd_integration()
        
        assert integration1 is integration2
        assert isinstance(integration1, BDDIntegration)
    
    def test_setup_bdd_function(self):
        """测试setup_bdd函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            features_dir = str(Path(temp_dir) / "features")
            steps_dir = str(Path(temp_dir) / "steps")
            
            integration = setup_bdd(features_dir, steps_dir)
            
            assert isinstance(integration, BDDIntegration)
            assert integration.features_dir == Path(features_dir)
            assert integration.steps_dir == Path(steps_dir)


class TestStepDefinitionDataclass:
    """测试步骤定义数据类"""
    
    def test_step_definition_creation(self):
        """测试步骤定义创建"""
        def test_func():
            pass
        
        step_def = StepDefinition(
            step_type="given",
            pattern="I have a condition",
            function=test_func,
            description="Test step",
            examples=["example1", "example2"]
        )
        
        assert step_def.step_type == "given"
        assert step_def.pattern == "I have a condition"
        assert step_def.function == test_func
        assert step_def.description == "Test step"
        assert step_def.examples == ["example1", "example2"]
    
    def test_step_definition_default_examples(self):
        """测试步骤定义默认示例"""
        def test_func():
            pass
        
        step_def = StepDefinition(
            step_type="when",
            pattern="I do something",
            function=test_func
        )
        
        assert step_def.examples == []


class TestFeatureInfoDataclass:
    """测试Feature信息数据类"""
    
    def test_feature_info_creation(self):
        """测试Feature信息创建"""
        feature_info = FeatureInfo(
            name="Test Feature",
            description="Test description",
            file_path="/path/to/feature.feature",
            scenarios=["Scenario 1", "Scenario 2"],
            tags=["tag1", "tag2"]
        )
        
        assert feature_info.name == "Test Feature"
        assert feature_info.description == "Test description"
        assert feature_info.file_path == "/path/to/feature.feature"
        assert feature_info.scenarios == ["Scenario 1", "Scenario 2"]
        assert feature_info.tags == ["tag1", "tag2"]
    
    def test_feature_info_default_tags(self):
        """测试Feature信息默认标签"""
        feature_info = FeatureInfo(
            name="Test Feature",
            description="Test description",
            file_path="/path/to/feature.feature",
            scenarios=["Scenario 1"]
        )
        
        assert feature_info.tags == []


@pytest.fixture
def temp_bdd_environment():
    """临时BDD环境fixture"""
    with tempfile.TemporaryDirectory() as temp_dir:
        features_dir = str(Path(temp_dir) / "features")
        steps_dir = str(Path(temp_dir) / "steps")
        
        integration = BDDIntegration(features_dir, steps_dir)
        
        # 创建示例Feature文件
        feature_content = """@test
Feature: Sample Feature
  Sample feature for testing
  
  Scenario: Sample scenario
    Given I have a sample condition
    When I perform a sample action
    Then I should see a sample result
"""
        feature_file = Path(features_dir) / "sample.feature"
        feature_file.write_text(feature_content)
        
        yield integration


class TestBDDIntegrationWithFixture:
    """使用fixture的BDD集成测试"""
    
    def test_generate_step_definitions_for_feature(self, temp_bdd_environment):
        """测试为Feature生成步骤定义"""
        integration = temp_bdd_environment
        feature_file = str(integration.features_dir / "sample.feature")
        
        with patch('src.phoenixframe.bdd.BDD_AVAILABLE', True):
            with patch('src.phoenixframe.bdd.Feature') as mock_feature:
                # Mock Feature对象
                mock_scenario = Mock()
                mock_scenario.name = "Sample scenario"
                mock_scenario.steps = []
                
                mock_feature_obj = Mock()
                mock_feature_obj.scenarios = [mock_scenario]
                mock_feature.from_file.return_value = mock_feature_obj
                
                # 测试生成步骤定义
                step_code = integration.generate_step_definitions_for_feature(feature_file)
                
                assert "Auto-generated BDD step definitions" in step_code
                assert "import pytest" in step_code
                assert "from pytest_bdd import given, when, then, scenario" in step_code
                assert "@scenario" in step_code
    
    def test_discover_features_with_fixture(self, temp_bdd_environment):
        """测试使用fixture发现Features"""
        integration = temp_bdd_environment
        
        features = integration.feature_manager.discover_features()
        
        assert len(features) == 1
        assert features[0].name == "Sample Feature"
        assert "Sample feature for testing" in features[0].description
        assert "Sample scenario" in features[0].scenarios
        assert "test" in features[0].tags