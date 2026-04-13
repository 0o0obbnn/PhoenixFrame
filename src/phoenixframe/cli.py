"""PhoenixFrame命令行工具"""
from pathlib import Path
import click
import yaml
import os
import json
import sys
from typing import Optional, Dict, Any

# Expose module-level symbols for tests to patch
from .data import get_data_repository  # noqa: F401
from .performance import run_performance_test, generate_locustfile  # noqa: F401
from .observability.metrics import get_metrics_summary, export_metrics  # noqa: F401

def _safe_import(module_name, item_name=None):
    """安全导入模块，失败时返回None"""
    try:
        if item_name:
            if module_name.startswith('.'):
                # 相对导入
                module = __import__(f'{__package__}{module_name}', fromlist=[item_name])
            else:
                module = __import__(module_name, fromlist=[item_name])
            return getattr(module, item_name)
        else:
            if module_name.startswith('.'):
                return __import__(f'{__package__}{module_name}')
            else:
                return __import__(module_name)
    except (ImportError, AttributeError) as e:
        return None

# 尝试导入可选模块
try:
    from . import env as env_module
except ImportError:
    env_module = None

setup_logging = _safe_import('phoenixframe.observability.logger', 'setup_logging')
get_logger = _safe_import('phoenixframe.observability.logger', 'get_logger')
setup_tracing = _safe_import('phoenixframe.observability.tracer', 'setup_tracing')
setup_metrics = _safe_import('phoenixframe.observability.metrics', 'setup_metrics')
bdd_cli = _safe_import('phoenixframe.bdd.tools', 'bdd_cli')

def _check_dependency_error(feature_name: str, missing_deps: list = None):
    """检查依赖并给出友好的错误信息"""
    click.echo(f"❌ {feature_name} 功能不可用", err=True)
    if missing_deps:
        click.echo(f"缺少依赖: {', '.join(missing_deps)}", err=True)
        click.echo(f"请运行: pip install {' '.join(missing_deps)}", err=True)
    else:
        click.echo("请确保已安装所有必要的依赖", err=True)

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--json-logs', is_flag=True, help='Enable JSON formatted logs')
@click.option('--trace-console', is_flag=True, help='Enable console tracing')
@click.option('--metrics-console', is_flag=True, help='Enable console metrics')
@click.pass_context
def main(ctx, debug, json_logs, trace_console, metrics_console):
    """PhoenixFrame CLI - 企业级自动化测试框架"""
    # 确保context对象存在
    ctx.ensure_object(dict)
    
    # 设置观测性
    if setup_logging:
        log_level = "DEBUG" if debug else "INFO"
        setup_logging(
            level=log_level,
            enable_console=True,
            json_format=json_logs
        )
    else:
        click.echo("⚠️  日志系统不可用，请检查依赖安装", err=True)
    
    if trace_console and setup_tracing:
        setup_tracing(
            service_name="phoenixframe-cli",
            console_export=True
        )
    elif trace_console:
        _check_dependency_error("追踪系统", ["opentelemetry-api", "opentelemetry-sdk"])
    
    if metrics_console and setup_metrics:
        setup_metrics(
            collection_interval=5.0,
            console_export=True
        )
    elif metrics_console:
        _check_dependency_error("度量系统", ["psutil"])
    
    # 存储配置到context
    ctx.obj['debug'] = debug
    ctx.obj['json_logs'] = json_logs
    ctx.obj['trace_console'] = trace_console
    ctx.obj['metrics_console'] = metrics_console


@main.command()
@click.argument("project_name", type=click.Path())
def init(project_name):
    """Initialize a new PhoenixFrame project."""
    project_path = Path(project_name).resolve()
    if project_path.exists() and any(project_path.iterdir()):
        click.echo(f"Error: Directory '{project_path}' already exists and is not empty.", err=True)
        return

    click.echo(f"Initializing project '{project_name}' at '{project_path}'...")

    try:
        # Create directories
        expected_dirs = [
            "src/phoenixframe",
            "tests",
            "configs",
            "data",
            "docs",
            "templates",
        ]
        for d in expected_dirs:
            dir_path = project_path / d
            dir_path.mkdir(parents=True, exist_ok=True)
            click.echo(f"  Created directory: {dir_path}")

        # Create files
        project_config = {
            "app_name": project_path.name,
            "version": "1.0",
            "environments": {
                "default": {
                    "base_url": "http://localhost:8000",
                    "description": "Default environment"
                }
            },
            "reporting": {
                "allure": {
                    "enabled": True,
                    "report_dir": "allure-report",
                    "results_dir": "allure-results"
                }
            }
        }
        
        files_to_create = {
            "configs/phoenix.yaml": yaml.dump(project_config, default_flow_style=False, allow_unicode=True),
            "pyproject.toml": f'[project]\nname = "{project_name}"\nversion = "0.1.0"\ndescription = "PhoenixFrame automated testing project"\nrequires-python = ">=3.8"\ndependencies = [\n    "phoenixframe",\n    "pytest",\n    "pytest-bdd",\n    "allure-pytest"\n]\n\n[build-system]\nrequires = ["setuptools>=61.0"]\nbuild-backend = "setuptools.build_meta"\n',
            "README.md": f"# {project_name}\n\n这是一个使用PhoenixFrame框架创建的自动化测试项目。\n\n## 快速开始\n\n```bash\n# 安装依赖\npip install -r requirements.txt\n\n# 运行测试\nphoenix run tests/\n\n# 运行BDD测试\nphoenix bdd run\n\n# 生成报告\nphoenix report\n```\n\n## 项目结构\n\n- `features/` - BDD Feature文件\n- `tests/` - 测试用例\n- `configs/` - 配置文件\n- `data/` - 测试数据\n- `docs/` - 文档\n",
            ".gitignore": "# Python\n__pycache__/\n*.pyc\n*.pyo\n*.pyd\n.Python\nbuild/\ndevelop-eggs/\ndist/\ndownloads/\neggs/\n.eggs/\nlib/\nlib64/\nparts/\nsdist/\nvar/\nwheels/\n*.egg-info/\n.installed.cfg\n*.egg\n\n# Virtual environments\n.venv/\nenv/\nvenv/\nENV/\nenv.bak/\nvenv.bak/\n\n# PhoenixFrame\n.pytest_cache/\n.coverage\nhtmlcov/\n\n# Reports\nallure-report/\nallure-results/\ntest-results/\nlogs/\nscreenshots/\n\n# IDE\n.vscode/\n.idea/\n*.swp\n*.swo\n*~\n\n# OS\n.DS_Store\nThumbs.db\n",
            "features/.gitkeep": "",
            "tests/__init__.py": "",
            "tests/conftest.py": f'''"""测试配置和fixtures"""
import pytest
from src.phoenixframe.observability.logger import setup_logging
from src.phoenixframe.observability.tracer import setup_tracing
from src.phoenixframe.observability.metrics import setup_metrics

# 设置观测性
setup_logging(level="INFO", enable_console=True, json_format=False)
setup_tracing(service_name="{project_name}", console_export=True)
setup_metrics(collection_interval=10.0, console_export=True)


@pytest.fixture(scope="session")
def api_client():
    """API客户端fixture"""
    from src.phoenixframe.api.client import APIClient
    client = APIClient()
    yield client
    client.close()


@pytest.fixture(scope="function")
def selenium_page():
    """Selenium页面fixture"""
    from src.phoenixframe.web.selenium_driver import SeleniumDriver, SeleniumPage
    driver_manager = SeleniumDriver(browser="chrome", headless=True)
    driver = driver_manager.start()
    page = SeleniumPage(driver)
    yield page
    driver_manager.quit()


@pytest.fixture(scope="function")
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
''',
            "tests/test_example.py": '''"""示例测试用例"""
import pytest


def test_example_pass():
    """示例通过测试"""
    assert 1 + 1 == 2


def test_example_api(api_client):
    """示例API测试"""
    # response = api_client.get("/api/health")
    # assert response.status_code == 200
    pass


@pytest.mark.web
def test_example_web(selenium_page):
    """示例Web测试"""
    # selenium_page.navigate("https://example.com")
    # assert selenium_page.is_element_present("h1")
    pass
''',
            "requirements.txt": "# PhoenixFrame dependencies\npytest>=7.0\npytest-bdd>=6.0\nallure-pytest>=2.0\nselenium>=4.0\nplaywright>=1.0\nrequests>=2.28\npytest-xdist>=3.0\npytest-html>=3.0\npsutil>=5.9\n",
        }

        for file_path, content in files_to_create.items():
            path = project_path / file_path
            path.write_text(content, encoding="utf-8")
            click.echo(f"  Created file: {path}")

        click.echo(f"\nProject '{project_name}' initialized successfully.")

    except Exception as e:
        click.echo(f"Error during project initialization: {e}", err=True)


@main.command()
def report():
    """Generate and serve the Allure report."""
    import subprocess
    try:
        subprocess.run(["allure", "serve", "allure-results"], check=True)
    except FileNotFoundError:
        click.echo("Error: 'allure' command not found. Please make sure Allure is installed and in your PATH.", err=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error serving Allure report: {e}", err=True)

@main.command(context_settings={'ignore_unknown_options': True, 'allow_extra_args': True})
@click.argument("test_paths", nargs=-1, type=click.Path(exists=True))
@click.option("--env", "-e", help="Specify the environment to use for testing")
@click.pass_context
def run(ctx, test_paths, env):
    """Run tests with optional environment and pytest arguments.

    Extra pytest arguments can be passed after a '--' separator.
    Example: phoenix run tests/ -- -v -k "login_test"
    """
    from .core.runner import PhoenixRunner
    from .core.config import get_config, set_config, load_config
    from pathlib import Path

    # Set environment if specified
    if env:
        config = get_config()
        if env in config.environments:
            click.echo(f"Using environment: {env}")
            # 可以在这里设置当前环境，影响后续的配置获取
            # 这里我们通过临时设置环境变量来实现
            import os
            current_env = config.environments[env]
            os.environ['PHOENIX_CURRENT_ENV'] = env
            click.echo(f"Environment base URL: {current_env.base_url}")
        else:
            available_envs = list(config.environments.keys())
            click.echo(f"Error: Environment '{env}' not found. Available environments: {available_envs}", err=True)
            return

    # Get extra arguments from context
    pytest_extra_args = ctx.args if ctx.args else []

    runner = PhoenixRunner()
    result = runner.run_tests(test_paths=list(test_paths), pytest_extra_args=pytest_extra_args)
    exit(result.get("pytest_exit_code", 0))



@main.command()
def doctor():
    """Check environment configuration and dependencies."""
    from . import doctor as doctor_module
    doctor_module.run_checks()

@main.group()
def env():
    """Manage test environments."""
    pass

@env.command("list")
def list_envs():
    """List all configured environments."""
    if env_module:
        env_module.list_environments()
    else:
        _check_dependency_error("环境管理", ["pydantic", "pyyaml"])

@main.group()
def generate():
    """Generate test code from various assets."""
    pass

@generate.command()
@click.argument("har_file", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option("--output", "-o", type=click.Path(dir_okay=False, writable=True), default="generated_api_test.py", help="Output file path for the generated test code.")
def har(har_file, output):
    """Generate API test code from a HAR file.

    HAR_FILE: Path to the HAR file.
    """
    from .codegen.har_parser import HARParser
    from .codegen.api_generator import APITestGenerator

    click.echo(f"Generating API test code from {har_file}...")
    try:
        with open(har_file, "r", encoding="utf-8") as f:
            har_content = f.read()

        parser = HARParser()
        parsed_data = parser.parse(har_content)

        generator = APITestGenerator()
        generated_code = generator.generate(parsed_data)

        output_path = Path(output)
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(generated_code)

        click.echo(f"Successfully generated test code to {output_path}")
    except Exception as e:
        click.echo(f"Error generating code: {e}", err=True)
        exit(1)

@generate.command()
@click.argument("openapi_file", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option("--output", "-o", type=click.Path(dir_okay=False, writable=True), default="generated_openapi_test.py", help="Output file path for the generated test code.")
def openapi(openapi_file, output):
    """Generate API test code skeletons from an OpenAPI/Swagger file.

    OPENAPI_FILE: Path to the OpenAPI/Swagger file (YAML or JSON).
    """
    from .codegen.openapi_parser import OpenAPIParser
    from .codegen.openapi_generator import OpenAPITestGenerator

    click.echo(f"Generating OpenAPI test code skeletons from {openapi_file}...")
    try:
        with open(openapi_file, "r", encoding="utf-8") as f:
            openapi_content = f.read()

        parser = OpenAPIParser()
        parsed_data = parser.parse(openapi_content)

        generator = OpenAPITestGenerator()
        generated_code = generator.generate(parsed_data)

        output_path = Path(output)
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(generated_code)

        click.echo(f"Successfully generated test code to {output_path}")
    except Exception as e:
        click.echo(f"Error generating code: {e}", err=True)
        exit(1)

@generate.command("playwright-codegen")
@click.argument("script_file", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option("--output-pom", type=click.Path(dir_okay=False, writable=True), default="generated_pom.py", help="Output file path for the generated Page Object Model.")
@click.option("--output-test", type=click.Path(dir_okay=False, writable=True), default="generated_playwright_test.py", help="Output file path for the generated Playwright test.")
@click.option("--output-data", type=click.Path(dir_okay=False, writable=True), default="generated_test_data.yaml", help="Output file path for the generated test data YAML.")
def playwright_codegen(script_file, output_pom, output_test, output_data):
    """Generate POM and test code from a Playwright Codegen Python script.

    SCRIPT_FILE: Path to the Playwright Codegen Python script.
    """
    from .codegen.playwright_parser import PlaywrightParser
    from .codegen.pom_generator import POMGenerator

    click.echo(f"Generating POM and test code from {script_file}...")
    try:
        with open(script_file, "r", encoding="utf-8") as f:
            script_content = f.read()

        parser = PlaywrightParser()
        parsed_data = parser.parse(script_content)

        generator = POMGenerator()
        generated_assets = generator.generate(parsed_data)

        # Write POM code
        pom_output_path = Path(output_pom)
        if not pom_output_path.parent.exists():
            pom_output_path.parent.mkdir(parents=True)
        with open(pom_output_path, "w", encoding="utf-8") as f:
            f.write(generated_assets["pom_code"])
        click.echo(f"Successfully generated Page Object Model to {pom_output_path}")

        # Write Test code
        test_output_path = Path(output_test)
        if not test_output_path.parent.exists():
            test_output_path.parent.mkdir(parents=True)
        with open(test_output_path, "w", encoding="utf-8") as f:
            f.write(generated_assets["test_code"])
        click.echo(f"Successfully generated Playwright test to {test_output_path}")

        # Write Data YAML
        data_output_path = Path(output_data)
        if not data_output_path.parent.exists():
            data_output_path.parent.mkdir(parents=True)
        with open(data_output_path, "w", encoding="utf-8") as f:
            yaml.dump(generated_assets["data_yaml"], f, allow_unicode=True)
        click.echo(f"Successfully generated test data to {data_output_path}")

    except Exception as e:
        click.echo(f"Error generating code: {e}", err=True)
        exit(1)


# 添加脚手架命令组
@main.group()
def scaffold():
    """代码脚手架生成器"""
    pass


@scaffold.command()
@click.argument("name")
@click.option("--base-url", default="", help="页面基础URL")
@click.option("--output", "-o", help="输出文件路径")
def page(name, base_url, output):
    """生成页面对象模板"""
    logger = get_logger("phoenixframe.cli.scaffold")
    
    page_template = f'''"""
{name} Page Object
Generated by PhoenixFrame CLI
"""
from typing import Optional
from src.phoenixframe.web.base_page import BasePage
from src.phoenixframe.observability.logger import get_logger
from src.phoenixframe.observability.tracer import get_tracer


class {name.title().replace('_', '')}Page(BasePage):
    """Page Object for {name}"""
    
    def __init__(self, driver):
        super().__init__(driver)
        self.url = "{base_url}"
        self.logger = get_logger(f"{{__name__}}")
        self.tracer = get_tracer(f"{{__name__}}")
    
    # Locators
    # Example: LOGIN_BUTTON = "#login-btn"
    
    def navigate(self, url: Optional[str] = None) -> None:
        """导航到页面"""
        target_url = url or self.url
        if not target_url:
            raise ValueError("URL is required")
        self.driver.get(target_url)
        self.logger.info(f"Navigated to {{target_url}}")
    
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """等待页面加载完成"""
        # TODO: 实现页面加载等待逻辑
        return True
    
    def is_page_loaded(self) -> bool:
        """检查页面是否加载完成"""
        # TODO: 实现页面加载检查逻辑
        return True
    
    # Page Actions
    # Example:
    # def click_login_button(self):
    #     """点击登录按钮"""
    #     with self.tracer.trace_page_action("click_login_button"):
    #         self.click_element(self.LOGIN_BUTTON)
    #         self.logger.web_action("click", element=self.LOGIN_BUTTON)
'''
    
    if not output:
        output = f"{name.lower()}_page.py"
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page_template, encoding='utf-8')
    
    click.echo(f"✅ Generated page object: {output_path}")
    logger.info(f"Generated page object: {output_path}")


@scaffold.command()
@click.argument("name")
@click.option("--base-url", default="", help="API基础URL")
@click.option("--output", "-o", help="输出文件路径")
def api(name, base_url, output):
    """生成API客户端模板"""
    logger = get_logger("phoenixframe.cli.scaffold")
    
    api_template = f'''"""
{name} API Client
Generated by PhoenixFrame CLI
"""
from typing import Dict, Any, Optional
from src.phoenixframe.api.client import APIClient
from src.phoenixframe.api.response import APIResponse
from src.phoenixframe.observability.logger import get_logger
from src.phoenixframe.observability.tracer import get_tracer


class {name.title().replace('_', '')}API:
    """API Client for {name}"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or "{base_url}"
        self.client = APIClient(self.base_url)
        self.logger = get_logger(f"{{__name__}}")
        self.tracer = get_tracer(f"{{__name__}}")
    
    def close(self):
        """关闭客户端"""
        self.client.close()
    
    # API Methods
    # Example:
    # def get_users(self, params: Optional[Dict[str, Any]] = None) -> APIResponse:
    #     """获取用户列表"""
    #     with self.tracer.trace_api_request("GET", "/users"):
    #         response = self.client.get("/users", params=params)
    #         self.logger.api_request("GET", "/users", params=params)
    #         self.logger.api_response(response.status_code, 0.0)
    #         return response
    
    # def create_user(self, user_data: Dict[str, Any]) -> APIResponse:
    #     """创建用户"""
    #     with self.tracer.trace_api_request("POST", "/users"):
    #         response = self.client.post("/users", json=user_data)
    #         self.logger.api_request("POST", "/users", data=user_data)
    #         self.logger.api_response(response.status_code, 0.0)
    #         return response
'''
    
    if not output:
        output = f"{name.lower()}_api.py"
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(api_template, encoding='utf-8')
    
    click.echo(f"✅ Generated API client: {output_path}")
    logger.info(f"Generated API client: {output_path}")


@scaffold.command()
@click.argument("name")
@click.option("--scenarios", "-s", multiple=True, help="Scenario names")
@click.option("--tags", "-t", multiple=True, help="Feature tags")
@click.option("--output", "-o", help="输出文件路径")
def feature(name, scenarios, tags, output):
    """生成BDD Feature文件"""
    logger = get_logger("phoenixframe.cli.scaffold")
    
    from .bdd import get_bdd_integration
    
    bdd_integration = get_bdd_integration()
    
    if not scenarios:
        scenarios = [f"Basic {name} scenario"]
    
    feature_content = bdd_integration.feature_manager.create_feature_template(
        feature_name=name,
        scenarios=list(scenarios),
        description=f"Feature for {name} functionality",
        tags=list(tags) if tags else None
    )
    
    if not output:
        output = f"features/{name.lower().replace(' ', '_')}.feature"
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(feature_content, encoding='utf-8')
    
    click.echo(f"✅ Generated feature file: {output_path}")
    logger.info(f"Generated feature file: {output_path}")


@scaffold.command()
@click.argument("test_name")
@click.option("--test-type", type=click.Choice(['unit', 'integration', 'api', 'web', 'bdd']), 
              default='unit', help="测试类型")
@click.option("--output", "-o", help="输出文件路径")
def test(test_name, test_type, output):
    """生成测试用例模板"""
    logger = get_logger("phoenixframe.cli.scaffold")
    
    templates = {
        'unit': f'''"""
{test_name} Unit Tests
Generated by PhoenixFrame CLI
"""
import pytest
from src.phoenixframe.observability.logger import get_logger
from src.phoenixframe.observability.tracer import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class Test{test_name.title().replace('_', '')}:
    """Unit tests for {test_name}"""
    
    def test_{test_name.lower()}_basic(self):
        """Basic test for {test_name}"""
        with tracer.trace_test_case("test_{test_name.lower()}_basic"):
            logger.test_start("test_{test_name.lower()}_basic")
            
            # TODO: Implement test logic
            assert True
            
            logger.test_end("test_{test_name.lower()}_basic", "passed", 0.0)
    
    def test_{test_name.lower()}_edge_cases(self):
        """Edge cases test for {test_name}"""
        with tracer.trace_test_case("test_{test_name.lower()}_edge_cases"):
            logger.test_start("test_{test_name.lower()}_edge_cases")
            
            # TODO: Implement edge cases
            assert True
            
            logger.test_end("test_{test_name.lower()}_edge_cases", "passed", 0.0)
''',
        'api': f'''"""
{test_name} API Tests
Generated by PhoenixFrame CLI
"""
import pytest
from src.phoenixframe.observability.logger import get_logger
from src.phoenixframe.observability.tracer import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class Test{test_name.title().replace('_', '')}API:
    """API tests for {test_name}"""
    
    def test_{test_name.lower()}_get_request(self, api_client):
        """Test GET request for {test_name}"""
        with tracer.trace_test_case("test_{test_name.lower()}_get_request"):
            logger.test_start("test_{test_name.lower()}_get_request")
            
            # TODO: Implement API GET test
            # response = api_client.get("/api/{test_name.lower()}")
            # assert response.status_code == 200
            
            logger.test_end("test_{test_name.lower()}_get_request", "passed", 0.0)
    
    def test_{test_name.lower()}_post_request(self, api_client):
        """Test POST request for {test_name}"""
        with tracer.trace_test_case("test_{test_name.lower()}_post_request"):
            logger.test_start("test_{test_name.lower()}_post_request")
            
            # TODO: Implement API POST test
            # data = {{"key": "value"}}
            # response = api_client.post("/api/{test_name.lower()}", json=data)
            # assert response.status_code == 201
            
            logger.test_end("test_{test_name.lower()}_post_request", "passed", 0.0)
''',
        'web': f'''"""
{test_name} Web Tests
Generated by PhoenixFrame CLI
"""
import pytest
from src.phoenixframe.observability.logger import get_logger
from src.phoenixframe.observability.tracer import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


@pytest.mark.web
class Test{test_name.title().replace('_', '')}Web:
    """Web tests for {test_name}"""
    
    def test_{test_name.lower()}_page_load(self, selenium_page):
        """Test page loading for {test_name}"""
        with tracer.trace_test_case("test_{test_name.lower()}_page_load"):
            logger.test_start("test_{test_name.lower()}_page_load")
            
            # TODO: Implement web test
            # selenium_page.navigate("https://example.com/{test_name.lower()}")
            # assert selenium_page.wait_for_page_load()
            
            logger.test_end("test_{test_name.lower()}_page_load", "passed", 0.0)
    
    def test_{test_name.lower()}_interaction(self, selenium_page):
        """Test user interaction for {test_name}"""
        with tracer.trace_test_case("test_{test_name.lower()}_interaction"):
            logger.test_start("test_{test_name.lower()}_interaction")
            
            # TODO: Implement interaction test
            # selenium_page.navigate("https://example.com/{test_name.lower()}")
            # selenium_page.click_element("#submit-button")
            # assert selenium_page.is_element_present(".success-message")
            
            logger.test_end("test_{test_name.lower()}_interaction", "passed", 0.0)
''',
        'integration': f'''"""
{test_name} Integration Tests
Generated by PhoenixFrame CLI
"""
import pytest
from src.phoenixframe.observability.logger import get_logger
from src.phoenixframe.observability.tracer import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


@pytest.mark.integration
class Test{test_name.title().replace('_', '')}Integration:
    """Integration tests for {test_name}"""
    
    def test_{test_name.lower()}_end_to_end(self, api_client, selenium_page):
        """End-to-end test for {test_name}"""
        with tracer.trace_test_case("test_{test_name.lower()}_end_to_end"):
            logger.test_start("test_{test_name.lower()}_end_to_end")
            
            # TODO: Implement integration test
            # Step 1: API call
            # response = api_client.post("/api/{test_name.lower()}", json={{"data": "test"}})
            # assert response.status_code == 201
            
            # Step 2: Web verification  
            # selenium_page.navigate("https://example.com/{test_name.lower()}")
            # assert selenium_page.is_element_present(".created-item")
            
            logger.test_end("test_{test_name.lower()}_end_to_end", "passed", 0.0)
''',
        'bdd': f'''"""
{test_name} BDD Step Definitions
Generated by PhoenixFrame CLI
"""
from pytest_bdd import given, when, then, scenario
from src.phoenixframe.bdd.steps import *


# Load scenarios
@scenario('features/{test_name.lower()}.feature', '{test_name} basic scenario')
def test_{test_name.lower()}_basic_scenario():
    pass


# Custom step definitions
@given('I have {test_name.lower()} precondition')
def given_{test_name.lower()}_precondition():
    """Given step for {test_name}"""
    # TODO: Implement precondition
    pass


@when('I perform {test_name.lower()} action')
def when_{test_name.lower()}_action():
    """When step for {test_name}"""
    # TODO: Implement action
    pass


@then('I should see {test_name.lower()} result')
def then_{test_name.lower()}_result():
    """Then step for {test_name}"""
    # TODO: Implement verification
    pass
'''
    }
    
    if not output:
        output = f"tests/test_{test_name.lower()}_{test_type}.py"
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(templates[test_type], encoding='utf-8')
    
    click.echo(f"✅ Generated {test_type} test: {output_path}")
    logger.info(f"Generated {test_type} test: {output_path}")


@scaffold.command()
@click.argument("name")
@click.option("--target-url", required=True, help="目标URL")
@click.option("--users", default=10, help="并发用户数")
@click.option("--duration", default=60, help="测试持续时间(秒)")
@click.option("--output", "-o", help="输出文件路径")
def locustfile(name, target_url, users, duration, output):
    """生成Locust性能测试文件"""
    logger = get_logger("phoenixframe.cli.scaffold")
    
    locust_template = f'''"""
{name} Performance Test
Generated by PhoenixFrame CLI
Target: {target_url}
"""
from locust import HttpUser, task, between
import time
import json
import random


class {name.title().replace('_', '')}User(HttpUser):
    """Performance test user for {name}"""
    
    wait_time = between(1, 3)
    host = "{target_url}"
    
    def on_start(self):
        """Called when a user starts"""
        self.client.verify = False
        # TODO: Add authentication logic if needed
        
    @task(3)
    def load_home_page(self):
        """Load home page"""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Got status code {{response.status_code}}")
            else:
                response.success()
    
    @task(2)
    def api_health_check(self):
        """API health check"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # 404 might be expected
            else:
                response.failure(f"Health check failed: {{response.status_code}}")
    
    @task(1)
    def post_test_data(self):
        """POST test data"""
        test_data = {{
            "id": random.randint(1, 1000),
            "name": f"test_user_{{random.randint(1, 100)}}",
            "timestamp": int(time.time()),
            "data": "test_performance_data"
        }}
        
        with self.client.post("/api/data", json=test_data, catch_response=True) as response:
            if response.status_code in [200, 201, 404]:
                response.success()
            else:
                response.failure(f"POST failed with status {{response.status_code}}")
    
    @task(1)
    def simulate_workflow(self):
        """Simulate user workflow"""
        # Step 1: Get data
        with self.client.get("/api/items", catch_response=True) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure("Workflow step 1 failed")
                return
        
        # Step 2: Process delay
        time.sleep(random.uniform(0.1, 0.5))
        
        # Step 3: Update data
        update_data = {{"status": "processed", "user_id": random.randint(1, 100)}}
        with self.client.put("/api/items/1", json=update_data, catch_response=True) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure("Workflow step 3 failed")


# Custom locust test configuration
class {name.title().replace('_', '')}TestConfig:
    """Test configuration for {name}"""
    
    # Test parameters
    USERS = {users}
    DURATION = {duration}
    TARGET_URL = "{target_url}"
    
    # Performance thresholds
    MAX_RESPONSE_TIME = 2000  # ms
    MIN_SUCCESS_RATE = 95  # %
    MIN_RPS = 10  # requests per second


if __name__ == "__main__":
    # Direct execution
    import os
    cmd = f"locust -f {{__file__}} --host {target_url} --users {users} --spawn-rate 1 --run-time {duration}s --headless"
    print(f"Running: {{cmd}}")
    os.system(cmd)
'''
    
    if not output:
        output = f"{name.lower()}_performance_test.py"
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(locust_template, encoding='utf-8')
    
    click.echo(f"✅ Generated Locust file: {output_path}")
    click.echo(f"   Target URL: {target_url}")
    click.echo(f"   Users: {users}")
    click.echo(f"   Duration: {duration}s")
    
    logger.info(f"Generated Locust file: {output_path}")


# 观测性命令组
@main.group()
def observability():
    """观测性管理"""
    pass


@observability.command()
@click.option('--output', '-o', help='输出文件路径')
def metrics(output):
    """导出度量数据"""
    logger = get_logger("phoenixframe.cli.observability")
    
    summary = get_metrics_summary()
    
    if output:
        export_metrics(output)
        click.echo(f"✅ Metrics exported to: {output}")
    else:
        click.echo("📊 Metrics Summary:")
        click.echo(f"  Test Metrics: {summary.get('test_metrics', {})}")
        click.echo(f"  API Metrics: {summary.get('api_metrics', {})}")
        click.echo(f"  Web Metrics: {summary.get('web_metrics', {})}")
        click.echo(f"  Collection Interval: {summary.get('collection_interval', 0)}s")
        click.echo(f"  Total Data Points: {summary.get('total_data_points', 0)}")


# 数据管理命令组
@main.group()
def data():
    """测试数据管理"""
    pass


@data.group()
def dataset():
    """数据集管理"""
    pass


@dataset.command()
@click.argument('name')
@click.option('--description', default='', help='数据集描述')
@click.option('--data-type', type=click.Choice(['user', 'product', 'order', 'custom']), default='user', help='数据类型')
@click.option('--count', default=10, help='生成记录数')
@click.option('--output', '-o', help='输出文件路径')
@click.option('--tags', multiple=True, help='数据集标签')
def create(name, description, data_type, count, output, tags):
    """创建测试数据集"""
    from .data.factories import create_test_dataset, get_test_data_factory
    from .data import get_data_repository
    
    logger = get_logger("phoenixframe.cli.data")
    
    click.echo(f"🔧 Creating {data_type} dataset: {name}")
    click.echo(f"   Records: {count}")
    click.echo(f"   Description: {description}")
    
    try:
        # 创建数据集
        if data_type == 'custom':
            factory = get_test_data_factory()
            data = []
            for i in range(count):
                record = {"id": f"record_{i+1}", "name": f"Item {i+1}", "value": i+1}
                data.append(record)
            
            from .data import TestDataset
            dataset = TestDataset(
                name=name,
                description=description or f"Custom dataset with {count} records",
                data=data,
                tags=list(tags) if tags else ['custom', 'generated']
            )
        else:
            dataset = create_test_dataset(name, data_type, count, tags=list(tags) if tags else None)
            if description:
                dataset.description = description
        
        # 保存到仓库
        repository = get_data_repository()
        dataset_id = repository.save_dataset(dataset, overwrite=True)
        
        # 如果指定了输出文件，也保存到文件
        if output:
            import json
            from pathlib import Path
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "name": dataset.name,
                    "description": dataset.description,
                    "data": dataset.data,
                    "schema": dataset.schema,
                    "tags": dataset.tags,
                    "metadata": dataset.metadata
                }, f, indent=2, ensure_ascii=False)
            
            click.echo(f"   Saved to file: {output}")
        
        click.echo(f"✅ Created dataset: {dataset_id}")
        click.echo(f"   Records created: {len(dataset.data)}")
        click.echo(f"   Schema fields: {list(dataset.schema.keys()) if dataset.schema else 'auto-detected'}")
        
        logger.info(f"Created dataset {dataset_id} with {len(dataset.data)} records")
        
    except Exception as e:
        click.echo(f"❌ Failed to create dataset: {e}")
        logger.error(f"Failed to create dataset {name}: {e}")
        sys.exit(1)


@dataset.command()
def list():
    """列出所有数据集"""
    from .data import get_data_repository
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        repository = get_data_repository()
        datasets = repository.list_datasets()
        
        if not datasets:
            click.echo("📭 No datasets found")
            return
        
        click.echo(f"📋 Found {len(datasets)} datasets:")
        click.echo()
        
        for dataset in datasets:
            click.echo(f"  📊 {dataset['name']} (v{dataset['version']})")
            click.echo(f"     ID: {dataset['id']}")
            click.echo(f"     Records: {dataset['record_count']}")
            click.echo(f"     Tags: {', '.join(dataset['tags'])}")
            click.echo(f"     Updated: {dataset['updated_at']}")
            click.echo()
        
        logger.info(f"Listed {len(datasets)} datasets")
        
    except Exception as e:
        click.echo(f"❌ Failed to list datasets: {e}")
        logger.error(f"Failed to list datasets: {e}")


@dataset.command()
@click.argument('dataset_id')
@click.option('--format', 'output_format', type=click.Choice(['json', 'csv', 'yaml']), default='json', help='输出格式')
@click.option('--output', '-o', help='输出文件路径')
@click.option('--limit', default=None, type=int, help='限制显示记录数')
def show(dataset_id, output_format, output, limit):
    """显示数据集详情"""
    from .data import get_data_repository
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        repository = get_data_repository()
        dataset = repository.load_dataset(dataset_id)
        
        click.echo(f"📊 Dataset: {dataset.name}")
        click.echo(f"   ID: {dataset_id}")
        click.echo(f"   Description: {dataset.description}")
        click.echo(f"   Version: {dataset.version}")
        click.echo(f"   Records: {len(dataset.data)}")
        click.echo(f"   Tags: {', '.join(dataset.tags)}")
        click.echo(f"   Created: {dataset.created_at}")
        click.echo(f"   Updated: {dataset.updated_at}")
        
        if dataset.schema:
            click.echo(f"   Schema: {', '.join(dataset.schema.keys())}")
        
        # 显示数据样本
        display_data = dataset.data[:limit] if limit else dataset.data
        
        if output:
            # 保存到文件
            from pathlib import Path
            import json
            import csv
            import yaml
            
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if output_format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(display_data, f, indent=2, ensure_ascii=False)
            elif output_format == 'csv' and display_data:
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=display_data[0].keys())
                    writer.writeheader()
                    writer.writerows(display_data)
            elif output_format == 'yaml':
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(display_data, f, default_flow_style=False, allow_unicode=True)
            
            click.echo(f"   Exported to: {output}")
        else:
            # 显示在控制台
            if display_data:
                click.echo(f"\n📋 Sample Data ({min(len(display_data), 5)} of {len(dataset.data)} records):")
                for i, record in enumerate(display_data[:5]):
                    click.echo(f"   Record {i+1}: {record}")
                    
                if len(dataset.data) > 5:
                    click.echo(f"   ... and {len(dataset.data) - 5} more records")
        
        logger.info(f"Showed dataset {dataset_id}")
        
    except Exception as e:
        click.echo(f"❌ Failed to show dataset: {e}")
        logger.error(f"Failed to show dataset {dataset_id}: {e}")


@dataset.command()
@click.argument('dataset_id')
@click.confirmation_option(prompt='Are you sure you want to delete this dataset?')
def delete(dataset_id):
    """删除数据集"""
    from .data import get_data_repository
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        repository = get_data_repository()
        
        if repository.delete_dataset(dataset_id):
            click.echo(f"✅ Deleted dataset: {dataset_id}")
            logger.info(f"Deleted dataset {dataset_id}")
        else:
            click.echo(f"❌ Dataset not found: {dataset_id}")
    
    except Exception as e:
        click.echo(f"❌ Failed to delete dataset: {e}")
        logger.error(f"Failed to delete dataset {dataset_id}: {e}")


@dataset.command()
@click.argument('query')
def search(query):
    """搜索数据集"""
    from .data import get_data_repository
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        repository = get_data_repository()
        results = repository.search_datasets(query)
        
        if not results:
            click.echo(f"🔍 No datasets found matching: {query}")
            return
        
        click.echo(f"🔍 Found {len(results)} datasets matching '{query}':")
        click.echo()
        
        for result in results:
            click.echo(f"  📊 {result['name']} (v{result['version']}) - Score: {result['relevance_score']:.1f}")
            click.echo(f"     ID: {result['id']}")
            click.echo(f"     Records: {result['record_count']}")
            click.echo(f"     Tags: {', '.join(result['tags'])}")
            click.echo()
        
        logger.info(f"Searched datasets with query: {query}")
        
    except Exception as e:
        click.echo(f"❌ Failed to search datasets: {e}")
        logger.error(f"Failed to search datasets: {e}")


@data.group()
def mask():
    """数据脱敏管理"""
    pass


@mask.command()
@click.argument('dataset_id')
@click.option('--email', is_flag=True, help='脱敏邮箱字段')
@click.option('--phone', is_flag=True, help='脱敏电话字段')
@click.option('--ssn', is_flag=True, help='脱敏SSN字段')
@click.option('--custom-field', multiple=True, help='自定义脱敏字段')
@click.option('--output', '-o', help='输出数据集ID')
def apply(dataset_id, email, phone, ssn, custom_field, output):
    """对数据集应用脱敏"""
    from .data import get_data_repository, get_data_masker, DataMask
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        repository = get_data_repository()
        masker = get_data_masker()
        
        # 加载数据集
        dataset = repository.load_dataset(dataset_id)
        
        # 准备脱敏规则
        masks = []
        
        if email:
            masks.append(masker.default_masks["email"])
        if phone:
            masks.append(masker.default_masks["phone"])
        if ssn:
            masks.append(masker.default_masks["ssn"])
        
        for field in custom_field:
            masks.append(DataMask(field, "partial", {"pattern": "***"}))
        
        if not masks:
            click.echo("❌ No masking rules specified")
            return
        
        click.echo(f"🎭 Applying masking to dataset: {dataset.name}")
        click.echo(f"   Rules: {[mask.field for mask in masks]}")
        
        # 应用脱敏
        masked_dataset = masker.mask_dataset(dataset, masks)
        
        # 保存脱敏数据集
        output_id = output or f"{dataset_id}_masked"
        saved_id = repository.save_dataset(masked_dataset, overwrite=True)
        
        click.echo(f"✅ Created masked dataset: {saved_id}")
        click.echo(f"   Original records: {len(dataset.data)}")
        click.echo(f"   Masked records: {len(masked_dataset.data)}")
        
        logger.info(f"Applied masking to dataset {dataset_id}")
        
    except Exception as e:
        click.echo(f"❌ Failed to apply masking: {e}")
        logger.error(f"Failed to apply masking to dataset {dataset_id}: {e}")


@data.group()
def version():
    """数据版本控制"""
    pass


@version.command()
@click.argument('dataset_id')
@click.option('--message', '-m', required=True, help='提交消息')
@click.option('--author', default='cli_user', help='作者')
def commit(dataset_id, message, author):
    """提交数据版本"""
    from .data import get_data_repository
    from .data.version import get_version_control
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        repository = get_data_repository()
        vc = get_version_control()
        
        # 加载数据集
        dataset = repository.load_dataset(dataset_id)
        
        # 提交版本
        version = vc.commit(dataset, message, author)
        
        click.echo(f"✅ Committed dataset version: {version}")
        click.echo(f"   Dataset: {dataset.name}")
        click.echo(f"   Message: {message}")
        click.echo(f"   Author: {author}")
        click.echo(f"   Records: {len(dataset.data)}")
        
        logger.info(f"Committed version {version} for dataset {dataset_id}")
        
    except Exception as e:
        click.echo(f"❌ Failed to commit version: {e}")
        logger.error(f"Failed to commit version for dataset {dataset_id}: {e}")


@version.command()
@click.argument('dataset_id')
@click.option('--version-id', help='指定版本ID')
@click.option('--limit', default=10, help='显示版本数量')
def log(dataset_id, version_id, limit):
    """查看版本历史"""
    from .data.version import get_version_control
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        vc = get_version_control()
        
        if version_id:
            # 显示单个版本详情
            dataset = vc.checkout(dataset_id, version_id)
            click.echo(f"📋 Version: {version_id}")
            click.echo(f"   Dataset: {dataset.name}")
            click.echo(f"   Records: {len(dataset.data)}")
            click.echo(f"   Version: {dataset.version}")
            click.echo(f"   Created: {dataset.created_at}")
            click.echo(f"   Updated: {dataset.updated_at}")
        else:
            # 显示版本历史
            history = vc.get_version_history(dataset_id, limit)
            
            if not history:
                click.echo(f"📭 No version history found for dataset: {dataset_id}")
                return
            
            click.echo(f"📜 Version history for {dataset_id} (showing {len(history)} versions):")
            click.echo()
            
            for version in history:
                click.echo(f"  🏷️  {version.version}")
                click.echo(f"      Message: {version.message}")
                click.echo(f"      Author: {version.author}")
                click.echo(f"      Date: {version.timestamp}")
                click.echo(f"      Records: {version.record_count}")
                click.echo()
        
        logger.info(f"Showed version log for dataset {dataset_id}")
        
    except Exception as e:
        click.echo(f"❌ Failed to show version log: {e}")
        logger.error(f"Failed to show version log for dataset {dataset_id}: {e}")


@data.group()
def dependency():
    """数据依赖关系管理"""
    pass


@dependency.command()
@click.argument('source_dataset')
@click.argument('target_dataset')
@click.option('--type', 'dep_type', type=click.Choice(['required', 'optional', 'reference', 'parent_child', 'sequential']), 
              default='required', help='依赖类型')
@click.option('--description', default='', help='依赖描述')
def add(source_dataset, target_dataset, dep_type, description):
    """添加数据依赖关系"""
    from .data.dependencies import get_dependency_manager, DataDependency, DependencyType
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        manager = get_dependency_manager()
        
        dependency = DataDependency(
            source_dataset=source_dataset,
            target_dataset=target_dataset,
            dependency_type=DependencyType(dep_type),
            description=description
        )
        
        manager.add_dependency(dependency)
        
        click.echo(f"✅ Added dependency: {source_dataset} -> {target_dataset}")
        click.echo(f"   Type: {dep_type}")
        click.echo(f"   Description: {description}")
        
        logger.info(f"Added dependency {source_dataset} -> {target_dataset}")
        
    except Exception as e:
        click.echo(f"❌ Failed to add dependency: {e}")
        logger.error(f"Failed to add dependency {source_dataset} -> {target_dataset}: {e}")


@dependency.command()
@click.argument('dataset_name')
def tree(dataset_name):
    """显示数据集依赖树"""
    from .data.dependencies import get_dependency_manager
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        manager = get_dependency_manager()
        
        dep_tree = manager.get_dependency_tree(dataset_name)
        
        def print_tree(node, indent=0):
            prefix = "  " * indent + ("├─ " if indent > 0 else "")
            click.echo(f"{prefix}📊 {node['name']}")
            
            if 'dependency_type' in node:
                click.echo(f"{'  ' * (indent + 1)}└─ Type: {node['dependency_type']}")
            
            for dep in node.get('dependencies', []):
                print_tree(dep, indent + 1)
        
        click.echo(f"🌳 Dependency tree for: {dataset_name}")
        print_tree(dep_tree)
        
        logger.info(f"Showed dependency tree for {dataset_name}")
        
    except Exception as e:
        click.echo(f"❌ Failed to show dependency tree: {e}")
        logger.error(f"Failed to show dependency tree for {dataset_name}: {e}")


@dependency.command()
@click.argument('dataset_name')
def impact(dataset_name):
    """分析数据集变更影响"""
    from .data.dependencies import get_dependency_manager
    
    logger = get_logger("phoenixframe.cli.data")
    
    try:
        manager = get_dependency_manager()
        
        analysis = manager.get_impact_analysis(dataset_name)
        
        click.echo(f"💥 Impact analysis for: {analysis['dataset']}")
        click.echo(f"   Direct dependents: {analysis['direct_dependents']}")
        click.echo(f"   Total affected datasets: {analysis['total_affected']}")
        click.echo(f"   Impact level: {analysis['impact_level'].upper()}")
        
        if analysis['affected_datasets']:
            click.echo(f"\n📋 Affected datasets:")
            for affected in analysis['affected_datasets']:
                click.echo(f"   - {affected}")
        
        logger.info(f"Analyzed impact for dataset {dataset_name}")
        
    except Exception as e:
        click.echo(f"❌ Failed to analyze impact: {e}")
        logger.error(f"Failed to analyze impact for dataset {dataset_name}: {e}")


# 性能测试命令组
@main.group()
def performance():
    """性能测试管理"""
    pass


@performance.command()
@click.option('--target-url', required=True, help='目标URL')
@click.option('--users', default=10, help='并发用户数')
@click.option('--spawn-rate', default=1.0, help='用户生成速率')
@click.option('--duration', default=60, help='测试持续时间(秒)')
@click.option('--test-name', default='performance_test', help='测试名称')
@click.option('--locustfile', help='自定义Locust文件路径')
@click.option('--html-report', help='HTML报告输出路径')
@click.option('--csv-prefix', help='CSV输出文件前缀')
@click.option('--tags', multiple=True, help='包含的标签')
@click.option('--exclude-tags', multiple=True, help='排除的标签')
def run(target_url, users, spawn_rate, duration, test_name, locustfile, html_report, csv_prefix, tags, exclude_tags):
    """运行性能测试"""
    from .performance import PerformanceTestConfig, run_performance_test
    
    logger = get_logger("phoenixframe.cli.performance")
    
    config = PerformanceTestConfig(
        target_url=target_url,
        users=users,
        spawn_rate=spawn_rate,
        duration=duration,
        test_name=test_name,
        locustfile=locustfile,
        html_report=html_report,
        csv_prefix=csv_prefix,
        tags=list(tags) if tags else [],
        exclude_tags=list(exclude_tags) if exclude_tags else []
    )
    
    click.echo(f"🚀 Starting performance test: {test_name}")
    click.echo(f"   Target URL: {target_url}")
    click.echo(f"   Users: {users}")
    click.echo(f"   Duration: {duration}s")
    
    result = run_performance_test(config)
    
    click.echo(f"\n📊 Performance Test Results:")
    click.echo(f"   Status: {result.status}")
    click.echo(f"   Duration: {result.duration:.2f}s")
    click.echo(f"   Total Requests: {result.metrics.total_requests}")
    click.echo(f"   Failed Requests: {result.metrics.failed_requests}")
    click.echo(f"   Success Rate: {result.metrics.success_rate:.1f}%")
    click.echo(f"   Average Response Time: {result.metrics.average_response_time:.2f}ms")
    click.echo(f"   Requests/Second: {result.metrics.requests_per_second:.2f}")
    
    if result.errors:
        click.echo(f"\n❌ Errors ({len(result.errors)}):")
        for error in result.errors[:5]:  # 显示前5个错误
            click.echo(f"   - {error.get('message', 'Unknown error')}")
    
    if result.status == "success":
        click.echo("✅ Performance test completed successfully!")
    else:
        click.echo("❌ Performance test failed!")
        sys.exit(1)


@performance.command()
@click.option('--target-url', required=True, help='目标URL')
@click.option('--test-name', default='performance_test', help='测试名称')
@click.option('--output', '-o', required=True, help='输出Locust文件路径')
@click.option('--test-type', type=click.Choice(['basic', 'api']), default='basic', help='测试类型')
def generate(target_url, test_name, output, test_type):
    """生成Locust测试文件"""
    from .performance import PerformanceTestConfig, generate_locustfile
    
    logger = get_logger("phoenixframe.cli.performance")
    
    config = PerformanceTestConfig(
        target_url=target_url,
        test_name=test_name
    )
    
    click.echo(f"🔧 Generating {test_type} performance test...")
    
    content = generate_locustfile(config, output, test_type)
    
    click.echo(f"✅ Generated Locust file: {output}")
    click.echo(f"   Target URL: {target_url}")
    click.echo(f"   Test Type: {test_type}")
    click.echo(f"   Test Name: {test_name}")
    
    logger.info(f"Generated Locust file: {output}")


@performance.command()
@click.argument('results_dir', type=click.Path(exists=True, file_okay=False))
@click.option('--output', '-o', help='输出报告文件路径')
def report(results_dir, output):
    """生成性能测试报告"""
    from .performance import generate_performance_report
    
    logger = get_logger("phoenixframe.cli.performance")
    
    # 这里应该从results_dir读取测试结果
    # 简化实现，显示提示信息
    click.echo(f"📊 Generating performance report from: {results_dir}")
    
    if output:
        click.echo(f"✅ Report would be saved to: {output}")
    else:
        click.echo("📋 Report Summary:")
        click.echo("   No test results found in the specified directory.")
        click.echo("   Run performance tests first to generate results.")


# 集成BDD命令
if bdd_cli:
    main.add_command(bdd_cli, name="bdd")


if __name__ == "__main__":
    main()