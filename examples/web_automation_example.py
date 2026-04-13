"""
Web自动化综合示例
演示PhoenixFrame的Web自动化测试功能
包括Selenium和Playwright的使用模式
"""
import sys
import time
from pathlib import Path

# 添加src路径以便导入模块
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.phoenixframe.web.base_page import BasePage
from src.phoenixframe.observability.logger import get_logger, setup_logging

# 设置日志
setup_logging(level="INFO", enable_console=True)
logger = get_logger("web_automation_example")

try:
    from src.phoenixframe.web.selenium_driver import SeleniumDriver, SeleniumPage
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available. Install with: pip install selenium")

try:
    from src.phoenixframe.web.playwright_driver import PlaywrightDriver, PlaywrightPage
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available. Install with: pip install playwright")


class DemoLoginPage(BasePage):
    """示例登录页面对象"""
    
    def __init__(self, driver):
        super().__init__(driver)
        self.url = "https://httpbin.org/forms/post"
        
        # 页面元素定位器
        self.USERNAME_INPUT = "input[name='custname']"
        self.EMAIL_INPUT = "input[name='custemail']"
        self.SUBMIT_BUTTON = "input[type='submit']"
        self.RESULT_AREA = "pre"
    
    def navigate(self):
        """导航到登录页面"""
        self.driver.get(self.url)
        logger.info(f"Navigated to {self.url}")
    
    def fill_form(self, username: str, email: str):
        """填写表单"""
        try:
            # 填写用户名
            username_element = self.driver.find_element("css selector", self.USERNAME_INPUT)
            username_element.clear()
            username_element.send_keys(username)
            logger.info(f"Entered username: {username}")
            
            # 填写邮箱
            email_element = self.driver.find_element("css selector", self.EMAIL_INPUT)
            email_element.clear()
            email_element.send_keys(email)
            logger.info(f"Entered email: {email}")
            
        except Exception as e:
            logger.error(f"Failed to fill form: {e}")
            raise
    
    def submit_form(self):
        """提交表单"""
        try:
            submit_button = self.driver.find_element("css selector", self.SUBMIT_BUTTON)
            submit_button.click()
            logger.info("Clicked submit button")
            time.sleep(2)  # 等待页面响应
        except Exception as e:
            logger.error(f"Failed to submit form: {e}")
            raise
    
    def get_result_text(self):
        """获取结果文本"""
        try:
            result_element = self.driver.find_element("css selector", self.RESULT_AREA)
            return result_element.text
        except Exception as e:
            logger.error(f"Failed to get result: {e}")
            return ""


class DemoSearchPage(BasePage):
    """示例搜索页面对象"""
    
    def __init__(self, driver):
        super().__init__(driver)
        self.url = "https://httpbin.org/html"
        
        # 页面元素
        self.PAGE_TITLE = "h1"
        self.LINKS = "a"
    
    def navigate(self):
        """导航到搜索页面"""
        self.driver.get(self.url)
        logger.info(f"Navigated to {self.url}")
    
    def get_page_title(self):
        """获取页面标题"""
        try:
            title_element = self.driver.find_element("css selector", self.PAGE_TITLE)
            return title_element.text
        except Exception as e:
            logger.error(f"Failed to get page title: {e}")
            return ""
    
    def get_all_links(self):
        """获取所有链接"""
        try:
            link_elements = self.driver.find_elements("css selector", self.LINKS)
            links = []
            for element in link_elements:
                href = element.get_attribute("href")
                text = element.text
                if href:
                    links.append({"text": text, "href": href})
            return links
        except Exception as e:
            logger.error(f"Failed to get links: {e}")
            return []


def demo_selenium_automation():
    """演示Selenium自动化"""
    if not SELENIUM_AVAILABLE:
        logger.warning("Skipping Selenium demo - not available")
        return
    
    logger.info("=== Selenium Web Automation Demo ===")
    
    try:
        # 初始化Selenium驱动
        selenium_driver = SeleniumDriver(browser="chrome", headless=True)
        driver = selenium_driver.start()
        
        # 创建页面对象
        login_page = DemoLoginPage(driver)
        search_page = DemoSearchPage(driver)
        
        # 演示登录流程
        logger.info("--- Login Flow Demo ---")
        login_page.navigate()
        login_page.fill_form("testuser", "test@example.com")
        login_page.submit_form()
        
        result_text = login_page.get_result_text()
        if "testuser" in result_text and "test@example.com" in result_text:
            logger.info("✅ Login form submission successful")
        else:
            logger.warning("⚠️ Login form submission may have failed")
        
        # 演示搜索页面
        logger.info("--- Search Page Demo ---")
        search_page.navigate()
        
        page_title = search_page.get_page_title()
        logger.info(f"Page title: {page_title}")
        
        links = search_page.get_all_links()
        logger.info(f"Found {len(links)} links on the page")
        for i, link in enumerate(links[:3]):  # 显示前3个链接
            logger.info(f"  Link {i+1}: {link['text']} -> {link['href']}")
        
        logger.info("✅ Selenium automation demo completed successfully")
        
    except Exception as e:
        logger.error(f"Selenium demo failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        try:
            selenium_driver.quit()
        except:
            pass


def demo_playwright_automation():
    """演示Playwright自动化"""
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("Skipping Playwright demo - not available")
        return
    
    logger.info("=== Playwright Web Automation Demo ===")
    
    try:
        # 初始化Playwright驱动
        playwright_driver = PlaywrightDriver(browser="chromium", headless=True)
        page = playwright_driver.start()
        
        # 演示基本导航
        logger.info("--- Basic Navigation Demo ---")
        page.goto("https://httpbin.org/html")
        
        # 获取页面标题
        title = page.title()
        logger.info(f"Page title: {title}")
        
        # 获取页面内容
        h1_text = page.locator("h1").text_content()
        logger.info(f"H1 text: {h1_text}")
        
        # 演示表单操作
        logger.info("--- Form Interaction Demo ---")
        page.goto("https://httpbin.org/forms/post")
        
        # 填写表单
        page.fill("input[name='custname']", "playwright_user")
        page.fill("input[name='custemail']", "playwright@example.com")
        
        # 提交表单
        page.click("input[type='submit']")
        page.wait_for_load_state("networkidle")
        
        # 检查结果
        page_content = page.content()
        if "playwright_user" in page_content and "playwright@example.com" in page_content:
            logger.info("✅ Playwright form submission successful")
        else:
            logger.warning("⚠️ Playwright form submission may have failed")
        
        # 演示等待策略
        logger.info("--- Wait Strategies Demo ---")
        page.goto("https://httpbin.org/delay/2")
        
        # 等待页面完全加载
        page.wait_for_load_state("networkidle")
        logger.info("✅ Page loaded after delay")
        
        # 演示截图功能
        logger.info("--- Screenshot Demo ---")
        screenshot_path = Path(__file__).parent / "demo_screenshot.png"
        page.screenshot(path=str(screenshot_path))
        logger.info(f"Screenshot saved to: {screenshot_path}")
        
        logger.info("✅ Playwright automation demo completed successfully")
        
    except Exception as e:
        logger.error(f"Playwright demo failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        try:
            playwright_driver.quit()
        except:
            pass


def demo_cross_browser_testing():
    """演示跨浏览器测试"""
    logger.info("=== Cross-Browser Testing Demo ===")
    
    browsers_to_test = []
    
    if SELENIUM_AVAILABLE:
        browsers_to_test.append(("selenium", "chrome"))
        browsers_to_test.append(("selenium", "firefox"))
    
    if PLAYWRIGHT_AVAILABLE:
        browsers_to_test.append(("playwright", "chromium"))
        browsers_to_test.append(("playwright", "firefox"))
        browsers_to_test.append(("playwright", "webkit"))
    
    test_url = "https://httpbin.org/html"
    
    for driver_type, browser in browsers_to_test:
        try:
            logger.info(f"--- Testing with {driver_type} {browser} ---")
            
            if driver_type == "selenium" and SELENIUM_AVAILABLE:
                driver_manager = SeleniumDriver(browser=browser, headless=True)
                driver = driver_manager.start()
                driver.get(test_url)
                title = driver.title
                driver_manager.quit()
                
            elif driver_type == "playwright" and PLAYWRIGHT_AVAILABLE:
                driver_manager = PlaywrightDriver(browser=browser, headless=True)
                page = driver_manager.start()
                page.goto(test_url)
                title = page.title()
                driver_manager.quit()
            
            else:
                continue
            
            logger.info(f"✅ {driver_type} {browser}: Page title = {title}")
            
        except Exception as e:
            logger.error(f"❌ {driver_type} {browser} failed: {e}")


def demo_page_object_patterns():
    """演示页面对象模式最佳实践"""
    logger.info("=== Page Object Model Patterns Demo ===")
    
    # 如果两个框架都不可用，跳过演示
    if not (SELENIUM_AVAILABLE or PLAYWRIGHT_AVAILABLE):
        logger.warning("Skipping Page Object demo - no web drivers available")
        return
    
    # 选择可用的驱动
    if SELENIUM_AVAILABLE:
        driver_manager = SeleniumDriver(browser="chrome", headless=True)
        driver = driver_manager.start()
        
        # 演示页面对象组合
        logger.info("--- Page Object Composition ---")
        login_page = DemoLoginPage(driver)
        search_page = DemoSearchPage(driver)
        
        # 工作流演示
        logger.info("--- Workflow Demo ---")
        
        # 步骤1：访问登录页面
        login_page.navigate()
        logger.info("Step 1: Navigated to login page")
        
        # 步骤2：填写并提交表单
        login_page.fill_form("workflow_user", "workflow@example.com")
        logger.info("Step 2: Filled login form")
        
        login_page.submit_form()
        logger.info("Step 3: Submitted form")
        
        # 步骤4：验证结果
        result = login_page.get_result_text()
        if "workflow_user" in result:
            logger.info("Step 4: ✅ Workflow completed successfully")
        else:
            logger.warning("Step 4: ⚠️ Workflow verification failed")
        
        # 步骤5：导航到另一个页面
        search_page.navigate()
        title = search_page.get_page_title()
        logger.info(f"Step 5: Navigated to search page - {title}")
        
        driver_manager.quit()
        
    elif PLAYWRIGHT_AVAILABLE:
        driver_manager = PlaywrightDriver(browser="chromium", headless=True)
        page = driver_manager.start()
        
        # 简化的Playwright演示
        logger.info("--- Playwright Page Object Demo ---")
        page.goto("https://httpbin.org/forms/post")
        page.fill("input[name='custname']", "pw_workflow_user")
        page.fill("input[name='custemail']", "pw_workflow@example.com")
        page.click("input[type='submit']")
        page.wait_for_load_state("networkidle")
        
        content = page.content()
        if "pw_workflow_user" in content:
            logger.info("✅ Playwright workflow completed successfully")
        else:
            logger.warning("⚠️ Playwright workflow verification failed")
        
        driver_manager.quit()


def demo_error_handling_strategies():
    """演示错误处理策略"""
    logger.info("=== Error Handling Strategies Demo ===")
    
    if not (SELENIUM_AVAILABLE or PLAYWRIGHT_AVAILABLE):
        logger.warning("Skipping error handling demo - no web drivers available")
        return
    
    if SELENIUM_AVAILABLE:
        try:
            driver_manager = SeleniumDriver(browser="chrome", headless=True)
            driver = driver_manager.start()
            
            # 演示超时处理
            logger.info("--- Timeout Handling ---")
            driver.get("https://httpbin.org/delay/1")
            
            try:
                # 尝试查找不存在的元素
                driver.find_element("css selector", "#nonexistent-element")
            except Exception as e:
                logger.info(f"✅ Gracefully handled missing element: {type(e).__name__}")
            
            # 演示网络错误处理
            logger.info("--- Network Error Handling ---")
            try:
                driver.get("https://invalid-domain-that-does-not-exist.com")
            except Exception as e:
                logger.info(f"✅ Gracefully handled network error: {type(e).__name__}")
            
            driver_manager.quit()
            
        except Exception as e:
            logger.error(f"Error handling demo failed: {e}")


def main():
    """主演示函数"""
    logger.info("PhoenixFrame Web Automation Demo")
    logger.info("=" * 50)
    
    # 检查可用的Web驱动
    available_drivers = []
    if SELENIUM_AVAILABLE:
        available_drivers.append("Selenium")
    if PLAYWRIGHT_AVAILABLE:
        available_drivers.append("Playwright")
    
    if not available_drivers:
        logger.error("No web automation drivers available!")
        logger.info("Install drivers with:")
        logger.info("  pip install selenium")
        logger.info("  pip install playwright")
        logger.info("  playwright install")
        return
    
    logger.info(f"Available drivers: {', '.join(available_drivers)}")
    print()
    
    try:
        # 运行各个演示
        demo_selenium_automation()
        print()
        
        demo_playwright_automation()
        print()
        
        demo_cross_browser_testing()
        print()
        
        demo_page_object_patterns()
        print()
        
        demo_error_handling_strategies()
        print()
        
        logger.info("=== Demo Summary ===")
        if SELENIUM_AVAILABLE:
            logger.info("✅ Selenium automation patterns")
        if PLAYWRIGHT_AVAILABLE:
            logger.info("✅ Playwright automation patterns")
        logger.info("✅ Cross-browser testing strategies")
        logger.info("✅ Page Object Model patterns")
        logger.info("✅ Error handling strategies")
        
        logger.info("\n🎉 All web automation features demonstrated successfully!")
        
        # CLI使用示例
        logger.info("\n📋 CLI Usage Examples:")
        logger.info("# Generate page object from Playwright recording")
        logger.info("phoenix generate playwright-codegen recorded_script.py --output-pom login_page.py")
        logger.info("\n# Create page object scaffold")
        logger.info("phoenix scaffold page LoginPage --base-url https://app.example.com/login")
        logger.info("\n# Create web test scaffold")
        logger.info("phoenix scaffold test LoginTest --test-type web")
        logger.info("\n# Run web tests")
        logger.info("phoenix run tests/ -m web --env staging")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()