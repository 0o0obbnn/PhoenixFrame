"""BDD集成工具和辅助函数"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import click

from ..observability.logger import get_logger
from . import get_bdd_integration, BDD_AVAILABLE

logger = get_logger("phoenixframe.bdd.tools")


class BDDTools:
    """BDD工具集"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.features_dir = self.project_root / "features"
        self.steps_dir = self.project_root / "tests" / "bdd" / "steps"
        self.bdd_integration = get_bdd_integration(str(self.features_dir), str(self.steps_dir))
    
    def init_bdd_project(self) -> None:
        """初始化BDD项目结构"""
        # 创建目录结构
        directories = [
            self.features_dir,
            self.steps_dir,
            self.project_root / "tests" / "bdd",
            self.project_root / "tests" / "bdd" / "fixtures"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        
        # 创建示例Feature文件
        self._create_sample_feature()
        
        # 创建conftest.py
        self._create_conftest()
        
        # 创建步骤定义示例
        self._create_sample_steps()
        
        # 创建pytest.ini配置
        self._create_pytest_config()
        
        logger.info("BDD project structure initialized")
    
    def _create_sample_feature(self) -> None:
        """创建示例Feature文件"""
        sample_feature = '''@web @api
Feature: Sample User Registration
  As a new user
  I want to register an account
  So that I can access the application

  Background:
    Given I have an API client
    And I have a web browser

  @smoke @regression
  Scenario: Successful user registration via API
    When I send a POST request to "/api/users" with data:
      """
      {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123"
      }
      """
    Then the response status code should be 201
    And the response should contain "id"
    And the response "username" should be "testuser"

  @web @regression
  Scenario: Successful user registration via web
    When I navigate to "https://example.com/register"
    And I type "testuser" into "#username"
    And I type "test@example.com" into "#email"
    And I type "SecurePass123" into "#password"
    And I click on "#register-button"
    Then I should see element ".success-message"
    And the element ".success-message" should contain text "Registration successful"

  @validation @negative
  Scenario Outline: Registration with invalid data
    When I send a POST request to "/api/users" with data:
      """
      {
        "username": "<username>",
        "email": "<email>",
        "password": "<password>"
      }
      """
    Then the response status code should be 400
    And the response should contain "error"

    Examples:
      | username | email           | password |
      |          | test@email.com  | pass123  |
      | user     |                 | pass123  |
      | user     | test@email.com  |          |
      | user     | invalid-email   | pass123  |
'''
        
        feature_file = self.features_dir / "sample_registration.feature"
        feature_file.write_text(sample_feature, encoding='utf-8')
        logger.info(f"Created sample feature: {feature_file}")
    
    def _create_conftest(self) -> None:
        """创建pytest配置文件"""
        conftest_content = '''"""BDD测试配置"""
import pytest
from src.phoenixframe.bdd.steps import cleanup_test_context
from src.phoenixframe.observability.logger import setup_logging
from src.phoenixframe.observability.tracer import setup_tracing
from src.phoenixframe.observability.metrics import setup_metrics

# 设置观测性
setup_logging(level="INFO", enable_console=True, json_format=False)
setup_tracing(service_name="phoenixframe-bdd", console_export=True)
setup_metrics(collection_interval=5.0, console_export=True)


@pytest.fixture(scope="session", autouse=True)
def setup_bdd_environment():
    """设置BDD测试环境"""
    from src.phoenixframe.bdd import setup_bdd
    setup_bdd()
    yield
    # 清理


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """每个测试后自动清理"""
    yield
    cleanup_test_context()


@pytest.fixture
def api_client():
    """API客户端fixture"""
    from src.phoenixframe.api.client import APIClient
    client = APIClient()
    yield client
    client.close()


@pytest.fixture
def web_page():
    """Web页面fixture"""
    from src.phoenixframe.web.selenium_driver import SeleniumDriver, SeleniumPage
    driver_manager = SeleniumDriver(browser="chrome", headless=True)
    driver = driver_manager.start()
    page = SeleniumPage(driver)
    yield page
    driver_manager.quit()


@pytest.fixture
def playwright_page():
    """Playwright页面fixture"""
    try:
        from src.phoenixframe.web.playwright_driver import PlaywrightDriver, PlaywrightPage
        driver_manager = PlaywrightDriver(browser="chromium", headless=True)
        driver = driver_manager.start()
        page = PlaywrightPage(driver)
        yield page
        driver_manager.quit()
    except ImportError:
        pytest.skip("Playwright not available")
'''
        
        conftest_file = self.project_root / "tests" / "bdd" / "conftest.py"
        conftest_file.write_text(conftest_content, encoding='utf-8')
        logger.info(f"Created conftest.py: {conftest_file}")
    
    def _create_sample_steps(self) -> None:
        """创建示例步骤定义"""
        steps_content = '''"""示例BDD步骤定义"""
from pytest_bdd import scenarios, given, when, then
from src.phoenixframe.bdd.steps import *

# 加载所有scenarios
scenarios("../../features/")

# 自定义步骤定义可以在这里添加

@given('I have custom precondition')
def given_custom_precondition():
    """自定义Given步骤"""
    pass

@when('I perform custom action')
def when_custom_action():
    """自定义When步骤"""
    pass

@then('I should see custom result')
def then_custom_result():
    """自定义Then步骤"""
    pass
'''
        
        steps_file = self.steps_dir / "test_sample_steps.py"
        steps_file.write_text(steps_content, encoding='utf-8')
        logger.info(f"Created sample steps: {steps_file}")
    
    def _create_pytest_config(self) -> None:
        """创建pytest配置"""
        pytest_ini_content = '''[tool:pytest]
minversion = 6.0
addopts = 
    -ra
    -q
    --tb=short
    --strict-markers
    --strict-config
    --disable-warnings
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    smoke: smoke tests
    regression: regression tests
    web: web interface tests
    api: API tests
    integration: integration tests
    unit: unit tests
    slow: slow running tests
    validation: validation tests
    negative: negative test cases
bdd_features_base_dir = features/
'''
        
        config_file = self.project_root / "pytest.ini"
        if not config_file.exists():
            config_file.write_text(pytest_ini_content, encoding='utf-8')
            logger.info(f"Created pytest.ini: {config_file}")
    
    def generate_steps_from_features(self, output_dir: Optional[str] = None) -> List[str]:
        """从所有Feature文件生成步骤定义"""
        if not output_dir:
            output_dir = str(self.steps_dir)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        for feature_file in self.features_dir.rglob("*.feature"):
            feature_name = feature_file.stem
            output_file = output_path / f"test_{feature_name}_steps.py"
            
            try:
                step_code = self.bdd_integration.generate_step_definitions_for_feature(
                    str(feature_file), str(output_file)
                )
                generated_files.append(str(output_file))
                logger.info(f"Generated steps for {feature_file.name}")
            except Exception as e:
                logger.error(f"Failed to generate steps for {feature_file.name}: {e}")
        
        return generated_files
    
    def run_bdd_tests(self, tags: Optional[List[str]] = None, 
                     features: Optional[List[str]] = None,
                     parallel: bool = False,
                     html_report: bool = False,
                     allure_report: bool = False) -> Dict[str, Any]:
        """运行BDD测试"""
        cmd = [sys.executable, "-m", "pytest"]
        
        # 添加BDD相关参数
        if BDD_AVAILABLE:
            cmd.extend(["--gherkin-terminal-reporter"])
        
        # 添加HTML报告参数
        if html_report:
            html_report_path = self.project_root / "reports" / "bdd_report.html"
            html_report_path.parent.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--html", str(html_report_path), "--self-contained-html"])
        
        # 添加Allure报告参数
        if allure_report:
            allure_report_path = self.project_root / "reports" / "allure-results"
            allure_report_path.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--alluredir", str(allure_report_path)])
        
        # 添加测试路径
        if features:
            for feature in features:
                if not feature.startswith('/'):
                    feature = str(self.features_dir / feature)
                cmd.append(feature)
        else:
            cmd.append(str(self.project_root / "tests" / "bdd"))
        
        # 添加标签过滤
        if tags:
            tag_expression = " and ".join(tags)
            cmd.extend(["-m", tag_expression])
        
        # 并行执行
        if parallel:
            try:
                import pytest_xdist
                cmd.extend(["-n", "auto"])
            except ImportError:
                logger.warning("pytest-xdist not available, running sequentially")
        
        # 其他选项
        cmd.extend([
            "-v",
            "--tb=short",
            "--strict-markers",
            f"--rootdir={self.project_root}"
        ])
        
        # 执行命令
        logger.info(f"Running BDD tests with command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            return {
                "command": " ".join(cmd),
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "command": " ".join(cmd),
                "exit_code": -1,
                "stdout": "",
                "stderr": "Test execution timed out",
                "success": False
            }
        except Exception as e:
            return {
                "command": " ".join(cmd),
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False
            }
    
    def validate_features(self) -> Dict[str, Any]:
        """验证Feature文件"""
        results = {
            "total_features": 0,
            "total_scenarios": 0,
            "valid_features": [],
            "invalid_features": [],
            "errors": [],
            "validation_passed": True
        }
        
        if not self.features_dir.exists():
            results["errors"].append(f"Features directory not found: {self.features_dir}")
            results["validation_passed"] = False
            return results
        
        for feature_file in self.features_dir.rglob("*.feature"):
            results["total_features"] += 1
            validation_result = self.bdd_integration.feature_manager.validate_feature(str(feature_file))
            
            if validation_result["valid"]:
                results["valid_features"].append(str(feature_file))
            else:
                results["invalid_features"].append(str(feature_file))
                results["errors"].extend(validation_result["errors"])
                results["validation_passed"] = False
        
        return results
    
    def get_test_coverage(self) -> Dict[str, Any]:
        """获取测试覆盖率信息"""
        coverage_data = {
            "total_steps": 0,
            "implemented_steps": 0,
            "coverage_percent": 0.0,
            "features_count": 0,
            "missing_steps": []
        }
        
        # 发现所有Feature文件
        features = self.bdd_integration.feature_manager.discover_features()
        coverage_data["features_count"] = len(features)
        
        # 收集所有步骤
        all_steps = set()
        for feature_info in features:
            # 这里应该解析Feature文件并提取步骤
            # 简化处理，仅作示例
            pass
        
        # 计算覆盖率（简化示例）
        coverage_data["total_steps"] = len(all_steps)
        coverage_data["implemented_steps"] = len(all_steps)  # 假设全部已实现
        coverage_data["coverage_percent"] = 100.0 if all_steps else 0.0
        
        return coverage_data
    
    def generate_html_report_template(self) -> str:
        """生成HTML报告模板"""
        template = '''
<!DOCTYPE html>
<html>
<head>
    <title>BDD测试报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }
        .summary { margin: 20px 0; }
        .feature { border: 1px solid #ddd; margin: 10px 0; padding: 10px; border-radius: 5px; }
        .scenario { margin: 10px 0; padding: 5px; background-color: #f9f9f9; }
        .passed { color: green; }
        .failed { color: red; }
        .stats { display: flex; justify-content: space-around; margin: 20px 0; }
        .stat-box { text-align: center; padding: 10px; border-radius: 5px; }
        .stat-box.passed { background-color: #d4edda; }
        .stat-box.failed { background-color: #f8d7da; }
    </style>
</head>
<body>
    <div class="header">
        <h1>BDD测试报告</h1>
        <p>生成时间: <span id="report-time"></span></p>
    </div>
    
    <div class="stats">
        <div class="stat-box passed">
            <h2 id="passed-count">0</h2>
            <p>通过</p>
        </div>
        <div class="stat-box failed">
            <h2 id="failed-count">0</h2>
            <p>失败</p>
        </div>
    </div>
    
    <div class="summary">
        <h2>测试摘要</h2>
        <p>总功能数: <span id="total-features">0</span></p>
        <p>总场景数: <span id="total-scenarios">0</span></p>
        <p>通过率: <span id="pass-rate">0%</span></p>
    </div>
    
    <div id="features-container">
        <!-- 功能和场景将在这里动态生成 -->
    </div>
    
    <script>
        // 设置报告生成时间
        document.getElementById('report-time').textContent = new Date().toLocaleString();
        
        // 示例数据（实际应用中应从测试结果中获取）
        const testData = {
            features: [
                {
                    name: "用户登录功能",
                    description: "测试用户登录相关场景",
                    scenarios: [
                        { name: "成功登录", status: "passed", steps: ["Given 用户在登录页面", "When 输入有效凭据", "Then 登录成功"] },
                        { name: "无效凭据登录", status: "failed", steps: ["Given 用户在登录页面", "When 输入无效凭据", "Then 显示错误信息"] }
                    ]
                }
            ],
            summary: {
                totalFeatures: 1,
                totalScenarios: 2,
                passed: 1,
                failed: 1
            }
        };
        
        // 更新统计信息
        document.getElementById('passed-count').textContent = testData.summary.passed;
        document.getElementById('failed-count').textContent = testData.summary.failed;
        document.getElementById('total-features').textContent = testData.summary.totalFeatures;
        document.getElementById('total-scenarios').textContent = testData.summary.totalScenarios;
        document.getElementById('pass-rate').textContent = ((testData.summary.passed / (testData.summary.passed + testData.summary.failed)) * 100).toFixed(1) + '%';
        
        // 生成功能和场景列表
        const container = document.getElementById('features-container');
        testData.features.forEach(feature => {
            const featureDiv = document.createElement('div');
            featureDiv.className = 'feature';
            featureDiv.innerHTML = `
                <h3>${feature.name}</h3>
                <p>${feature.description}</p>
            `;
            
            feature.scenarios.forEach(scenario => {
                const scenarioDiv = document.createElement('div');
                scenarioDiv.className = `scenario ${scenario.status}`;
                scenarioDiv.innerHTML = `
                    <h4>${scenario.name} <span class="${scenario.status}">(${scenario.status})</span></h4>
                    <ul>
                        ${scenario.steps.map(step => `<li>${step}</li>`).join('')}
                    </ul>
                `;
                featureDiv.appendChild(scenarioDiv);
            });
            
            container.appendChild(featureDiv);
        });
    </script>
</body>
</html>
        '''
        
        report_dir = self.project_root / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "bdd_report_template.html"
        report_file.write_text(template, encoding='utf-8')
        
        return str(report_file)


# CLI命令
@click.group()
def bdd_cli():
    """BDD相关命令"""
    pass


@bdd_cli.command()
@click.option('--project-root', default='.', help='项目根目录')
def init(project_root: str):
    """初始化BDD项目结构"""
    tools = BDDTools(project_root)
    tools.init_bdd_project()
    click.echo("BDD project structure initialized successfully!")


@bdd_cli.command()
@click.option('--output-dir', help='输出目录')
@click.option('--project-root', default='.', help='项目根目录')
def generate_steps(output_dir: Optional[str], project_root: str):
    """从Feature文件生成步骤定义"""
    tools = BDDTools(project_root)
    files = tools.generate_steps_from_features(output_dir)
    click.echo(f"Generated {len(files)} step definition files:")
    for file_path in files:
        click.echo(f"  - {file_path}")


@bdd_cli.command()
@click.option('--tags', multiple=True, help='运行指定标签的测试')
@click.option('--features', multiple=True, help='运行指定Feature文件')
@click.option('--tags', multiple=True, help='运行指定标签的测试')
@click.option('--features', multiple=True, help='运行指定Feature文件')
@click.option('--parallel', is_flag=True, help='并行执行测试')
@click.option('--html-report', is_flag=True, help='生成HTML报告')
@click.option('--allure-report', is_flag=True, help='生成Allure报告')
@click.option('--project-root', default='.', help='项目根目录')
def run(tags: List[str], features: List[str], parallel: bool, 
        html_report: bool, allure_report: bool, project_root: str):
    """运行BDD测试"""
    tools = BDDTools(project_root)
    result = tools.run_bdd_tests(list(tags) if tags else None, list(features) if features else None, parallel)
    
    click.echo(f"Command: {result['command']}")
    click.echo(f"Exit code: {result['exit_code']}")
    
    if result['stdout']:
        click.echo("STDOUT:")
        click.echo(result['stdout'])
    
    if result['stderr']:
        click.echo("STDERR:")
        click.echo(result['stderr'])
    
    if result['success']:
        click.echo("✅ BDD tests passed!")
    else:
        click.echo("❌ BDD tests failed!")
        sys.exit(1)


@bdd_cli.command()
@click.option('--project-root', default='.', help='项目根目录')
def validate(project_root: str):
    """验证Feature文件"""
    tools = BDDTools(project_root)
    results = tools.validate_features()
    
    click.echo(f"Total features: {results['total_features']}")
    click.echo(f"Total scenarios: {results['total_scenarios']}")
    click.echo(f"Valid features: {len(results['valid_features'])}")
    click.echo(f"Invalid features: {len(results['invalid_features'])}")
    
    if results['errors']:
        click.echo("\nErrors:")
        for error in results['errors']:
            click.echo(f"  - {error}")
    
    if results['validation_passed']:
        click.echo("✅ All features are valid!")
    else:
        click.echo("❌ Some features have issues!")
        sys.exit(1)


@bdd_cli.command()
@click.option('--project-root', default='.', help='项目根目录')
def coverage(project_root: str):
    """显示步骤覆盖率"""
    tools = BDDTools(project_root)
    coverage_data = tools.get_test_coverage()
    
    click.echo(f"Total steps: {coverage_data['total_steps']}")
    click.echo(f"Implemented steps: {coverage_data['implemented_steps']}")
    click.echo(f"Coverage: {coverage_data['coverage_percent']:.1f}%")
    click.echo(f"Features: {coverage_data['features_count']}")
    
    if coverage_data['missing_steps']:
        click.echo(f"\nMissing steps ({len(coverage_data['missing_steps'])}):")
        for step in coverage_data['missing_steps'][:10]:  # 只显示前10个
            click.echo(f"  - {step['step_type']}: {step['step_text']}")
        
        if len(coverage_data['missing_steps']) > 10:
            click.echo(f"  ... and {len(coverage_data['missing_steps']) - 10} more")


if __name__ == '__main__':
    bdd_cli()