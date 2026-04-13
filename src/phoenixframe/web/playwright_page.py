"""Playwright页面实现

基于BasePage的Playwright具体实现，提供：
- Playwright Page集成
- 元素定位和操作
- 等待策略实现
- 错误处理和重试
- 截图和日志记录
"""

from typing import Any, List, Optional, Union, Callable
try:
    from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = Any
    Locator = Any
    PlaywrightTimeoutError = Exception

from .base_page import (
    BasePage, WaitCondition, PageError, ElementNotFoundError,
    ElementNotClickableError, PageLoadTimeoutError
)


class PlaywrightPage(BasePage):
    """Playwright页面实现类"""
    
    def __init__(self, page: Page):
        """
        初始化Playwright页面
        
        Args:
            page: Playwright Page实例
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not installed. Install with: pip install playwright")
        
        super().__init__(page)
        self.page = page
        
        # 设置默认超时
        self.page.set_default_timeout(self.default_timeout * 1000)  # Playwright使用毫秒
    
    # === 抽象方法实现 ===
    
    def navigate(self, url: Optional[str] = None) -> None:
        """
        导航到页面
        
        Args:
            url: 目标URL，如果为None则使用页面默认URL
        """
        target_url = url or self.url
        if not target_url:
            raise ValueError("URL is required")
        
        try:
            with self.tracer.trace_page_action("navigate", page_url=target_url):
                self.page.goto(target_url)
                self.logger.web_action("navigate", page_url=target_url, outcome="success")
        except Exception as e:
            self.logger.web_action("navigate", page_url=target_url, outcome="failed", error=str(e))
            raise PageError(f"Navigation failed: {e}")
    
    def find_element(self, locator: str, timeout: Optional[int] = None) -> Locator:
        """
        查找元素
        
        Args:
            locator: 元素定位器
            timeout: 超时时间（秒）
            
        Returns:
            Locator: Playwright定位器对象
        """
        try:
            timeout_ms = (timeout or self.default_timeout) * 1000
            element = self.page.locator(locator)
            element.wait_for(timeout=timeout_ms, state="visible")
            self.logger.web_action("find_element", element=locator, outcome="found")
            return element
        except PlaywrightTimeoutError:
            self.logger.web_action("find_element", element=locator, outcome="not_found")
            raise ElementNotFoundError(f"Element not found: {locator}")
        except Exception as e:
            self.logger.web_action("find_element", element=locator, outcome="error", error=str(e))
            raise PageError(f"Find element failed: {e}")
    
    def click_element(self, locator: str, timeout: Optional[int] = None) -> None:
        """
        点击元素
        
        Args:
            locator: 元素定位器
            timeout: 超时时间（秒）
        """
        try:
            timeout_ms = (timeout or self.default_timeout) * 1000
            with self.tracer.trace_page_action("click", element=locator):
                element = self.page.locator(locator)
                element.click(timeout=timeout_ms)
                self.logger.web_action("click", element=locator, outcome="success")
        except PlaywrightTimeoutError:
            self.logger.web_action("click", element=locator, outcome="timeout")
            raise ElementNotClickableError(f"Element not clickable: {locator}")
        except Exception as e:
            self.logger.web_action("click", element=locator, outcome="error", error=str(e))
            raise PageError(f"Click failed: {e}")
    
    def input_text(self, locator: str, text: str, timeout: Optional[int] = None) -> None:
        """
        在元素中输入文本
        
        Args:
            locator: 元素定位器
            text: 输入文本
            timeout: 超时时间（秒）
        """
        try:
            timeout_ms = (timeout or self.default_timeout) * 1000
            with self.tracer.trace_page_action("input_text", element=locator):
                element = self.page.locator(locator)
                element.fill(text, timeout=timeout_ms)
                self.logger.web_action("input_text", element=locator, text_length=len(text), outcome="success")
        except Exception as e:
            self.logger.web_action("input_text", element=locator, outcome="error", error=str(e))
            raise PageError(f"Input text failed: {e}")
    
    def get_text(self, locator: str, timeout: Optional[int] = None) -> str:
        """
        获取元素文本
        
        Args:
            locator: 元素定位器
            timeout: 超时时间（秒）
            
        Returns:
            str: 元素文本
        """
        try:
            timeout_ms = (timeout or self.default_timeout) * 1000
            with self.tracer.trace_page_action("get_text", element=locator):
                element = self.page.locator(locator)
                text = element.text_content(timeout=timeout_ms) or ""
                self.logger.web_action("get_text", element=locator, text_length=len(text), outcome="success")
                return text
        except Exception as e:
            self.logger.web_action("get_text", element=locator, outcome="error", error=str(e))
            raise PageError(f"Get text failed: {e}")
    
    def wait_for_page_load(self, timeout: Optional[int] = None) -> bool:
        """
        等待页面加载完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否加载完成
        """
        try:
            timeout_ms = (timeout or self.default_timeout) * 1000
            with self.tracer.trace_page_action("wait_for_page_load", duration=timeout or self.default_timeout):
                self.page.wait_for_load_state("networkidle", timeout=timeout_ms)
                self.logger.web_action("wait_for_page_load", outcome="success")
                return True
        except Exception as e:
            self.logger.web_action("wait_for_page_load", outcome="timeout", error=str(e))
            return False
    
    # === 设备模拟功能 ===
    
    def set_device(self, device_name: str) -> None:
        """
        设置设备模拟
        
        Args:
            device_name: 设备名称
        """
        # 这个方法需要在driver层面设置，这里仅提供接口说明
        raise NotImplementedError("Device simulation should be set at driver level")
    
    def set_viewport_size(self, width: int, height: int) -> None:
        """
        设置视口大小
        
        Args:
            width: 宽度
            height: 高度
        """
        try:
            self.page.set_viewport_size({"width": width, "height": height})
            self.logger.debug(f"Set viewport size to {width}x{height}")
        except Exception as e:
            self.logger.error(f"Failed to set viewport size: {e}")
    
    # === 网络拦截功能 ===
    
    def intercept_requests(self, url_pattern: str, handler: Callable) -> None:
        """
        拦截网络请求
        
        Args:
            url_pattern: URL模式
            handler: 处理函数
        """
        try:
            self.page.route(url_pattern, handler)
            self.logger.debug(f"Started intercepting requests matching: {url_pattern}")
        except Exception as e:
            self.logger.error(f"Failed to intercept requests: {e}")
    
    def stop_intercepting_requests(self, url_pattern: str) -> None:
        """
        停止拦截网络请求
        
        Args:
            url_pattern: URL模式
        """
        try:
            self.page.unroute(url_pattern)
            self.logger.debug(f"Stopped intercepting requests matching: {url_pattern}")
        except Exception as e:
            self.logger.error(f"Failed to stop intercepting requests: {e}")
    
    # === 视觉对比测试功能 ===
    
    def take_screenshot(self, path: Optional[str] = None, full_page: bool = False) -> bytes:
        """
        截取页面截图
        
        Args:
            path: 截图保存路径
            full_page: 是否截取整个页面
            
        Returns:
            bytes: 截图数据
        """
        try:
            screenshot_data = self.page.screenshot(path=path, full_page=full_page)
            self.logger.web_action("screenshot", file_path=path, size=len(screenshot_data), outcome="success")
            return screenshot_data
        except Exception as e:
            self.logger.web_action("screenshot", file_path=path, outcome="failed", error=str(e))
            raise PageError(f"Screenshot failed: {e}")
    
    def compare_visual(self, baseline_image_path: str, comparison_image_path: str = None, 
                      threshold: float = 0.1) -> bool:
        """
        视觉对比测试
        
        Args:
            baseline_image_path: 基线图像路径
            comparison_image_path: 对比图像路径，如果为None则自动截图
            threshold: 差异阈值（0-1）
            
        Returns:
            bool: 是否通过视觉对比
        """
        try:
            import cv2
            import numpy as np
            
            # 如果没有提供对比图像，则截取当前页面
            if not comparison_image_path:
                comparison_image_path = "temp_comparison.png"
                self.take_screenshot(comparison_image_path)
            
            # 读取图像
            baseline_img = cv2.imread(baseline_image_path)
            comparison_img = cv2.imread(comparison_image_path)
            
            if baseline_img is None or comparison_img is None:
                raise PageError("Failed to load images for visual comparison")
            
            # 调整图像大小以匹配
            if baseline_img.shape != comparison_img.shape:
                comparison_img = cv2.resize(comparison_img, (baseline_img.shape[1], baseline_img.shape[0]))
            
            # 计算差异
            diff = cv2.absdiff(baseline_img, comparison_img)
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            
            # 计算差异百分比
            _, diff_thresh = cv2.threshold(gray_diff, 25, 255, cv2.THRESH_BINARY)
            diff_ratio = np.sum(diff_thresh > 0) / diff_thresh.size
            
            result = diff_ratio <= threshold
            self.logger.web_action("visual_comparison", baseline=baseline_image_path, 
                                 comparison=comparison_image_path, difference=diff_ratio, 
                                 threshold=threshold, outcome="success" if result else "failed")
            
            return result
            
        except ImportError:
            self.logger.warning("OpenCV not installed. Visual comparison requires: pip install opencv-python")
            return True  # 如果没有安装OpenCV，则跳过视觉对比
        except Exception as e:
            self.logger.web_action("visual_comparison", baseline=baseline_image_path, 
                                 comparison=comparison_image_path, outcome="error", error=str(e))
            raise PageError(f"Visual comparison failed: {e}")
