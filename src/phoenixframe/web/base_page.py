"""基础页面对象模型类"""
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Union, List, Dict, Callable
from enum import Enum
from ..observability.logger import get_logger
from ..observability.tracer import get_tracer


class WaitCondition(Enum):
    """等待条件枚举"""
    PRESENT = "present"  # 元素存在
    VISIBLE = "visible"  # 元素可见
    CLICKABLE = "clickable"  # 元素可点击
    INVISIBLE = "invisible"  # 元素不可见
    TEXT_PRESENT = "text_present"  # 文本存在
    ATTRIBUTE_CONTAINS = "attribute_contains"  # 属性包含值
    PAGE_LOADED = "page_loaded"  # 页面加载完成


class PageError(Exception):
    """页面操作异常"""
    pass


class ElementNotFoundError(PageError):
    """元素未找到异常"""
    pass


class ElementNotClickableError(PageError):
    """元素不可点击异常"""
    pass


class PageLoadTimeoutError(PageError):
    """页面加载超时异常"""
    pass


class BasePage(ABC):
    """页面对象模型基类，定义通用的页面操作接口"""
    
    def __init__(self, driver: Any):
        """
        初始化页面对象
        
        Args:
            driver: WebDriver实例（Selenium或Playwright）
        """
        self.driver = driver
        self.url: Optional[str] = None
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.tracer = get_tracer(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # 默认配置
        self.default_timeout = 10
        self.default_poll_frequency = 0.5
        self.max_retry_attempts = 3
        
        # 页面元素缓存
        self._element_cache: Dict[str, Any] = {}
        self._cache_enabled = False
    
    # === 抽象方法 - 子类必须实现 ===
    
    @abstractmethod
    def navigate(self, url: Optional[str] = None) -> None:
        """
        导航到页面
        
        Args:
            url: 页面URL，如果为None则使用self.url
        """
        pass
    
    @abstractmethod
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """
        等待页面加载完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 页面是否加载成功
        """
        pass
    
    @abstractmethod
    def is_element_present(self, locator: str) -> bool:
        """
        检查元素是否存在
        
        Args:
            locator: 元素定位器
            
        Returns:
            bool: 元素是否存在
        """
        pass
    
    @abstractmethod
    def click_element(self, locator: str) -> None:
        """
        点击元素
        
        Args:
            locator: 元素定位器
        """
        pass
    
    @abstractmethod
    def input_text(self, locator: str, text: str) -> None:
        """
        在元素中输入文本
        
        Args:
            locator: 元素定位器
            text: 要输入的文本
        """
        pass
    
    @abstractmethod
    def get_text(self, locator: str) -> str:
        """
        获取元素文本
        
        Args:
            locator: 元素定位器
            
        Returns:
            str: 元素文本
        """
        pass
    
    # === 通用方法实现 ===
    
    def get_title(self) -> str:
        """
        获取页面标题
        
        Returns:
            str: 页面标题
        """
        try:
            title = self.driver.title if hasattr(self.driver, 'title') else ""
            self.logger.debug(f"Page title: {title}")
            return title
        except Exception as e:
            self.logger.error(f"Failed to get page title: {e}")
            return ""
    
    def get_current_url(self) -> str:
        """
        获取当前页面URL
        
        Returns:
            str: 当前页面URL
        """
        try:
            url = self.driver.current_url if hasattr(self.driver, 'current_url') else ""
            self.logger.debug(f"Current URL: {url}")
            return url
        except Exception as e:
            self.logger.error(f"Failed to get current URL: {e}")
            return ""
    
    # === 智能等待策略 ===
    
    def wait_for_element(self, locator: str, condition: WaitCondition = WaitCondition.PRESENT, 
                        timeout: Optional[int] = None, poll_frequency: Optional[float] = None,
                        error_message: Optional[str] = None) -> bool:
        """
        智能等待元素满足指定条件
        
        Args:
            locator: 元素定位器
            condition: 等待条件
            timeout: 超时时间（秒）
            poll_frequency: 轮询频率（秒）
            error_message: 自定义错误消息
            
        Returns:
            bool: 条件是否满足
            
        Raises:
            PageError: 等待超时或其他错误
        """
        timeout = timeout or self.default_timeout
        poll_frequency = poll_frequency or self.default_poll_frequency
        
        start_time = time.time()
        
        with self.tracer.trace_page_action("wait_for_element", element=locator, condition=condition.value):
            while time.time() - start_time < timeout:
                try:
                    if self._check_condition(locator, condition):
                        self.logger.debug(f"Element {locator} condition {condition.value} satisfied")
                        return True
                except Exception as e:
                    self.logger.debug(f"Condition check failed: {e}")
                
                time.sleep(poll_frequency)
            
            # 超时处理
            error_msg = error_message or f"Element {locator} condition {condition.value} not met within {timeout}s"
            self.logger.error(error_msg)
            raise PageError(error_msg)
    
    def wait_for_text(self, locator: str, expected_text: str, timeout: Optional[int] = None) -> bool:
        """
        等待元素包含指定文本
        
        Args:
            locator: 元素定位器
            expected_text: 期望的文本
            timeout: 超时时间（秒）
            
        Returns:
            bool: 文本是否出现
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                actual_text = self.get_text(locator)
                if expected_text in actual_text:
                    self.logger.debug(f"Expected text '{expected_text}' found in element {locator}")
                    return True
            except Exception as e:
                self.logger.debug(f"Failed to get text from {locator}: {e}")
            
            time.sleep(0.5)
        
        self.logger.error(f"Text '{expected_text}' not found in element {locator} within {timeout}s")
        return False
    
    def wait_for_any_element(self, locators: List[str], timeout: Optional[int] = None) -> Optional[str]:
        """
        等待任意一个元素出现
        
        Args:
            locators: 元素定位器列表
            timeout: 超时时间（秒）
            
        Returns:
            Optional[str]: 第一个出现的元素定位器，如果都没出现则返回None
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            for locator in locators:
                try:
                    if self.is_element_present(locator):
                        self.logger.debug(f"Element {locator} appeared first")
                        return locator
                except Exception:
                    continue
            
            time.sleep(0.5)
        
        self.logger.error(f"None of the elements {locators} appeared within {timeout}s")
        return None
    
    def wait_for_all_elements(self, locators: List[str], timeout: Optional[int] = None) -> bool:
        """
        等待所有元素都出现
        
        Args:
            locators: 元素定位器列表
            timeout: 超时时间（秒）
            
        Returns:
            bool: 所有元素是否都出现
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_present = True
            for locator in locators:
                try:
                    if not self.is_element_present(locator):
                        all_present = False
                        break
                except Exception:
                    all_present = False
                    break
            
            if all_present:
                self.logger.debug(f"All elements {locators} are present")
                return True
            
            time.sleep(0.5)
        
        self.logger.error(f"Not all elements {locators} appeared within {timeout}s")
        return False
    
    # === 错误处理和重试机制 ===
    
    def retry_on_failure(self, func: Callable, *args, max_attempts: Optional[int] = None, 
                        delay: float = 1.0, **kwargs) -> Any:
        """
        在失败时重试操作
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            max_attempts: 最大重试次数
            delay: 重试间隔（秒）
            **kwargs: 函数关键字参数
            
        Returns:
            Any: 函数执行结果
            
        Raises:
            Exception: 最后一次执行的异常
        """
        max_attempts = max_attempts or self.max_retry_attempts
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"Operation succeeded on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_attempts - 1:
                    self.logger.debug(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {max_attempts} attempts failed")
        
        raise last_exception
    
    def safe_click(self, locator: str, timeout: Optional[int] = None) -> bool:
        """
        安全点击元素（带重试和错误处理）
        
        Args:
            locator: 元素定位器
            timeout: 超时时间（秒）
            
        Returns:
            bool: 点击是否成功
        """
        try:
            # 等待元素可点击
            self.wait_for_element(locator, WaitCondition.CLICKABLE, timeout)
            
            # 重试点击
            self.retry_on_failure(self.click_element, locator)
            
            self.logger.info(f"Successfully clicked element: {locator}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to click element {locator}: {e}")
            return False
    
    def safe_input(self, locator: str, text: str, clear_first: bool = True, 
                  timeout: Optional[int] = None) -> bool:
        """
        安全输入文本（带重试和错误处理）
        
        Args:
            locator: 元素定位器
            text: 要输入的文本
            clear_first: 是否先清空输入框
            timeout: 超时时间（秒）
            
        Returns:
            bool: 输入是否成功
        """
        try:
            # 等待元素存在
            self.wait_for_element(locator, WaitCondition.PRESENT, timeout)
            
            # 清空输入框（如果需要）
            if clear_first:
                try:
                    self.clear_element(locator)
                except Exception as e:
                    self.logger.warning(f"Failed to clear element {locator}: {e}")
            
            # 重试输入
            self.retry_on_failure(self.input_text, locator, text)
            
            self.logger.info(f"Successfully input text into element: {locator}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to input text into element {locator}: {e}")
            return False
    
    # === 高级页面操作 ===
    
    def scroll_to_element(self, locator: str) -> bool:
        """
        滚动到元素位置
        
        Args:
            locator: 元素定位器
            
        Returns:
            bool: 滚动是否成功
        """
        try:
            # 这里需要根据具体的驱动类型实现
            # Selenium和Playwright有不同的滚动方法
            if hasattr(self.driver, 'execute_script'):
                # Selenium实现
                element = self.driver.find_element("css selector", locator)
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            elif hasattr(self.driver, 'locator'):
                # Playwright实现
                self.driver.locator(locator).scroll_into_view_if_needed()
            
            self.logger.debug(f"Scrolled to element: {locator}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to scroll to element {locator}: {e}")
            return False
    
    def take_screenshot(self, filename: Optional[str] = None) -> Optional[str]:
        """
        截取页面截图
        
        Args:
            filename: 截图文件名，如果为None则自动生成
            
        Returns:
            Optional[str]: 截图文件路径
        """
        try:
            if not filename:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            if hasattr(self.driver, 'get_screenshot_as_file'):
                # Selenium实现
                self.driver.get_screenshot_as_file(filename)
            elif hasattr(self.driver, 'screenshot'):
                # Playwright实现
                self.driver.screenshot(path=filename)
            
            self.logger.info(f"Screenshot saved: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def execute_javascript(self, script: str, *args) -> Any:
        """
        执行JavaScript代码
        
        Args:
            script: JavaScript代码
            *args: 脚本参数
            
        Returns:
            Any: 脚本执行结果
        """
        try:
            if hasattr(self.driver, 'execute_script'):
                # Selenium实现
                result = self.driver.execute_script(script, *args)
            elif hasattr(self.driver, 'evaluate'):
                # Playwright实现
                result = self.driver.evaluate(script)
            else:
                raise NotImplementedError("JavaScript execution not supported by this driver")
            
            self.logger.debug(f"Executed JavaScript: {script[:50]}...")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute JavaScript: {e}")
            raise
    
    # === 页面状态检查 ===
    
    def is_page_ready(self) -> bool:
        """
        检查页面是否准备就绪
        
        Returns:
            bool: 页面是否准备就绪
        """
        try:
            # 检查document.readyState
            ready_state = self.execute_javascript("return document.readyState")
            is_ready = ready_state == "complete"
            
            self.logger.debug(f"Page ready state: {ready_state}")
            return is_ready
            
        except Exception as e:
            self.logger.error(f"Failed to check page ready state: {e}")
            return False
    
    def wait_for_ajax_complete(self, timeout: Optional[int] = None) -> bool:
        """
        等待AJAX请求完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: AJAX是否完成
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 检查jQuery.active（如果页面使用jQuery）
                active_requests = self.execute_javascript(
                    "return (typeof jQuery !== 'undefined') ? jQuery.active : 0"
                )
                
                if active_requests == 0:
                    self.logger.debug("AJAX requests completed")
                    return True
                    
            except Exception as e:
                self.logger.debug(f"AJAX check failed: {e}")
            
            time.sleep(0.5)
        
        self.logger.warning(f"AJAX requests may not have completed within {timeout}s")
        return False
    
    # === 元素缓存机制 ===
    
    def enable_element_cache(self) -> None:
        """启用元素缓存"""
        self._cache_enabled = True
        self.logger.debug("Element cache enabled")
    
    def disable_element_cache(self) -> None:
        """禁用元素缓存"""
        self._cache_enabled = False
        self._element_cache.clear()
        self.logger.debug("Element cache disabled")
    
    def clear_element_cache(self) -> None:
        """清空元素缓存"""
        self._element_cache.clear()
        self.logger.debug("Element cache cleared")
    
    # === 辅助方法 ===
    
    def _check_condition(self, locator: str, condition: WaitCondition) -> bool:
        """
        检查等待条件是否满足
        
        Args:
            locator: 元素定位器
            condition: 等待条件
            
        Returns:
            bool: 条件是否满足
        """
        if condition == WaitCondition.PRESENT:
            return self.is_element_present(locator)
        elif condition == WaitCondition.VISIBLE:
            return self.is_element_visible(locator)
        elif condition == WaitCondition.CLICKABLE:
            return self.is_element_clickable(locator)
        elif condition == WaitCondition.INVISIBLE:
            return not self.is_element_visible(locator)
        else:
            raise ValueError(f"Unsupported wait condition: {condition}")
    
    def is_element_visible(self, locator: str) -> bool:
        """
        检查元素是否可见（子类可重写）
        
        Args:
            locator: 元素定位器
            
        Returns:
            bool: 元素是否可见
        """
        # 默认实现，子类应该重写
        return self.is_element_present(locator)
    
    def is_element_clickable(self, locator: str) -> bool:
        """
        检查元素是否可点击（子类可重写）
        
        Args:
            locator: 元素定位器
            
        Returns:
            bool: 元素是否可点击
        """
        # 默认实现，子类应该重写
        return self.is_element_visible(locator)
    
    def clear_element(self, locator: str) -> None:
        """
        清空元素内容（子类可重写）
        
        Args:
            locator: 元素定位器
        """
        # 默认实现，子类应该重写
        pass
