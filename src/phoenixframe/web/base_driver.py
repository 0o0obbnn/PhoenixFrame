"""统一的 Web 驱动接口抽象层

提供 Selenium 和 Playwright 的统一接口，确保功能一致性。
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Union


class WaitStrategy(Enum):
    """等待策略枚举"""

    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    FLUENT = "fluent"


class LocatorStrategy(Enum):
    """元素定位策略枚举"""

    CSS = "css"
    XPATH = "xpath"
    ID = "id"
    CLASS = "class"
    TAG = "tag"
    NAME = "name"
    LINK_TEXT = "link_text"
    PARTIAL_LINK_TEXT = "partial_link_text"


class BaseWebDriver(ABC):
    """统一的 Web 驱动接口

    定义所有 Web 驱动必须实现的核心方法，确保 Selenium 和 Playwright
    功能对齐，提供一致的用户体验。
    """

    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        """初始化 Web 驱动

        Args:
            headless: 是否无头模式运行
            browser_type: 浏览器类型 (chromium, firefox, webkit)
        """
        self.headless = headless
        self.browser_type = browser_type
        self._is_started = False

    @abstractmethod
    def start(self) -> None:
        """启动浏览器实例"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止浏览器实例"""
        pass

    @abstractmethod
    def navigate_to(self, url: str) -> None:
        """导航到指定 URL"""
        pass

    @abstractmethod
    def get_current_url(self) -> str:
        """获取当前页面 URL"""
        pass

    @abstractmethod
    def get_page_title(self) -> str:
        """获取当前页面标题"""
        pass

    @abstractmethod
    def find_element(
        self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS
    ) -> Any:
        """查找单个元素

        Args:
            locator: 元素定位器
            strategy: 定位策略

        Returns:
            元素对象
        """
        pass

    @abstractmethod
    def find_elements(
        self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS
    ) -> list[Any]:
        """查找多个元素

        Args:
            locator: 元素定位器
            strategy: 定位策略

        Returns:
            元素对象列表
        """
        pass

    @abstractmethod
    def wait_for_element(
        self, locator: str, timeout: int = 10, strategy: WaitStrategy = WaitStrategy.EXPLICIT
    ) -> Any:
        """等待元素出现

        Args:
            locator: 元素定位器
            timeout: 超时时间（秒）
            strategy: 等待策略

        Returns:
            元素对象
        """
        pass

    @abstractmethod
    def click_element(
        self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS
    ) -> None:
        """点击元素"""
        pass

    @abstractmethod
    def input_text(
        self, locator: str, text: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS
    ) -> None:
        """在元素中输入文本"""
        pass

    @abstractmethod
    def get_element_text(
        self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS
    ) -> str:
        """获取元素文本内容"""
        pass

    @abstractmethod
    def get_element_attribute(
        self,
        locator: str,
        attribute: str,
        strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS,
    ) -> str:
        """获取元素属性值"""
        pass

    @abstractmethod
    def is_element_displayed(
        self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS
    ) -> bool:
        """检查元素是否可见"""
        pass

    @abstractmethod
    def is_element_enabled(
        self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS
    ) -> bool:
        """检查元素是否可用"""
        pass

    @abstractmethod
    def switch_to_window(self, window_handle: str) -> None:
        """切换到指定窗口"""
        pass

    @abstractmethod
    def switch_to_tab(self, tab_index: int) -> None:
        """切换到指定标签页"""
        pass

    @abstractmethod
    def get_window_handles(self) -> list[str]:
        """获取所有窗口句柄"""
        pass

    @abstractmethod
    def close_current_tab(self) -> None:
        """关闭当前标签页"""
        pass

    @abstractmethod
    def open_new_tab(self, url: Optional[str] = None) -> None:
        """打开新标签页"""
        pass

    @abstractmethod
    def intercept_requests(self, patterns: list[str]) -> None:
        """拦截网络请求

        Args:
            patterns: 要拦截的 URL 模式列表
        """
        pass

    @abstractmethod
    def get_network_logs(self) -> list[dict[str, Any]]:
        """获取网络请求日志

        Returns:
            网络请求日志列表
        """
        pass

    @abstractmethod
    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """截取页面截图

        Args:
            filename: 截图文件名，如果为 None 则自动生成

        Returns:
            截图文件路径
        """
        pass

    @abstractmethod
    def execute_javascript(self, script: str, *args) -> Any:
        """执行 JavaScript 代码

        Args:
            script: JavaScript 代码
            *args: 传递给脚本的参数

        Returns:
            脚本执行结果
        """
        pass

    @abstractmethod
    def scroll_to_element(
        self, locator: str, strategy: Union[str, LocatorStrategy] = LocatorStrategy.CSS
    ) -> None:
        """滚动到指定元素"""
        pass

    @abstractmethod
    def scroll_to_bottom(self) -> None:
        """滚动到页面底部"""
        pass

    @abstractmethod
    def scroll_to_top(self) -> None:
        """滚动到页面顶部"""
        pass

    @abstractmethod
    def refresh_page(self) -> None:
        """刷新当前页面"""
        pass

    @abstractmethod
    def go_back(self) -> None:
        """后退到上一页"""
        pass

    @abstractmethod
    def go_forward(self) -> None:
        """前进到下一页"""
        pass

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()

    @property
    def is_started(self) -> bool:
        """检查驱动是否已启动"""
        return self._is_started
