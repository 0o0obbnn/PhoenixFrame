# Web自动化模块
from .selenium_driver import SeleniumDriver
from .playwright_driver import PlaywrightDriver
from .base_page import BasePage, WaitCondition, PageError, ElementNotFoundError, ElementNotClickableError, PageLoadTimeoutError
from .selenium_page import SeleniumPage
from .playwright_page import PlaywrightPage
from .driver_manager import (
    BrowserType, DriverType, DriverConfig, BaseDriverManager,
    SeleniumDriverManager, PlaywrightDriverManager, WebDriverManager,
    get_driver_manager, create_driver, get_driver, stop_driver
)

__all__ = [
    # 原有驱动
    "SeleniumDriver", "PlaywrightDriver", 
    
    # 页面对象
    "BasePage", "SeleniumPage", "PlaywrightPage",
    
    # 异常和枚举
    "WaitCondition", "PageError", "ElementNotFoundError", 
    "ElementNotClickableError", "PageLoadTimeoutError",
    
    # 驱动管理
    "BrowserType", "DriverType", "DriverConfig", "BaseDriverManager",
    "SeleniumDriverManager", "PlaywrightDriverManager", "WebDriverManager",
    "get_driver_manager", "create_driver", "get_driver", "stop_driver"
]
