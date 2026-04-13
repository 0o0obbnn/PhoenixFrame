"""Selenium页面实现

基于BasePage的Selenium具体实现，提供：
- Selenium WebDriver集成
- 元素定位和操作
- 等待策略实现
- 错误处理和重试
- 截图和日志记录
"""

from typing import Any, List, Optional, Union
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    StaleElementReferenceException, WebDriverException
)

from .base_page import (
    BasePage, WaitCondition, PageError, ElementNotFoundError,
    ElementNotClickableError, PageLoadTimeoutError
)


class SeleniumPage(BasePage):
    """Selenium页面实现类"""
    
    def __init__(self, driver: webdriver.Remote):
        """
        初始化Selenium页面
        
        Args:
            driver: Selenium WebDriver实例
        """
        super().__init__(driver)
        self.wait = WebDriverWait(driver, self.default_timeout)
        self.actions = ActionChains(driver)
    
    # === 抽象方法实现 ===
    
    def navigate(self, url: Optional[str] = None) -> None:
        """
        导航到页面
        
        Args:
            url: 页面URL，如果为None则使用self.url
        """
        target_url = url or self.url
        if not target_url:
            raise ValueError("No URL specified for navigation")
        
        try:
            with self.tracer.trace_page_action("navigate", url=target_url):
                self.driver.get(target_url)
                self.logger.info(f"Navigated to: {target_url}")
                
                # 等待页面加载
                self.wait_for_page_load()
                
        except Exception as e:
            self.logger.error(f"Failed to navigate to {target_url}: {e}")
            raise PageError(f"Navigation failed: {e}")
    
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """
        等待页面加载完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 页面是否加载成功
        """
        try:
            with self.tracer.trace_page_action("wait_for_page_load", timeout=timeout):
                # 等待document.readyState为complete
                WebDriverWait(self.driver, timeout).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                # 等待jQuery加载完成（如果存在）
                try:
                    WebDriverWait(self.driver, 2).until(
                        lambda driver: driver.execute_script("return jQuery.active == 0") if 
                        driver.execute_script("return typeof jQuery !== 'undefined'") else True
                    )
                except TimeoutException:
                    pass  # jQuery可能不存在，继续执行
                
                self.logger.debug("Page loaded successfully")
                return True
                
        except TimeoutException:
            self.logger.error(f"Page load timeout after {timeout} seconds")
            raise PageLoadTimeoutError(f"Page failed to load within {timeout} seconds")
        except Exception as e:
            self.logger.error(f"Error waiting for page load: {e}")
            return False
    
    def is_element_present(self, locator: str) -> bool:
        """
        检查元素是否存在
        
        Args:
            locator: 元素定位器（CSS选择器）
            
        Returns:
            bool: 元素是否存在
        """
        try:
            self.driver.find_element(By.CSS_SELECTOR, locator)
            return True
        except NoSuchElementException:
            return False
        except Exception as e:
            self.logger.debug(f"Error checking element presence {locator}: {e}")
            return False
    
    def click_element(self, locator: str) -> None:
        """
        点击元素
        
        Args:
            locator: 元素定位器（CSS选择器）
        """
        try:
            with self.tracer.trace_page_action("click_element", element=locator):
                element = self.driver.find_element(By.CSS_SELECTOR, locator)
                
                # 滚动到元素位置
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                
                # 等待元素可点击
                WebDriverWait(self.driver, self.default_timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, locator))
                )
                
                # 执行点击
                element.click()
                self.logger.debug(f"Clicked element: {locator}")
                
        except TimeoutException:
            raise ElementNotClickableError(f"Element {locator} is not clickable")
        except NoSuchElementException:
            raise ElementNotFoundError(f"Element {locator} not found")
        except Exception as e:
            self.logger.error(f"Failed to click element {locator}: {e}")
            raise PageError(f"Click failed: {e}")
    
    def input_text(self, locator: str, text: str) -> None:
        """
        在元素中输入文本
        
        Args:
            locator: 元素定位器（CSS选择器）
            text: 要输入的文本
        """
        try:
            with self.tracer.trace_page_action("input_text", element=locator, text=text):
                element = self.driver.find_element(By.CSS_SELECTOR, locator)
                
                # 等待元素可见
                WebDriverWait(self.driver, self.default_timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, locator))
                )
                
                # 清空并输入文本
                element.clear()
                element.send_keys(text)
                self.logger.debug(f"Input text '{text}' into element: {locator}")
                
        except NoSuchElementException:
            raise ElementNotFoundError(f"Element {locator} not found")
        except Exception as e:
            self.logger.error(f"Failed to input text into element {locator}: {e}")
            raise PageError(f"Input failed: {e}")
    
    def get_text(self, locator: str) -> str:
        """
        获取元素文本
        
        Args:
            locator: 元素定位器（CSS选择器）
            
        Returns:
            str: 元素文本
        """
        try:
            with self.tracer.trace_page_action("get_text", element=locator):
                element = self.driver.find_element(By.CSS_SELECTOR, locator)
                
                # 等待元素可见
                WebDriverWait(self.driver, self.default_timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, locator))
                )
                
                text = element.text
                self.logger.debug(f"Got text '{text}' from element: {locator}")
                return text
                
        except NoSuchElementException:
            raise ElementNotFoundError(f"Element {locator} not found")
        except Exception as e:
            self.logger.error(f"Failed to get text from element {locator}: {e}")
            raise PageError(f"Get text failed: {e}")
    
    # === 条件检查实现 ===
    
    def _check_condition(self, locator: str, condition: WaitCondition) -> bool:
        """
        检查等待条件是否满足
        
        Args:
            locator: 元素定位器
            condition: 等待条件
            
        Returns:
            bool: 条件是否满足
        """
        try:
            if condition == WaitCondition.PRESENT:
                return self.is_element_present(locator)
            elif condition == WaitCondition.VISIBLE:
                return self.is_element_visible(locator)
            elif condition == WaitCondition.CLICKABLE:
                return self.is_element_clickable(locator)
            elif condition == WaitCondition.INVISIBLE:
                return not self.is_element_visible(locator)
            elif condition == WaitCondition.PAGE_LOADED:
                return self.is_page_ready()
            else:
                raise ValueError(f"Unsupported wait condition: {condition}")
        except Exception:
            return False
    
    def is_element_visible(self, locator: str) -> bool:
        """
        检查元素是否可见
        
        Args:
            locator: 元素定位器
            
        Returns:
            bool: 元素是否可见
        """
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, locator)
            return element.is_displayed()
        except (NoSuchElementException, StaleElementReferenceException):
            return False
        except Exception as e:
            self.logger.debug(f"Error checking element visibility {locator}: {e}")
            return False
    
    def is_element_clickable(self, locator: str) -> bool:
        """
        检查元素是否可点击
        
        Args:
            locator: 元素定位器
            
        Returns:
            bool: 元素是否可点击
        """
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, locator)
            return element.is_enabled() and element.is_displayed()
        except (NoSuchElementException, StaleElementReferenceException):
            return False
        except Exception as e:
            self.logger.debug(f"Error checking element clickability {locator}: {e}")
            return False
    
    def clear_element(self, locator: str) -> None:
        """
        清空元素内容
        
        Args:
            locator: 元素定位器
        """
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, locator)
            element.clear()
            self.logger.debug(f"Cleared element: {locator}")
        except NoSuchElementException:
            raise ElementNotFoundError(f"Element {locator} not found")
        except Exception as e:
            self.logger.error(f"Failed to clear element {locator}: {e}")
            raise PageError(f"Clear failed: {e}")
    
    # === 扩展方法 ===
    
    def find_element(self, locator: str) -> WebElement:
        """
        查找单个元素
        
        Args:
            locator: 元素定位器（CSS选择器）
            
        Returns:
            WebElement: 找到的元素
        """
        try:
            return self.driver.find_element(By.CSS_SELECTOR, locator)
        except NoSuchElementException:
            raise ElementNotFoundError(f"Element {locator} not found")
    
    def find_elements(self, locator: str) -> List[WebElement]:
        """
        查找多个元素
        
        Args:
            locator: 元素定位器（CSS选择器）
            
        Returns:
            List[WebElement]: 找到的元素列表
        """
        return self.driver.find_elements(By.CSS_SELECTOR, locator)
    
    def get_attribute(self, locator: str, attribute: str) -> Optional[str]:
        """
        获取元素属性
        
        Args:
            locator: 元素定位器
            attribute: 属性名
            
        Returns:
            Optional[str]: 属性值
        """
        try:
            element = self.find_element(locator)
            return element.get_attribute(attribute)
        except ElementNotFoundError:
            return None
    
    def set_attribute(self, locator: str, attribute: str, value: str) -> None:
        """
        设置元素属性
        
        Args:
            locator: 元素定位器
            attribute: 属性名
            value: 属性值
        """
        try:
            element = self.find_element(locator)
            self.driver.execute_script(f"arguments[0].setAttribute('{attribute}', '{value}');", element)
            self.logger.debug(f"Set attribute {attribute}={value} for element: {locator}")
        except Exception as e:
            self.logger.error(f"Failed to set attribute {attribute} for element {locator}: {e}")
            raise PageError(f"Set attribute failed: {e}")
    
    def hover_element(self, locator: str) -> None:
        """
        悬停在元素上
        
        Args:
            locator: 元素定位器
        """
        try:
            element = self.find_element(locator)
            self.actions.move_to_element(element).perform()
            self.logger.debug(f"Hovered over element: {locator}")
        except Exception as e:
            self.logger.error(f"Failed to hover over element {locator}: {e}")
            raise PageError(f"Hover failed: {e}")
    
    def double_click_element(self, locator: str) -> None:
        """
        双击元素
        
        Args:
            locator: 元素定位器
        """
        try:
            element = self.find_element(locator)
            self.actions.double_click(element).perform()
            self.logger.debug(f"Double-clicked element: {locator}")
        except Exception as e:
            self.logger.error(f"Failed to double-click element {locator}: {e}")
            raise PageError(f"Double-click failed: {e}")
    
    def right_click_element(self, locator: str) -> None:
        """
        右键点击元素
        
        Args:
            locator: 元素定位器
        """
        try:
            element = self.find_element(locator)
            self.actions.context_click(element).perform()
            self.logger.debug(f"Right-clicked element: {locator}")
        except Exception as e:
            self.logger.error(f"Failed to right-click element {locator}: {e}")
            raise PageError(f"Right-click failed: {e}")
    
    def drag_and_drop(self, source_locator: str, target_locator: str) -> None:
        """
        拖拽操作
        
        Args:
            source_locator: 源元素定位器
            target_locator: 目标元素定位器
        """
        try:
            source = self.find_element(source_locator)
            target = self.find_element(target_locator)
            self.actions.drag_and_drop(source, target).perform()
            self.logger.debug(f"Dragged from {source_locator} to {target_locator}")
        except Exception as e:
            self.logger.error(f"Failed to drag and drop from {source_locator} to {target_locator}: {e}")
            raise PageError(f"Drag and drop failed: {e}")
    
    def select_dropdown_by_text(self, locator: str, text: str) -> None:
        """
        通过文本选择下拉框选项
        
        Args:
            locator: 下拉框定位器
            text: 选项文本
        """
        try:
            from selenium.webdriver.support.ui import Select
            element = self.find_element(locator)
            select = Select(element)
            select.select_by_visible_text(text)
            self.logger.debug(f"Selected dropdown option '{text}' for element: {locator}")
        except Exception as e:
            self.logger.error(f"Failed to select dropdown option '{text}' for element {locator}: {e}")
            raise PageError(f"Dropdown selection failed: {e}")
    
    def select_dropdown_by_value(self, locator: str, value: str) -> None:
        """
        通过值选择下拉框选项
        
        Args:
            locator: 下拉框定位器
            value: 选项值
        """
        try:
            from selenium.webdriver.support.ui import Select
            element = self.find_element(locator)
            select = Select(element)
            select.select_by_value(value)
            self.logger.debug(f"Selected dropdown value '{value}' for element: {locator}")
        except Exception as e:
            self.logger.error(f"Failed to select dropdown value '{value}' for element {locator}: {e}")
            raise PageError(f"Dropdown selection failed: {e}")
    
    def upload_file(self, locator: str, file_path: str) -> None:
        """
        上传文件
        
        Args:
            locator: 文件输入框定位器
            file_path: 文件路径
        """
        try:
            element = self.find_element(locator)
            element.send_keys(file_path)
            self.logger.debug(f"Uploaded file '{file_path}' to element: {locator}")
        except Exception as e:
            self.logger.error(f"Failed to upload file '{file_path}' to element {locator}: {e}")
            raise PageError(f"File upload failed: {e}")
    
    def switch_to_frame(self, frame_locator: str) -> None:
        """
        切换到iframe
        
        Args:
            frame_locator: iframe定位器
        """
        try:
            frame = self.find_element(frame_locator)
            self.driver.switch_to.frame(frame)
            self.logger.debug(f"Switched to frame: {frame_locator}")
        except Exception as e:
            self.logger.error(f"Failed to switch to frame {frame_locator}: {e}")
            raise PageError(f"Frame switch failed: {e}")
    
    def switch_to_default_content(self) -> None:
        """切换回主文档"""
        try:
            self.driver.switch_to.default_content()
            self.logger.debug("Switched to default content")
        except Exception as e:
            self.logger.error(f"Failed to switch to default content: {e}")
            raise PageError(f"Default content switch failed: {e}")
    
    def switch_to_window(self, window_handle: str) -> None:
        """
        切换到指定窗口
        
        Args:
            window_handle: 窗口句柄
        """
        try:
            self.driver.switch_to.window(window_handle)
            self.logger.debug(f"Switched to window: {window_handle}")
        except Exception as e:
            self.logger.error(f"Failed to switch to window {window_handle}: {e}")
            raise PageError(f"Window switch failed: {e}")
    
    def get_window_handles(self) -> List[str]:
        """
        获取所有窗口句柄
        
        Returns:
            List[str]: 窗口句柄列表
        """
        return self.driver.window_handles
    
    def close_current_window(self) -> None:
        """关闭当前窗口"""
        try:
            self.driver.close()
            self.logger.debug("Closed current window")
        except Exception as e:
            self.logger.error(f"Failed to close current window: {e}")
            raise PageError(f"Window close failed: {e}")
    
    def refresh_page(self) -> None:
        """刷新页面"""
        try:
            self.driver.refresh()
            self.logger.debug("Refreshed page")
            self.wait_for_page_load()
        except Exception as e:
            self.logger.error(f"Failed to refresh page: {e}")
            raise PageError(f"Page refresh failed: {e}")
    
    def go_back(self) -> None:
        """后退"""
        try:
            self.driver.back()
            self.logger.debug("Navigated back")
            self.wait_for_page_load()
        except Exception as e:
            self.logger.error(f"Failed to go back: {e}")
            raise PageError(f"Back navigation failed: {e}")
    
    def go_forward(self) -> None:
        """前进"""
        try:
            self.driver.forward()
            self.logger.debug("Navigated forward")
            self.wait_for_page_load()
        except Exception as e:
            self.logger.error(f"Failed to go forward: {e}")
            raise PageError(f"Forward navigation failed: {e}")
    
    def maximize_window(self) -> None:
        """最大化窗口"""
        try:
            self.driver.maximize_window()
            self.logger.debug("Maximized window")
        except Exception as e:
            self.logger.error(f"Failed to maximize window: {e}")
    
    def set_window_size(self, width: int, height: int) -> None:
        """
        设置窗口大小
        
        Args:
            width: 宽度
            height: 高度
        """
        try:
            self.driver.set_window_size(width, height)
            self.logger.debug(f"Set window size to {width}x{height}")
        except Exception as e:
            self.logger.error(f"Failed to set window size: {e}")
    
    def get_page_source(self) -> str:
        """
        获取页面源码
        
        Returns:
            str: 页面源码
        """
        return self.driver.page_source
    
    def execute_script(self, script: str, *args) -> Any:
        """
        执行JavaScript代码
        
        Args:
            script: JavaScript代码
            *args: 脚本参数
            
        Returns:
            Any: 脚本执行结果
        """
        try:
            result = self.driver.execute_script(script, *args)
            self.logger.debug(f"Executed JavaScript: {script[:50]}...")
            return result
        except Exception as e:
            self.logger.error(f"Failed to execute JavaScript: {e}")
            raise PageError(f"JavaScript execution failed: {e}")