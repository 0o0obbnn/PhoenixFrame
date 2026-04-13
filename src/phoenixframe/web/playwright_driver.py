"""Playwright 驱动实现

基于 Playwright 的 Web 驱动实现，符合 BaseWebDriver 接口规范。
"""

import time
import os
from typing import Optional, Dict, Any, List, Union
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext, Route, Request
from .base_driver import BaseWebDriver, WaitStrategy, LocatorStrategy
from ..observability.tracer import get_tracer
from ..observability.logger import get_logger

try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = Any
    Page = Any
    BrowserContext = Any


class PlaywrightDriver(BaseWebDriver):
    """Playwright 驱动实现
    
    基于 Playwright 的 Web 驱动，提供完整的浏览器自动化功能。
    """
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium", 
                 options: Optional[Dict[str, Any]] = None):
        """初始化 Playwright 驱动
        
        Args:
            headless: 是否无头模式运行
            browser_type: 浏览器类型 (chromium, firefox, webkit)
            options: 额外的浏览器选项
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not installed. Please install it with: pip install playwright")
        
        super().__init__(headless, browser_type)
        self.options = options or {}
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._network_logs = []
        self._device_profile = None
        
        # 初始化观测性组件
        self.tracer = get_tracer("phoenixframe.web.playwright")
        self.logger = get_logger("phoenixframe.web.playwright")
    
    def start(self) -> None:
        """启动浏览器实例"""
        if self._is_started:
            return
        
        with self.tracer.trace_operation("playwright_start"):
            self.playwright = sync_playwright().start()
            
            # 选择浏览器
            browser_map = {
                "chromium": self.playwright.chromium,
                "firefox": self.playwright.firefox,
                "webkit": self.playwright.webkit
            }
            
            if self.browser_type not in browser_map:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
            
            # 启动浏览器
            launch_options = {
                "headless": self.headless,
                "args": ["--no-sandbox", "--disable-dev-shm-usage"]
            }
            launch_options.update(self.options)
            
            self.browser = browser_map[self.browser_type].launch(**launch_options)
            
            # 创建上下文
            context_options = {
                "viewport": {"width": 1280, "height": 720}
            }
            if self._device_profile:
                context_options.update(self._device_profile)
            
            self.context = self.browser.new_context(**context_options)
            
            # 启用网络拦截
            self.context.route("**/*", self._handle_route)
            
            # 创建页面
            self.page = self.context.new_page()
            self._is_started = True
            
            self.logger.info("Playwright driver started", 
                           browser_type=self.browser_type, headless=self.headless)
    
    def stop(self) -> None:
        """停止浏览器实例"""
        if not self._is_started:
            return
        
        with self.tracer.trace_operation("playwright_stop"):
            try:
                if self.page:
                    self.page.close()
                    self.page = None
                if self.context:
                    self.context.close()
                    self.context = None
                if self.browser:
                    self.browser.close()
                    self.browser = None
                if self.playwright:
                    self.playwright.stop()
                    self.playwright = None
                
                self._is_started = False
                self.logger.info("Playwright driver stopped")
            except Exception as e:
                self.logger.error("Error stopping Playwright driver", error=str(e))
    
    def _handle_route(self, route: Route) -> None:
        """处理网络请求拦截"""
        request: Request = route.request
        self._network_logs.append({
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "timestamp": time.time(),
            "resource_type": request.resource_type
        })
        route.continue_()
    
    def navigate_to(self, url: str) -> None:
        """导航到指定 URL"""
        if not self._is_started:
            raise RuntimeError("Driver not started. Call start() first.")
        
        with self.tracer.trace_operation("navigate", url=url):
            start_time = time.time()
            self.page.goto(url)
            duration = time.time() - start_time
            
            self.logger.info("Navigated to URL", url=url, duration=duration)
    
    def get_current_url(self) -> str:
        """获取当前页面 URL"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        return self.page.url
    
    def get_page_title(self) -> str:
        """获取当前页面标题"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        return self.page.title()
    
    def find_element(self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS) -> Any:
        """查找单个元素"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        strategy = LocatorStrategy(strategy) if isinstance(strategy, str) else strategy
        
        with self.tracer.trace_operation("find_element", locator=locator, strategy=strategy.value):
            if strategy == LocatorStrategy.CSS:
                return self.page.locator(locator).first
            elif strategy == LocatorStrategy.XPATH:
                return self.page.locator(f"xpath={locator}").first
            elif strategy == LocatorStrategy.ID:
                return self.page.locator(f"#{locator}").first
            elif strategy == LocatorStrategy.CLASS:
                return self.page.locator(f".{locator}").first
            elif strategy == LocatorStrategy.TAG:
                return self.page.locator(locator).first
            elif strategy == LocatorStrategy.NAME:
                return self.page.locator(f"[name='{locator}']").first
            elif strategy == LocatorStrategy.LINK_TEXT:
                return self.page.get_by_text(locator).first
            elif strategy == LocatorStrategy.PARTIAL_LINK_TEXT:
                return self.page.get_by_text(locator, exact=False).first
            else:
                raise ValueError(f"Unsupported strategy: {strategy}")
    
    def find_elements(self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS) -> List[Any]:
        """查找多个元素"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        strategy = LocatorStrategy(strategy) if isinstance(strategy, str) else strategy
        
        with self.tracer.trace_operation("find_elements", locator=locator, strategy=strategy.value):
            if strategy == LocatorStrategy.CSS:
                return self.page.locator(locator).all()
            elif strategy == LocatorStrategy.XPATH:
                return self.page.locator(f"xpath={locator}").all()
            elif strategy == LocatorStrategy.ID:
                return self.page.locator(f"#{locator}").all()
            elif strategy == LocatorStrategy.CLASS:
                return self.page.locator(f".{locator}").all()
            elif strategy == LocatorStrategy.TAG:
                return self.page.locator(locator).all()
            elif strategy == LocatorStrategy.NAME:
                return self.page.locator(f"[name='{locator}']").all()
            elif strategy == LocatorStrategy.LINK_TEXT:
                return self.page.get_by_text(locator).all()
            elif strategy == LocatorStrategy.PARTIAL_LINK_TEXT:
                return self.page.get_by_text(locator, exact=False).all()
            else:
                raise ValueError(f"Unsupported strategy: {strategy}")
    
    def wait_for_element(self, locator: str, timeout: int = 10, 
                        strategy: WaitStrategy = WaitStrategy.EXPLICIT) -> Any:
        """等待元素出现"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        with self.tracer.trace_operation("wait_for_element", locator=locator, timeout=timeout):
            element = self.find_element(locator, LocatorStrategy.CSS)
            
            if strategy == WaitStrategy.EXPLICIT:
                element.wait_for(state="visible", timeout=timeout * 1000)
            elif strategy == WaitStrategy.FLUENT:
                element.wait_for(state="attached", timeout=timeout * 1000)
            elif strategy == WaitStrategy.IMPLICIT:
                # Playwright 的隐式等待通过页面设置
                self.page.set_default_timeout(timeout * 1000)
            
            return element
    
    def click_element(self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS) -> None:
        """点击元素"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        with self.tracer.trace_operation("click_element", locator=locator):
            element = self.find_element(locator, strategy)
            element.click()
    
    def input_text(self, locator: str, text: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS) -> None:
        """在元素中输入文本"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        with self.tracer.trace_operation("input_text", locator=locator, text_length=len(text)):
            element = self.find_element(locator, strategy)
            element.clear()
            element.fill(text)
    
    def get_element_text(self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS) -> str:
        """获取元素文本内容"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        with self.tracer.trace_operation("get_element_text", locator=locator):
            element = self.find_element(locator, strategy)
            return element.text_content() or ""
    
    def get_element_attribute(self, locator: str, attribute: str, 
                            strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS) -> str:
        """获取元素属性值"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        with self.tracer.trace_operation("get_element_attribute", locator=locator, attribute=attribute):
            element = self.find_element(locator, strategy)
            return element.get_attribute(attribute) or ""
    
    def is_element_displayed(self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS) -> bool:
        """检查元素是否可见"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        try:
            element = self.find_element(locator, strategy)
            return element.is_visible()
        except Exception:
            return False
    
    def is_element_enabled(self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS) -> bool:
        """检查元素是否可用"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        try:
            element = self.find_element(locator, strategy)
            return element.is_enabled()
        except Exception:
            return False
    
    def switch_to_window(self, window_handle: str) -> None:
        """切换到指定窗口"""
        if not self._is_started or not self.context:
            raise RuntimeError("Driver not started or no context available.")
        
        # Playwright 中窗口切换通过 context 管理
        for page in self.context.pages:
            if page.url == window_handle:
                self.page = page
                break
        else:
            raise ValueError(f"Window with handle {window_handle} not found")
    
    def switch_to_tab(self, tab_index: int) -> None:
        """切换到指定标签页"""
        if not self._is_started or not self.context:
            raise RuntimeError("Driver not started or no context available.")
        
        pages = self.context.pages
        if 0 <= tab_index < len(pages):
            self.page = pages[tab_index]
        else:
            raise ValueError(f"Tab index {tab_index} out of range. Available tabs: {len(pages)}")
    
    def get_window_handles(self) -> List[str]:
        """获取所有窗口句柄"""
        if not self._is_started or not self.context:
            raise RuntimeError("Driver not started or no context available.")
        
        return [page.url for page in self.context.pages]
    
    def close_current_tab(self) -> None:
        """关闭当前标签页"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        self.page.close()
        # 如果还有其他页面，切换到第一个
        if self.context and self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = None
    
    def open_new_tab(self, url: Optional[str] = None) -> None:
        """打开新标签页"""
        if not self._is_started or not self.context:
            raise RuntimeError("Driver not started or no context available.")
        
        self.page = self.context.new_page()
        if url:
            self.navigate_to(url)
    
    def intercept_requests(self, patterns: List[str]) -> None:
        """拦截网络请求"""
        if not self._is_started or not self.context:
            raise RuntimeError("Driver not started or no context available.")
        
        def route_handler(route: Route):
            if any(pattern in route.request.url for pattern in patterns):
                self._handle_route(route)
            else:
                route.continue_()
        
        self.context.route("**/*", route_handler)
    
    def get_network_logs(self) -> List[Dict[str, Any]]:
        """获取网络请求日志"""
        return self._network_logs.copy()
    
    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """截取页面截图"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        if not filename:
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
        
        self.page.screenshot(path=filename)
        return filename
    
    def execute_javascript(self, script: str, *args) -> Any:
        """执行 JavaScript 代码"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        return self.page.evaluate(script, *args)
    
    def scroll_to_element(self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS) -> None:
        """滚动到指定元素"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        element = self.find_element(locator, strategy)
        element.scroll_into_view_if_needed()
    
    def scroll_to_bottom(self) -> None:
        """滚动到页面底部"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    
    def scroll_to_top(self) -> None:
        """滚动到页面顶部"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        self.page.evaluate("window.scrollTo(0, 0)")
    
    def refresh_page(self) -> None:
        """刷新当前页面"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        self.page.reload()
    
    def go_back(self) -> None:
        """后退到上一页"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        self.page.go_back()
    
    def go_forward(self) -> None:
        """前进到下一页"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        self.page.go_forward()
    
    def set_device(self, device_name: str) -> None:
        """设置设备模拟配置"""
        if not self._is_started or not self.playwright:
            raise RuntimeError("Driver not started. Call start() first.")
        
        if device_name in self.playwright.devices:
            self._device_profile = self.playwright.devices[device_name]
            # 重新创建上下文以应用设备配置
            if self.context:
                self.context.close()
            self.context = self.browser.new_context(**self._device_profile)
            self.page = self.context.new_page()
        else:
            available_devices = list(self.playwright.devices.keys())
            raise ValueError(f"Device '{device_name}' not found. Available devices: {available_devices[:10]}...")
    
    def get_available_devices(self) -> List[str]:
        """获取可用设备列表"""
        if not self._is_started or not self.playwright:
            raise RuntimeError("Driver not started. Call start() first.")
        
        return list(self.playwright.devices.keys())
    
    def set_viewport(self, width: int, height: int) -> None:
        """设置视口大小"""
        if not self._is_started or not self.page:
            raise RuntimeError("Driver not started or no page available.")
        
        self.page.set_viewport_size({"width": width, "height": height})
    
    def set_user_agent(self, user_agent: str) -> None:
        """设置用户代理"""
        if not self._is_started or not self.browser:
            raise RuntimeError("Driver not started. Call start() first.")
        
        # 重新创建上下文以应用用户代理
        if self.context:
            self.context.close()
        self.context = self.browser.new_context(user_agent=user_agent)
        self.page = self.context.new_page()