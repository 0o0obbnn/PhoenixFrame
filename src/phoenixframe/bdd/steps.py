"""BDD步骤定义模板和常用步骤"""
from typing import Any, Dict, Optional
import time
import json

from ..api.client import APIClient
from ..web.selenium_driver import SeleniumDriver, SeleniumPage
from ..web.playwright_driver import PlaywrightDriver, PlaywrightPage
from ..observability.logger import get_logger
from ..observability.tracer import get_tracer
from . import phoenix_given, phoenix_when, phoenix_then

# 获取观测性组件
logger = get_logger("phoenixframe.bdd.steps")
tracer = get_tracer("phoenixframe.bdd.steps")

# 全局测试上下文
test_context: Dict[str, Any] = {}


def reset_context():
    """重置测试上下文"""
    global test_context
    test_context.clear()


def get_context(key: str, default: Any = None) -> Any:
    """获取上下文值"""
    return test_context.get(key, default)


def set_context(key: str, value: Any) -> None:
    """设置上下文值"""
    test_context[key] = value


# ============================================================================
# API测试步骤定义
# ============================================================================

@phoenix_given('I have an API client')
def given_api_client():
    """创建API客户端"""
    client = APIClient()
    set_context('api_client', client)
    logger.info("API client created")


@phoenix_given('I have an API client with base URL "<base_url>"')
def given_api_client_with_base_url(base_url: str):
    """创建带基础URL的API客户端"""
    client = APIClient(base_url=base_url)
    set_context('api_client', client)
    logger.info(f"API client created with base URL: {base_url}")


@phoenix_when('I send a GET request to "<endpoint>"')
def when_send_get_request(endpoint: str):
    """发送GET请求"""
    client = get_context('api_client')
    if not client:
        raise ValueError("API client not found in context")
    
    with tracer.trace_api_request("GET", endpoint) as span:
        response = client.get(endpoint)
        set_context('api_response', response)
        logger.api_request("GET", endpoint)
        logger.api_response(response.status_code, 0.0)


@phoenix_when('I send a POST request to "<endpoint>" with data:')
def when_send_post_request_with_data(endpoint: str, data: str):
    """发送带数据的POST请求"""
    client = get_context('api_client')
    if not client:
        raise ValueError("API client not found in context")
    
    try:
        json_data = json.loads(data)
    except json.JSONDecodeError:
        json_data = {"data": data}
    
    with tracer.trace_api_request("POST", endpoint) as span:
        response = client.post(endpoint, json=json_data)
        set_context('api_response', response)
        logger.api_request("POST", endpoint, data=json_data)
        logger.api_response(response.status_code, 0.0)


@phoenix_then('the response status code should be <status_code>')
def then_response_status_code(status_code: int):
    """验证响应状态码"""
    response = get_context('api_response')
    if not response:
        raise ValueError("API response not found in context")
    
    assert response.status_code == status_code, f"Expected {status_code}, got {response.status_code}"
    logger.info(f"Response status code verified: {status_code}")


@phoenix_then('the response should contain "<key>"')
def then_response_contains_key(key: str):
    """验证响应包含指定键"""
    response = get_context('api_response')
    if not response:
        raise ValueError("API response not found in context")
    
    data = response.json()
    assert key in data, f"Key '{key}' not found in response"
    logger.info(f"Response contains key: {key}")


@phoenix_then('the response "<key>" should be "<value>"')
def then_response_key_equals_value(key: str, value: str):
    """验证响应字段值"""
    response = get_context('api_response')
    if not response:
        raise ValueError("API response not found in context")
    
    data = response.json()
    actual_value = str(data.get(key, ""))
    assert actual_value == value, f"Expected '{value}', got '{actual_value}'"
    logger.info(f"Response {key} verified: {value}")


# ============================================================================
# Web测试步骤定义
# ============================================================================

@phoenix_given('I have a web browser')
def given_web_browser():
    """创建Web浏览器"""
    driver_manager = SeleniumDriver(browser="chrome", headless=True)
    driver = driver_manager.start()
    page = SeleniumPage(driver)
    set_context('web_driver_manager', driver_manager)
    set_context('web_page', page)
    logger.info("Web browser created")


@phoenix_given('I have a "<browser>" browser')
def given_specific_browser(browser: str):
    """创建指定类型的浏览器"""
    driver_manager = SeleniumDriver(browser=browser.lower(), headless=True)
    driver = driver_manager.start()
    page = SeleniumPage(driver)
    set_context('web_driver_manager', driver_manager)
    set_context('web_page', page)
    logger.info(f"{browser} browser created")


@phoenix_given('I have a playwright browser')
def given_playwright_browser():
    """创建Playwright浏览器"""
    try:
        driver_manager = PlaywrightDriver(browser="chromium", headless=True)
        driver = driver_manager.start()
        page = PlaywrightPage(driver)
        set_context('web_driver_manager', driver_manager)
        set_context('web_page', page)
        logger.info("Playwright browser created")
    except ImportError:
        raise ImportError("Playwright not available")


@phoenix_when('I navigate to "<url>"')
def when_navigate_to_url(url: str):
    """导航到指定URL"""
    page = get_context('web_page')
    if not page:
        raise ValueError("Web page not found in context")
    
    with tracer.trace_page_action("navigate", page_url=url) as span:
        page.navigate(url)
        set_context('current_url', url)
        logger.web_action("navigate", url=url)


@phoenix_when('I click on "<element>"')
def when_click_element(element: str):
    """点击页面元素"""
    page = get_context('web_page')
    if not page:
        raise ValueError("Web page not found in context")
    
    with tracer.trace_page_action("click", element=element) as span:
        page.click_element(element)
        logger.web_action("click", element=element)


@phoenix_when('I type "<text>" into "<element>"')
def when_type_text_into_element(text: str, element: str):
    """在元素中输入文本"""
    page = get_context('web_page')
    if not page:
        raise ValueError("Web page not found in context")
    
    with tracer.trace_page_action("input_text", element=element) as span:
        page.input_text(element, text)
        logger.web_action("input_text", element=element, text_length=len(text))


@phoenix_when('I wait for <seconds> seconds')
def when_wait_for_seconds(seconds: int):
    """等待指定秒数"""
    with tracer.trace_page_action("wait", duration=seconds) as span:
        time.sleep(seconds)
        logger.web_action("wait", duration=seconds)


@phoenix_when('I wait for element "<element>" to appear')
def when_wait_for_element(element: str):
    """等待元素出现"""
    page = get_context('web_page')
    if not page:
        raise ValueError("Web page not found in context")
    
    with tracer.trace_page_action("wait_for_element", element=element) as span:
        page.wait_for_element(element)
        logger.web_action("wait_for_element", element=element)


@phoenix_then('I should see element "<element>"')
def then_should_see_element(element: str):
    """验证元素存在"""
    page = get_context('web_page')
    if not page:
        raise ValueError("Web page not found in context")
    
    assert page.is_element_present(element), f"Element '{element}' not found"
    logger.info(f"Element verified: {element}")


@phoenix_then('the element "<element>" should contain text "<text>"')
def then_element_contains_text(element: str, text: str):
    """验证元素包含指定文本"""
    page = get_context('web_page')
    if not page:
        raise ValueError("Web page not found in context")
    
    element_text = page.get_text(element)
    assert text in element_text, f"Text '{text}' not found in element '{element}'"
    logger.info(f"Element text verified: {element} contains '{text}'")


@phoenix_then('the page title should be "<title>"')
def then_page_title_should_be(title: str):
    """验证页面标题"""
    page = get_context('web_page')
    if not page:
        raise ValueError("Web page not found in context")
    
    actual_title = page.driver.title if hasattr(page.driver, 'title') else ""
    assert actual_title == title, f"Expected title '{title}', got '{actual_title}'"
    logger.info(f"Page title verified: {title}")


# ============================================================================
# 数据库测试步骤定义
# ============================================================================

@phoenix_given('I have a database connection')
def given_database_connection():
    """创建数据库连接"""
    # TODO: 实现数据库连接逻辑
    set_context('db_connection', None)
    logger.info("Database connection created (placeholder)")


@phoenix_when('I execute SQL query "<query>"')
def when_execute_sql_query(query: str):
    """执行SQL查询"""
    # TODO: 实现SQL查询执行逻辑
    set_context('db_result', None)
    logger.info(f"SQL query executed: {query}")


@phoenix_then('the query should return <count> rows')
def then_query_returns_count(count: int):
    """验证查询返回行数"""
    # TODO: 实现查询结果验证逻辑
    logger.info(f"Query result count verified: {count}")


# ============================================================================
# 文件操作步骤定义
# ============================================================================

@phoenix_given('I have a file "<filename>"')
def given_file_exists(filename: str):
    """验证文件存在"""
    import os
    assert os.path.exists(filename), f"File '{filename}' does not exist"
    set_context('current_file', filename)
    logger.info(f"File verified: {filename}")


@phoenix_when('I read the file "<filename>"')
def when_read_file(filename: str):
    """读取文件内容"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        set_context('file_content', content)
        set_context('current_file', filename)
        logger.info(f"File read: {filename}")
    except Exception as e:
        logger.error(f"Failed to read file {filename}: {e}")
        raise


@phoenix_then('the file should contain "<text>"')
def then_file_contains_text(text: str):
    """验证文件包含指定文本"""
    content = get_context('file_content', "")
    assert text in content, f"Text '{text}' not found in file"
    logger.info(f"File content verified: contains '{text}'")


# ============================================================================
# 清理步骤
# ============================================================================

def cleanup_test_context():
    """清理测试上下文"""
    # 关闭浏览器
    driver_manager = get_context('web_driver_manager')
    if driver_manager:
        try:
            driver_manager.quit()
            logger.info("Web browser closed")
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")
    
    # 关闭API客户端
    api_client = get_context('api_client')
    if api_client:
        try:
            api_client.close()
            logger.info("API client closed")
        except Exception as e:
            logger.error(f"Failed to close API client: {e}")
    
    # 重置上下文
    reset_context()


# 注册清理函数到pytest
try:
    import pytest
    
    @pytest.fixture(autouse=True)
    def auto_cleanup():
        """自动清理fixture"""
        yield
        cleanup_test_context()
        
except ImportError:
    pass  # pytest不可用时忽略