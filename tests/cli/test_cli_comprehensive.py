"""
CLI主要命令和功能的全面测试
扩展CLI测试覆盖率以达到80%+
"""
import pytest
import tempfile
import json
import yaml
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, Mock, MagicMock
from src.phoenixframe.cli import main as phoenix_cli


class TestCLIMainCommand:
    """测试CLI主命令和选项"""
    
    def test_cli_help(self):
        """测试CLI帮助命令"""
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, ['--help'])
        
        assert result.exit_code == 0
        assert "PhoenixFrame CLI" in result.output
        assert "企业级自动化测试框架" in result.output
    
    def test_cli_debug_option(self):
        """测试debug选项"""
        runner = CliRunner()
        with patch('src.phoenixframe.cli.setup_logging') as mock_setup_logging:
            result = runner.invoke(phoenix_cli, ['--debug', '--help'])
            
            mock_setup_logging.assert_called_once()
            args, kwargs = mock_setup_logging.call_args
            assert kwargs.get('level') == 'DEBUG' or args[0] == 'DEBUG'
    
    def test_cli_json_logs_option(self):
        """测试JSON日志选项"""
        runner = CliRunner()
        with patch('src.phoenixframe.cli.setup_logging') as mock_setup_logging:
            result = runner.invoke(phoenix_cli, ['--json-logs', '--help'])
            
            mock_setup_logging.assert_called_once()
            args, kwargs = mock_setup_logging.call_args
            assert kwargs.get('json_format') is True
    
    def test_cli_trace_console_option(self):
        """测试控制台追踪选项"""
        runner = CliRunner()
        with patch('src.phoenixframe.cli.setup_tracing') as mock_setup_tracing:
            result = runner.invoke(phoenix_cli, ['--trace-console', '--help'])
            
            mock_setup_tracing.assert_called_once()
            args, kwargs = mock_setup_tracing.call_args
            assert kwargs.get('console_export') is True
    
    def test_cli_metrics_console_option(self):
        """测试控制台度量选项"""
        runner = CliRunner()
        with patch('src.phoenixframe.cli.setup_metrics') as mock_setup_metrics:
            result = runner.invoke(phoenix_cli, ['--metrics-console', '--help'])
            
            mock_setup_metrics.assert_called_once()
            args, kwargs = mock_setup_metrics.call_args
            assert kwargs.get('console_export') is True


class TestCLIInitCommand:
    """测试项目初始化命令"""
    
    def test_init_new_project(self):
        """测试初始化新项目"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            
            result = runner.invoke(phoenix_cli, ['init', str(project_path)])
            
            assert result.exit_code == 0
            assert "Initializing project" in result.output
            assert "initialized successfully" in result.output
            
            # 检查目录结构
            assert project_path.exists()
            assert (project_path / "src" / "phoenixframe").exists()
            assert (project_path / "tests").exists()
            assert (project_path / "configs").exists()
            assert (project_path / "data").exists()
            assert (project_path / "docs").exists()
            assert (project_path / "templates").exists()
            
            # 检查文件
            assert (project_path / "configs" / "phoenix.yaml").exists()
            assert (project_path / "pyproject.toml").exists()
            assert (project_path / "README.md").exists()
            assert (project_path / ".gitignore").exists()
            assert (project_path / "tests" / "conftest.py").exists()
            assert (project_path / "tests" / "test_example.py").exists()
            assert (project_path / "requirements.txt").exists()
    
    def test_init_existing_non_empty_directory(self):
        """测试在非空目录初始化项目"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "existing_project"
            project_path.mkdir()
            (project_path / "existing_file.txt").write_text("existing content")
            
            result = runner.invoke(phoenix_cli, ['init', str(project_path)])
            
            assert result.exit_code == 0
            assert "already exists and is not empty" in result.output
    
    def test_init_project_config_content(self):
        """测试初始化项目配置内容"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "config_test_project"
            
            result = runner.invoke(phoenix_cli, ['init', str(project_path)])
            
            assert result.exit_code == 0
            
            # 检查phoenix.yaml配置
            config_file = project_path / "configs" / "phoenix.yaml"
            config = yaml.safe_load(config_file.read_text())
            
            assert config['app_name'] == project_path.name
            assert config['version'] == '1.0'
            assert 'environments' in config
            assert 'default' in config['environments']
            assert 'reporting' in config
            assert 'allure' in config['reporting']


class TestCLIRunCommand:
    """测试测试运行命令"""
    
    @patch('src.phoenixframe.cli.PhoenixRunner')
    def test_run_with_test_paths(self, mock_runner_class):
        """测试带测试路径的运行命令"""
        mock_runner = Mock()
        mock_runner.run_tests.return_value = {"pytest_exit_code": 0}
        mock_runner_class.return_value = mock_runner
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_example.py"
            test_file.write_text("def test_pass(): assert True")
            
            result = runner.invoke(phoenix_cli, ['run', str(test_file)])
            
            assert result.exit_code == 0
            mock_runner.run_tests.assert_called_once_with(
                test_paths=[str(test_file)], 
                pytest_extra_args=[]
            )
    
    @patch('src.phoenixframe.cli.PhoenixRunner')
    @patch('src.phoenixframe.cli.get_config')
    def test_run_with_environment(self, mock_get_config, mock_runner_class):
        """测试带环境选项的运行命令"""
        # Mock配置
        mock_config = Mock()
        mock_config.environments = {
            'dev': Mock(base_url='http://dev.example.com'),
            'prod': Mock(base_url='http://prod.example.com')
        }
        mock_get_config.return_value = mock_config
        
        # Mock运行器
        mock_runner = Mock()
        mock_runner.run_tests.return_value = {"pytest_exit_code": 0}
        mock_runner_class.return_value = mock_runner
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_example.py"
            test_file.write_text("def test_pass(): assert True")
            
            result = runner.invoke(phoenix_cli, ['run', '--env', 'dev', str(test_file)])
            
            assert result.exit_code == 0
            assert "Using environment: dev" in result.output
    
    @patch('src.phoenixframe.cli.PhoenixRunner')
    @patch('src.phoenixframe.cli.get_config')
    def test_run_with_invalid_environment(self, mock_get_config, mock_runner_class):
        """测试使用无效环境"""
        mock_config = Mock()
        mock_config.environments = {'dev': Mock()}
        mock_get_config.return_value = mock_config
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_example.py"
            test_file.write_text("def test_pass(): assert True")
            
            result = runner.invoke(phoenix_cli, ['run', '--env', 'invalid', str(test_file)])
            
            assert result.exit_code == 0
            assert "Environment 'invalid' not found" in result.output


class TestCLIReportCommand:
    """测试报告命令"""
    
    @patch('subprocess.run')
    def test_report_command_success(self, mock_subprocess):
        """测试报告命令成功执行"""
        mock_subprocess.return_value = None
        
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, ['report'])
        
        mock_subprocess.assert_called_once_with(
            ["allure", "serve", "allure-results"], 
            check=True
        )
    
    @patch('subprocess.run')
    def test_report_command_allure_not_found(self, mock_subprocess):
        """测试Allure未安装的情况"""
        mock_subprocess.side_effect = FileNotFoundError()
        
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, ['report'])
        
        assert "allure' command not found" in result.output


class TestCLIDoctorCommand:
    """测试环境检查命令"""
    
    @patch('src.phoenixframe.cli.doctor_module')
    def test_doctor_command(self, mock_doctor):
        """测试doctor命令"""
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, ['doctor'])
        
        mock_doctor.run_checks.assert_called_once()


class TestCLIEnvCommand:
    """测试环境管理命令"""
    
    @patch('src.phoenixframe.cli.env_module')
    def test_env_list_command(self, mock_env_module):
        """测试环境列表命令"""
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, ['env', 'list'])
        
        mock_env_module.list_environments.assert_called_once()


class TestCLIGenerateCommand:
    """测试代码生成命令"""
    
    @patch('src.phoenixframe.cli.HARParser')
    @patch('src.phoenixframe.cli.APITestGenerator')
    def test_generate_har_command(self, mock_generator_class, mock_parser_class):
        """测试HAR文件生成命令"""
        # 设置mocks
        mock_parser = Mock()
        mock_parser.parse.return_value = {"test": "data"}
        mock_parser_class.return_value = mock_parser
        
        mock_generator = Mock()
        mock_generator.generate.return_value = "generated code"
        mock_generator_class.return_value = mock_generator
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            har_file = Path(temp_dir) / "test.har"
            har_file.write_text('{"log": {"entries": []}}')
            
            output_file = Path(temp_dir) / "output.py"
            
            result = runner.invoke(phoenix_cli, [
                'generate', 'har', str(har_file), '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Successfully generated test code" in result.output
            assert output_file.exists()
            assert output_file.read_text() == "generated code"
    
    @patch('src.phoenixframe.cli.OpenAPIParser')
    @patch('src.phoenixframe.cli.OpenAPITestGenerator')
    def test_generate_openapi_command(self, mock_generator_class, mock_parser_class):
        """测试OpenAPI生成命令"""
        mock_parser = Mock()
        mock_parser.parse.return_value = {"endpoints": {}}
        mock_parser_class.return_value = mock_parser
        
        mock_generator = Mock()
        mock_generator.generate.return_value = "openapi generated code"
        mock_generator_class.return_value = mock_generator
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            openapi_file = Path(temp_dir) / "api.yaml"
            openapi_file.write_text('openapi: "3.0.0"')
            
            output_file = Path(temp_dir) / "api_test.py"
            
            result = runner.invoke(phoenix_cli, [
                'generate', 'openapi', str(openapi_file), '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Successfully generated test code" in result.output
    
    @patch('src.phoenixframe.cli.PlaywrightParser')
    @patch('src.phoenixframe.cli.POMGenerator')
    def test_generate_playwright_codegen_command(self, mock_generator_class, mock_parser_class):
        """测试Playwright代码生成命令"""
        mock_parser = Mock()
        mock_parser.parse.return_value = {"actions": []}
        mock_parser_class.return_value = mock_parser
        
        mock_generator = Mock()
        mock_generator.generate.return_value = {
            "pom_code": "pom code",
            "test_code": "test code",
            "data_yaml": {"data": "test"}
        }
        mock_generator_class.return_value = mock_generator
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            script_file = Path(temp_dir) / "script.py"
            script_file.write_text('# playwright script')
            
            result = runner.invoke(phoenix_cli, [
                'generate', 'playwright-codegen', str(script_file)
            ])
            
            assert result.exit_code == 0
            assert "Successfully generated Page Object Model" in result.output
            assert "Successfully generated Playwright test" in result.output
            assert "Successfully generated test data" in result.output


class TestCLIScaffoldCommand:
    """测试脚手架命令"""
    
    def test_scaffold_page_command(self):
        """测试页面脚手架生成"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "login_page.py"
            
            result = runner.invoke(phoenix_cli, [
                'scaffold', 'page', 'LoginPage', 
                '--base-url', 'https://example.com/login',
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Generated page object" in result.output
            assert output_file.exists()
            
            content = output_file.read_text()
            assert "class LoginpagePage(BasePage)" in content
            assert "https://example.com/login" in content
    
    def test_scaffold_api_command(self):
        """测试API客户端脚手架生成"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "user_api.py"
            
            result = runner.invoke(phoenix_cli, [
                'scaffold', 'api', 'UserAPI',
                '--base-url', 'https://api.example.com',
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Generated API client" in result.output
            assert output_file.exists()
            
            content = output_file.read_text()
            assert "class UserapiAPI:" in content
            assert "https://api.example.com" in content
    
    def test_scaffold_feature_command(self):
        """测试Feature文件脚手架生成"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "user_login.feature"
            
            result = runner.invoke(phoenix_cli, [
                'scaffold', 'feature', 'User Login',
                '--scenarios', 'Successful login',
                '--scenarios', 'Failed login',
                '--tags', 'auth',
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Generated feature file" in result.output
            assert output_file.exists()
            
            content = output_file.read_text()
            assert "Feature: User Login" in content
            assert "Scenario: Successful login" in content
            assert "Scenario: Failed login" in content
            assert "@auth" in content
    
    def test_scaffold_test_command_unit(self):
        """测试单元测试脚手架生成"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_calculator.py"
            
            result = runner.invoke(phoenix_cli, [
                'scaffold', 'test', 'Calculator',
                '--test-type', 'unit',
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Generated unit test" in result.output
            assert output_file.exists()
            
            content = output_file.read_text()
            assert "class TestCalculator:" in content
            assert "def test_calculator_basic" in content
    
    def test_scaffold_test_command_api(self):
        """测试API测试脚手架生成"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_api.py"
            
            result = runner.invoke(phoenix_cli, [
                'scaffold', 'test', 'UserAPI',
                '--test-type', 'api',
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Generated api test" in result.output
            assert output_file.exists()
            
            content = output_file.read_text()
            assert "class TestUserapiAPI:" in content
            assert "def test_userapi_get_request" in content
            assert "api_client" in content
    
    def test_scaffold_locustfile_command(self):
        """测试Locust文件脚手架生成"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "load_test.py"
            
            result = runner.invoke(phoenix_cli, [
                'scaffold', 'locustfile', 'LoadTest',
                '--target-url', 'https://api.example.com',
                '--users', '50',
                '--duration', '120',
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Generated Locust file" in result.output
            assert "Target URL: https://api.example.com" in result.output
            assert "Users: 50" in result.output
            assert "Duration: 120s" in result.output
            assert output_file.exists()
            
            content = output_file.read_text()
            assert "class LoadtestUser(HttpUser)" in content
            assert "https://api.example.com" in content


class TestCLIObservabilityCommand:
    """测试观测性命令"""
    
    @patch('src.phoenixframe.cli.get_metrics_summary')
    def test_observability_metrics_console_output(self, mock_get_metrics):
        """测试度量控制台输出"""
        mock_get_metrics.return_value = {
            'test_metrics': {'count': 10},
            'api_metrics': {'requests': 100},
            'web_metrics': {'actions': 50},
            'collection_interval': 10.0,
            'total_data_points': 160
        }
        
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, ['observability', 'metrics'])
        
        assert result.exit_code == 0
        assert "Metrics Summary" in result.output
        assert "Test Metrics" in result.output
        assert "API Metrics" in result.output
        assert "Web Metrics" in result.output
    
    @patch('src.phoenixframe.cli.export_metrics')
    def test_observability_metrics_file_output(self, mock_export_metrics):
        """测试度量文件输出"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "metrics.json"
            
            result = runner.invoke(phoenix_cli, [
                'observability', 'metrics', '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Metrics exported to" in result.output
            mock_export_metrics.assert_called_once_with(str(output_file))


class TestCLIDataCommands:
    """测试数据管理命令"""
    
    @patch('src.phoenixframe.cli.create_test_dataset')
    @patch('src.phoenixframe.cli.get_data_repository')
    def test_data_dataset_create_command(self, mock_get_repo, mock_create_dataset):
        """测试数据集创建命令"""
        # Mock repository
        mock_repo = Mock()
        mock_repo.save_dataset.return_value = "dataset_123"
        mock_get_repo.return_value = mock_repo
        
        # Mock dataset
        mock_dataset = Mock()
        mock_dataset.data = [{"id": 1}, {"id": 2}]
        mock_dataset.schema = {"id": "int"}
        mock_create_dataset.return_value = mock_dataset
        
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, [
            'data', 'dataset', 'create', 'test_users',
            '--data-type', 'user',
            '--count', '10',
            '--description', 'Test user dataset'
        ])
        
        assert result.exit_code == 0
        assert "Creating user dataset: test_users" in result.output
        assert "Created dataset: dataset_123" in result.output
    
    @patch('src.phoenixframe.cli.get_data_repository')
    def test_data_dataset_list_command(self, mock_get_repo):
        """测试数据集列表命令"""
        mock_repo = Mock()
        mock_repo.list_datasets.return_value = [
            {
                'name': 'test_users',
                'version': '1.0',
                'id': 'dataset_123',
                'record_count': 100,
                'tags': ['test', 'users'],
                'updated_at': '2024-01-01T10:00:00'
            }
        ]
        mock_get_repo.return_value = mock_repo
        
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, ['data', 'dataset', 'list'])
        
        assert result.exit_code == 0
        assert "Found 1 datasets" in result.output
        assert "test_users" in result.output
    
    @patch('src.phoenixframe.cli.get_data_repository')
    def test_data_dataset_show_command(self, mock_get_repo):
        """测试数据集显示命令"""
        mock_dataset = Mock()
        mock_dataset.name = "test_users"
        mock_dataset.description = "Test dataset"
        mock_dataset.version = "1.0"
        mock_dataset.data = [{"id": 1, "name": "User1"}]
        mock_dataset.tags = ["test"]
        mock_dataset.created_at = "2024-01-01T10:00:00"
        mock_dataset.updated_at = "2024-01-01T10:00:00"
        mock_dataset.schema = {"id": "int", "name": "str"}
        
        mock_repo = Mock()
        mock_repo.load_dataset.return_value = mock_dataset
        mock_get_repo.return_value = mock_repo
        
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, ['data', 'dataset', 'show', 'dataset_123'])
        
        assert result.exit_code == 0
        assert "Dataset: test_users" in result.output
        assert "Records: 1" in result.output


class TestCLIPerformanceCommands:
    """测试性能测试命令"""
    
    @patch('src.phoenixframe.cli.run_performance_test')
    def test_performance_run_command(self, mock_run_perf_test):
        """测试性能测试运行命令"""
        # Mock performance result
        mock_result = Mock()
        mock_result.status = "success"
        mock_result.duration = 60.5
        mock_result.metrics = Mock()
        mock_result.metrics.total_requests = 1000
        mock_result.metrics.failed_requests = 5
        mock_result.metrics.success_rate = 99.5
        mock_result.metrics.average_response_time = 250.0
        mock_result.metrics.requests_per_second = 16.5
        mock_result.errors = []
        mock_run_perf_test.return_value = mock_result
        
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, [
            'performance', 'run',
            '--target-url', 'https://api.example.com',
            '--users', '20',
            '--duration', '60'
        ])
        
        assert result.exit_code == 0
        assert "Starting performance test" in result.output
        assert "Performance Test Results" in result.output
        assert "Status: success" in result.output
        assert "Total Requests: 1000" in result.output
    
    @patch('src.phoenixframe.cli.generate_locustfile')
    def test_performance_generate_command(self, mock_generate_locustfile):
        """测试性能测试生成命令"""
        mock_generate_locustfile.return_value = "locust test content"
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test.py"
            
            result = runner.invoke(phoenix_cli, [
                'performance', 'generate',
                '--target-url', 'https://api.example.com',
                '--test-name', 'api_test',
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Generated Locust file" in result.output
            assert output_file.exists()


class TestCLIErrorHandling:
    """测试CLI错误处理"""
    
    def test_generate_har_file_not_found(self):
        """测试HAR文件不存在的错误处理"""
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, [
            'generate', 'har', '/nonexistent/file.har'
        ])
        
        assert result.exit_code != 0
    
    def test_scaffold_test_invalid_type(self):
        """测试无效测试类型的错误处理"""
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, [
            'scaffold', 'test', 'TestName',
            '--test-type', 'invalid_type'
        ])
        
        assert result.exit_code != 0
    
    @patch('src.phoenixframe.cli.get_data_repository')
    def test_data_command_error_handling(self, mock_get_repo):
        """测试数据命令错误处理"""
        mock_repo = Mock()
        mock_repo.save_dataset.side_effect = Exception("Database error")
        mock_get_repo.return_value = mock_repo
        
        runner = CliRunner()
        result = runner.invoke(phoenix_cli, [
            'data', 'dataset', 'create', 'test_dataset'
        ])
        
        assert result.exit_code == 1
        assert "Failed to create dataset" in result.output


@pytest.fixture
def temp_project_dir():
    """临时项目目录fixture"""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "test_project"
        project_dir.mkdir()
        
        # 创建基本项目结构
        (project_dir / "configs").mkdir()
        (project_dir / "tests").mkdir()
        
        # 创建配置文件
        config = {
            "app_name": "test_project",
            "environments": {
                "dev": {"base_url": "http://dev.example.com"},
                "prod": {"base_url": "http://prod.example.com"}
            }
        }
        config_file = project_dir / "configs" / "phoenix.yaml"
        config_file.write_text(yaml.dump(config))
        
        yield project_dir


class TestCLIIntegration:
    """CLI集成测试"""
    
    def test_full_workflow_project_init_and_run(self, temp_project_dir):
        """测试完整工作流：项目初始化和运行"""
        runner = CliRunner()
        
        # 1. 测试项目初始化
        result = runner.invoke(phoenix_cli, ['init', str(temp_project_dir / "new_project")])
        assert result.exit_code == 0
        
        # 2. 测试代码生成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write("""
Feature: Test Feature
  Test description
  
  Scenario: Test scenario
    Given a condition
    When an action  
    Then a result
""")
            feature_file = f.name
        
        try:
            result = runner.invoke(phoenix_cli, [
                'scaffold', 'feature', 'Integration Test',
                '--output', feature_file
            ])
            assert result.exit_code == 0
        finally:
            Path(feature_file).unlink()
    
    def test_cli_command_chaining(self):
        """测试CLI命令链接"""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. 创建项目
            project_path = Path(temp_dir) / "chain_test"
            result1 = runner.invoke(phoenix_cli, ['init', str(project_path)])
            assert result1.exit_code == 0
            
            # 2. 生成测试代码
            test_file = project_path / "tests" / "test_generated.py"
            result2 = runner.invoke(phoenix_cli, [
                'scaffold', 'test', 'GeneratedTest',
                '--test-type', 'unit',
                '--output', str(test_file)
            ])
            assert result2.exit_code == 0
            assert test_file.exists()