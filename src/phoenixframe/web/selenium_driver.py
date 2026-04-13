"""Selenium WebDriver封装"""
import time
from typing import Optional, Dict, Any

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
    WebDriverType = webdriver.Remote
except ImportError:
    webdriver = By = WebDriverWait = EC = ChromeOptions = FirefoxOptions = None
    TimeoutException = NoSuchElementException = None
    SELENIUM_AVAILABLE = False
    WebDriverType = Any

from .base_page import BasePage
from ..observability.tracer import get_tracer, is_tracing_enabled
from ..observability.logger import get_logger, log_web_action


class SeleniumDriver:
    """Selenium WebDriver管理器"""
    
    def __init__(self, browser: str = "chrome", headless: bool = False, options: Optional[Dict[str, Any]] = None):
        """
        初始化Selenium WebDriver
        
        Args:
            browser: 浏览器类型 ("chrome", "firefox")
            headless: 是否无头模式
            options: 额外的浏览器选项
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is not available. Install with: pip install selenium")
            
        self.browser = browser.lower()
        self.headless = headless
        self.options = options or {}
        self.driver: Optional[WebDriverType] = None
        
    def start(self) -> WebDriverType:
        """启动WebDriver"""
        if self.driver:
            return self.driver
            
        if self.browser == "chrome":
            chrome_options = ChromeOptions()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # 添加自定义选项
            for key, value in self.options.items():
                if isinstance(value, bool) and value:
                    chrome_options.add_argument(f"--{key}")
                elif not isinstance(value, bool):
                    chrome_options.add_argument(f"--{key}={value}")
                    
            self.driver = webdriver.Chrome(options=chrome_options)
            
        elif self.browser == "firefox":
            firefox_options = FirefoxOptions()
            if self.headless:
                firefox_options.add_argument("--headless")
                
            # 添加自定义选项
            for key, value in self.options.items():
                if isinstance(value, bool) and value:
                    firefox_options.add_argument(f"--{key}")
                elif not isinstance(value, bool):
                    firefox_options.add_argument(f"--{key}={value}")
                    
            self.driver = webdriver.Firefox(options=firefox_options)
            
        else:
            raise ValueError(f"Unsupported browser: {self.browser}")
            
        return self.driver
    
    def quit(self) -> None:
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def get_driver(self) -> Optional[WebDriverType]:
        """获取WebDriver实例"""
        return self.driver


class SeleniumPage(BasePage):
    """基于Selenium的页面对象"""
    
    def __init__(self, driver: WebDriverType):
        """
        初始化Selenium页面对象
        
        Args:
            driver: Selenium WebDriver实例
        """
        super().__init__(driver)
        self.wait = WebDriverWait(driver, 10)
        # 初始化观测性组件
        self.tracer = get_tracer("phoenixframe.web.selenium")
        self.logger = get_logger("phoenixframe.web.selenium")
        # 兼容属性：提供find_element以适配旧测试
    
    # 为向后兼容测试用例提供get方法别名
    def get(self, url: str) -> None:
        """兼容方法：导航到指定URL"""
        self.navigate(url)

    # 兼容方法：直接代理到底层driver
    def find_element(self, by: str, value: str):
        return self.driver.find_element(by, value)

    @property
    def title(self) -> str:
        """动态返回当前页面标题（兼容旧测试断言）。"""
        try:
            return getattr(self.driver, 'title', '')
        except Exception:
            return ""

    def navigate(self, url: Optional[str] = None) -> None:
        """导航到页面"""
        target_url = url or self.url
        if not target_url:
            raise ValueError("URL is required")
        
        # 记录导航操作
        start_time = time.time()
        with self.tracer.trace_page_action("navigate", page_url=target_url):
            self.driver.get(target_url)
            duration = time.time() - start_time
            self.logger.web_action("navigate", page_url=target_url, duration=duration)
    
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """等待页面加载完成"""
        try:
            start_time = time.time()
            with self.tracer.trace_page_action("wait_for_page_load", duration=timeout):
                WebDriverWait(self.driver, timeout).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                duration = time.time() - start_time
                self.logger.web_action("wait_for_page_load", duration=duration, outcome="success")
                return True
        except TimeoutException:
            duration = time.time() - start_time
            self.logger.web_action("wait_for_page_load", duration=duration, outcome="timeout")
            return False
    
    def is_element_present(self, locator: str) -> bool:
        """检查元素是否存在"""
        try:
            with self.tracer.trace_page_action("is_element_present", element=locator):
                self.driver.find_element(By.CSS_SELECTOR, locator)
                self.logger.web_action("is_element_present", element=locator, outcome="found")
                return True
        except NoSuchElementException:
            self.logger.web_action("is_element_present", element=locator, outcome="not_found")
            return False
    
    def click_element(self, locator: str) -> None:
        """点击元素"""
        start_time = time.time()
        with self.tracer.trace_page_action("click", element=locator):
            try:
                element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, locator)))
                element.click()
                duration = time.time() - start_time
                self.logger.web_action("click", element=locator, duration=duration, outcome="success")
            except Exception as e:
                duration = time.time() - start_time
                self.logger.web_action("click", element=locator, duration=duration, 
                                     outcome="failed", error=str(e))
                raise
    
    def input_text(self, locator: str, text: str) -> None:
        """在元素中输入文本"""
        start_time = time.time()
        with self.tracer.trace_page_action("input_text", element=locator):
            try:
                element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, locator)))
                element.clear()
                element.send_keys(text)
                duration = time.time() - start_time
                self.logger.web_action("input_text", element=locator, duration=duration, 
                                     text_length=len(text), outcome="success")
            except Exception as e:
                duration = time.time() - start_time
                self.logger.web_action("input_text", element=locator, duration=duration, 
                                     outcome="failed", error=str(e))
                raise
    
    def get_text(self, locator: str) -> str:
        """获取元素文本"""
        start_time = time.time()
        with self.tracer.trace_page_action("get_text", element=locator):
            try:
                element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, locator)))
                text = element.text
                duration = time.time() - start_time
                self.logger.web_action("get_text", element=locator, duration=duration, 
                                     text_length=len(text), outcome="success")
                return text
            except Exception as e:
                duration = time.time() - start_time
                self.logger.web_action("get_text", element=locator, duration=duration, 
                                     outcome="failed", error=str(e))
                raise
    
    def wait_for_element(self, locator: str, timeout: int = 10) -> Any:
        """等待元素出现"""
        start_time = time.time()
        with self.tracer.trace_page_action("wait_for_element", element=locator):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, locator))
                )
                duration = time.time() - start_time
                self.logger.web_action("wait_for_element", element=locator, duration=duration, 
                                     outcome="found")
                return element
            except TimeoutException as e:
                duration = time.time() - start_time
                self.logger.web_action("wait_for_element", element=locator, duration=duration, 
                                     outcome="timeout")
                raise
    
    def screenshot(self, path: Optional[str] = None) -> bytes:
        """截图"""
        start_time = time.time()
        with self.tracer.trace_page_action("screenshot", file_path=path or ""):
            try:
                if path:
                    self.driver.save_screenshot(path)
                    with open(path, 'rb') as f:
                        screenshot_data = f.read()
                else:
                    screenshot_data = self.driver.get_screenshot_as_png()
                
                duration = time.time() - start_time
                self.logger.web_action("screenshot", duration=duration, 
                                     file_path=path, size=len(screenshot_data), outcome="success")
                return screenshot_data
            except Exception as e:
                duration = time.time() - start_time
                self.logger.web_action("screenshot", duration=duration, 
                                     file_path=path, outcome="failed", error=str(e))
                raise
