"""WebDriver管理器

提供统一的WebDriver管理功能，包括：
- 多种浏览器支持（Chrome, Firefox, Safari等）
- Selenium和Playwright驱动统一管理
- 驱动配置和选项管理
- 会话管理和清理
- 远程WebDriver支持
"""

import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..core.lifecycle import LifecycleManager
from ..observability.logger import get_logger


class BrowserType(Enum):
    """浏览器类型枚举"""
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"
    CHROMIUM = "chromium"
    WEBKIT = "webkit"


class DriverType(Enum):
    """驱动类型枚举"""
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"


@dataclass
class DriverConfig:
    """驱动配置"""
    browser: BrowserType
    driver_type: DriverType
    headless: bool = False
    window_size: str = "1920x1080"
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    binary_path: Optional[str] = None
    driver_path: Optional[str] = None
    arguments: List[str] = field(default_factory=list)
    experimental_options: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    extensions: List[str] = field(default_factory=list)
    downloads_path: Optional[str] = None
    timeout: int = 30
    remote_url: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)


class BaseDriverManager(ABC):
    """驱动管理器基类"""
    
    def __init__(self, config: DriverConfig):
        self.config = config
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._driver: Optional[Any] = None
        self._is_started = False
    
    @abstractmethod
    def start(self) -> Any:
        """启动驱动"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止驱动"""
        pass
    
    @abstractmethod
    def restart(self) -> Any:
        """重启驱动"""
        pass
    
    def is_started(self) -> bool:
        """检查驱动是否已启动"""
        return self._is_started
    
    def get_driver(self) -> Optional[Any]:
        """获取驱动实例"""
        return self._driver


class SeleniumDriverManager(BaseDriverManager):
    """Selenium驱动管理器"""
    
    def __init__(self, config: DriverConfig):
        super().__init__(config)
        self._import_selenium()
    
    def _import_selenium(self):
        """导入Selenium模块"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service as ChromeService
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from selenium.webdriver.edge.service import Service as EdgeService
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.edge.options import Options as EdgeOptions
            from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
            
            self.webdriver = webdriver
            self.services = {
                BrowserType.CHROME: ChromeService,
                BrowserType.FIREFOX: FirefoxService,
                BrowserType.EDGE: EdgeService
            }
            self.options_classes = {
                BrowserType.CHROME: ChromeOptions,
                BrowserType.FIREFOX: FirefoxOptions,
                BrowserType.EDGE: EdgeOptions
            }
            self.capabilities = DesiredCapabilities
            
        except ImportError as e:
            raise ImportError(f"Selenium not installed: {e}")
    
    def start(self) -> Any:
        """启动Selenium驱动"""
        if self._is_started:
            return self._driver
        
        try:
            self.logger.info(f"Starting Selenium {self.config.browser.value} driver")
            
            # 远程驱动
            if self.config.remote_url:
                self._driver = self._create_remote_driver()
            else:
                self._driver = self._create_local_driver()
            
            self._is_started = True
            self.logger.info("Selenium driver started successfully")
            return self._driver
            
        except Exception as e:
            self.logger.error(f"Failed to start Selenium driver: {e}")
            raise
    
    def _create_local_driver(self) -> Any:
        """创建本地驱动"""
        browser = self.config.browser
        
        if browser == BrowserType.CHROME:
            return self._create_chrome_driver()
        elif browser == BrowserType.FIREFOX:
            return self._create_firefox_driver()
        elif browser == BrowserType.EDGE:
            return self._create_edge_driver()
        elif browser == BrowserType.SAFARI:
            return self._create_safari_driver()
        else:
            raise ValueError(f"Unsupported browser: {browser}")
    
    def _create_chrome_driver(self) -> Any:
        """创建Chrome驱动"""
        options = self.options_classes[BrowserType.CHROME]()
        
        # 基本配置
        if self.config.headless:
            options.add_argument("--headless")
        
        # 窗口大小
        if self.config.window_size:
            options.add_argument(f"--window-size={self.config.window_size}")
        
        # 用户代理
        if self.config.user_agent:
            options.add_argument(f"--user-agent={self.config.user_agent}")
        
        # 代理
        if self.config.proxy:
            options.add_argument(f"--proxy-server={self.config.proxy}")
        
        # 二进制路径
        if self.config.binary_path:
            options.binary_location = self.config.binary_path
        
        # 下载路径
        if self.config.downloads_path:
            prefs = {"download.default_directory": self.config.downloads_path}
            options.add_experimental_option("prefs", prefs)
        
        # 自定义参数
        for arg in self.config.arguments:
            options.add_argument(arg)
        
        # 实验性选项
        for key, value in self.config.experimental_options.items():
            options.add_experimental_option(key, value)
        
        # 首选项
        if self.config.preferences:
            options.add_experimental_option("prefs", self.config.preferences)
        
        # 扩展
        for extension in self.config.extensions:
            options.add_extension(extension)
        
        # 创建服务
        service_args = {}
        if self.config.driver_path:
            service_args["executable_path"] = self.config.driver_path
        
        service = self.services[BrowserType.CHROME](**service_args)
        
        return self.webdriver.Chrome(service=service, options=options)
    
    def _create_firefox_driver(self) -> Any:
        """创建Firefox驱动"""
        options = self.options_classes[BrowserType.FIREFOX]()
        
        # 基本配置
        if self.config.headless:
            options.add_argument("--headless")
        
        # 窗口大小
        if self.config.window_size:
            width, height = self.config.window_size.split('x')
            options.add_argument(f"--width={width}")
            options.add_argument(f"--height={height}")
        
        # 二进制路径
        if self.config.binary_path:
            options.binary_location = self.config.binary_path
        
        # 首选项
        for key, value in self.config.preferences.items():
            options.set_preference(key, value)
        
        # 下载路径
        if self.config.downloads_path:
            options.set_preference("browser.download.dir", self.config.downloads_path)
            options.set_preference("browser.download.folderList", 2)
        
        # 自定义参数
        for arg in self.config.arguments:
            options.add_argument(arg)
        
        # 创建服务
        service_args = {}
        if self.config.driver_path:
            service_args["executable_path"] = self.config.driver_path
        
        service = self.services[BrowserType.FIREFOX](**service_args)
        
        return self.webdriver.Firefox(service=service, options=options)
    
    def _create_edge_driver(self) -> Any:
        """创建Edge驱动"""
        options = self.options_classes[BrowserType.EDGE]()
        
        # 基本配置
        if self.config.headless:
            options.add_argument("--headless")
        
        # 窗口大小
        if self.config.window_size:
            options.add_argument(f"--window-size={self.config.window_size}")
        
        # 用户代理
        if self.config.user_agent:
            options.add_argument(f"--user-agent={self.config.user_agent}")
        
        # 二进制路径
        if self.config.binary_path:
            options.binary_location = self.config.binary_path
        
        # 自定义参数
        for arg in self.config.arguments:
            options.add_argument(arg)
        
        # 创建服务
        service_args = {}
        if self.config.driver_path:
            service_args["executable_path"] = self.config.driver_path
        
        service = self.services[BrowserType.EDGE](**service_args)
        
        return self.webdriver.Edge(service=service, options=options)
    
    def _create_safari_driver(self) -> Any:
        """创建Safari驱动"""
        return self.webdriver.Safari()
    
    def _create_remote_driver(self) -> Any:
        """创建远程驱动"""
        capabilities = self._build_capabilities()
        return self.webdriver.Remote(
            command_executor=self.config.remote_url,
            desired_capabilities=capabilities
        )
    
    def _build_capabilities(self) -> Dict[str, Any]:
        """构建capabilities"""
        browser = self.config.browser
        
        if browser == BrowserType.CHROME:
            caps = self.capabilities.CHROME.copy()
        elif browser == BrowserType.FIREFOX:
            caps = self.capabilities.FIREFOX.copy()
        elif browser == BrowserType.EDGE:
            caps = self.capabilities.EDGE.copy()
        elif browser == BrowserType.SAFARI:
            caps = self.capabilities.SAFARI.copy()
        else:
            caps = {}
        
        # 添加自定义capabilities
        caps.update(self.config.capabilities)
        
        return caps
    
    def stop(self) -> None:
        """停止驱动"""
        if self._driver and self._is_started:
            try:
                self._driver.quit()
                self.logger.info("Selenium driver stopped")
            except Exception as e:
                self.logger.error(f"Error stopping Selenium driver: {e}")
            finally:
                self._driver = None
                self._is_started = False
    
    def restart(self) -> Any:
        """重启驱动"""
        self.stop()
        return self.start()


class PlaywrightDriverManager(BaseDriverManager):
    """Playwright驱动管理器"""
    
    def __init__(self, config: DriverConfig):
        super().__init__(config)
        self._playwright = None
        self._browser = None
        self._context = None
        self._import_playwright()
    
    def _import_playwright(self):
        """导入Playwright模块"""
        try:
            from playwright.sync_api import sync_playwright
            self.sync_playwright = sync_playwright
        except ImportError as e:
            raise ImportError(f"Playwright not installed: {e}")
    
    def start(self) -> Any:
        """启动Playwright驱动"""
        if self._is_started:
            return self._driver
        
        try:
            self.logger.info(f"Starting Playwright {self.config.browser.value} driver")
            
            # 启动Playwright
            self._playwright = self.sync_playwright()
            playwright_instance = self._playwright.__enter__()
            
            # 获取浏览器
            browser_type = self._get_browser_type(playwright_instance)
            
            # 启动浏览器
            launch_options = self._build_launch_options()
            self._browser = browser_type.launch(**launch_options)
            
            # 创建上下文
            context_options = self._build_context_options()
            self._context = self._browser.new_context(**context_options)
            
            # 创建页面
            self._driver = self._context.new_page()
            
            # 设置超时
            self._driver.set_default_timeout(self.config.timeout * 1000)
            
            self._is_started = True
            self.logger.info("Playwright driver started successfully")
            return self._driver
            
        except Exception as e:
            self.logger.error(f"Failed to start Playwright driver: {e}")
            self._cleanup()
            raise
    
    def _get_browser_type(self, playwright_instance):
        """获取浏览器类型"""
        browser = self.config.browser
        
        if browser in (BrowserType.CHROME, BrowserType.CHROMIUM):
            return playwright_instance.chromium
        elif browser == BrowserType.FIREFOX:
            return playwright_instance.firefox
        elif browser in (BrowserType.SAFARI, BrowserType.WEBKIT):
            return playwright_instance.webkit
        else:
            raise ValueError(f"Unsupported browser for Playwright: {browser}")
    
    def _build_launch_options(self) -> Dict[str, Any]:
        """构建浏览器启动选项"""
        options = {
            "headless": self.config.headless
        }
        
        if self.config.binary_path:
            options["executable_path"] = self.config.binary_path
        
        if self.config.arguments:
            options["args"] = self.config.arguments
        
        return options
    
    def _build_context_options(self) -> Dict[str, Any]:
        """构建上下文选项"""
        options = {}
        
        # 视口大小
        if self.config.window_size:
            width, height = map(int, self.config.window_size.split('x'))
            options["viewport"] = {"width": width, "height": height}
        
        # 用户代理
        if self.config.user_agent:
            options["user_agent"] = self.config.user_agent
        
        # 代理
        if self.config.proxy:
            options["proxy"] = {"server": self.config.proxy}
        
        # 下载路径
        if self.config.downloads_path:
            options["accept_downloads"] = True
            # Playwright会自动处理下载到指定目录
        
        return options
    
    def stop(self) -> None:
        """停止驱动"""
        if self._is_started:
            try:
                self._cleanup()
                self.logger.info("Playwright driver stopped")
            except Exception as e:
                self.logger.error(f"Error stopping Playwright driver: {e}")
            finally:
                self._driver = None
                self._is_started = False
    
    def _cleanup(self) -> None:
        """清理资源"""
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass
            self._driver = None
        
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        
        if self._playwright:
            try:
                self._playwright.__exit__(None, None, None)
            except Exception:
                pass
            self._playwright = None
    
    def restart(self) -> Any:
        """重启驱动"""
        self.stop()
        return self.start()
    
    def get_context(self):
        """获取浏览器上下文"""
        return self._context
    
    def get_browser(self):
        """获取浏览器实例"""
        return self._browser


class WebDriverManager(LifecycleManager):
    """统一WebDriver管理器"""
    
    def __init__(self, name: str = "WebDriverManager"):
        super().__init__(name)
        self._drivers: Dict[str, BaseDriverManager] = {}
        self._lock = threading.RLock()
        self._default_config = DriverConfig(
            browser=BrowserType.CHROME,
            driver_type=DriverType.SELENIUM,
            headless=True
        )
    
    def create_driver(self, 
                     name: str,
                     browser: Union[str, BrowserType] = BrowserType.CHROME,
                     driver_type: Union[str, DriverType] = DriverType.SELENIUM,
                     config: Optional[DriverConfig] = None) -> Any:
        """
        创建并启动驱动
        
        Args:
            name: 驱动名称
            browser: 浏览器类型
            driver_type: 驱动类型
            config: 驱动配置
            
        Returns:
            驱动实例
        """
        with self._lock:
            if name in self._drivers:
                raise ValueError(f"Driver {name} already exists")
            
            # 转换枚举类型
            if isinstance(browser, str):
                browser = BrowserType(browser.lower())
            if isinstance(driver_type, str):
                driver_type = DriverType(driver_type.lower())
            
            # 使用提供的配置或创建默认配置
            if config is None:
                config = DriverConfig(browser=browser, driver_type=driver_type)
            
            # 创建驱动管理器
            if driver_type == DriverType.SELENIUM:
                driver_manager = SeleniumDriverManager(config)
            elif driver_type == DriverType.PLAYWRIGHT:
                driver_manager = PlaywrightDriverManager(config)
            else:
                raise ValueError(f"Unsupported driver type: {driver_type}")
            
            # 启动驱动
            driver = driver_manager.start()
            
            # 注册驱动
            self._drivers[name] = driver_manager
            self.add_resource(name, driver_manager)
            
            self.logger.info(f"Created driver: {name} ({driver_type.value} {browser.value})")
            return driver
    
    def get_driver(self, name: str) -> Optional[Any]:
        """
        获取驱动实例
        
        Args:
            name: 驱动名称
            
        Returns:
            驱动实例或None
        """
        with self._lock:
            driver_manager = self._drivers.get(name)
            if driver_manager:
                return driver_manager.get_driver()
            return None
    
    def stop_driver(self, name: str) -> None:
        """
        停止指定驱动
        
        Args:
            name: 驱动名称
        """
        with self._lock:
            driver_manager = self._drivers.get(name)
            if driver_manager:
                driver_manager.stop()
                self.logger.info(f"Stopped driver: {name}")
    
    def restart_driver(self, name: str) -> Any:
        """
        重启指定驱动
        
        Args:
            name: 驱动名称
            
        Returns:
            重启后的驱动实例
        """
        with self._lock:
            driver_manager = self._drivers.get(name)
            if driver_manager:
                driver = driver_manager.restart()
                self.logger.info(f"Restarted driver: {name}")
                return driver
            return None
    
    def remove_driver(self, name: str) -> None:
        """
        移除驱动
        
        Args:
            name: 驱动名称
        """
        with self._lock:
            if name in self._drivers:
                driver_manager = self._drivers.pop(name)
                driver_manager.stop()
                self.logger.info(f"Removed driver: {name}")
    
    def list_drivers(self) -> List[str]:
        """获取所有驱动名称"""
        return list(self._drivers.keys())
    
    def is_driver_started(self, name: str) -> bool:
        """
        检查驱动是否已启动
        
        Args:
            name: 驱动名称
            
        Returns:
            bool: 是否已启动
        """
        driver_manager = self._drivers.get(name)
        return driver_manager.is_started() if driver_manager else False
    
    def _do_dispose(self) -> None:
        """清理所有驱动"""
        with self._lock:
            for name, driver_manager in list(self._drivers.items()):
                try:
                    driver_manager.stop()
                except Exception as e:
                    self.logger.error(f"Error stopping driver {name}: {e}")
            
            self._drivers.clear()
            self.logger.info("All drivers cleaned up")


# 全局WebDriver管理器
_global_driver_manager: Optional[WebDriverManager] = None
_driver_manager_lock = threading.Lock()


def get_driver_manager() -> WebDriverManager:
    """获取全局WebDriver管理器"""
    global _global_driver_manager
    if _global_driver_manager is None:
        with _driver_manager_lock:
            if _global_driver_manager is None:
                _global_driver_manager = WebDriverManager()
    return _global_driver_manager


def create_driver(name: str, 
                 browser: Union[str, BrowserType] = BrowserType.CHROME,
                 driver_type: Union[str, DriverType] = DriverType.SELENIUM,
                 config: Optional[DriverConfig] = None) -> Any:
    """创建驱动的便捷函数"""
    manager = get_driver_manager()
    return manager.create_driver(name, browser, driver_type, config)


def get_driver(name: str) -> Optional[Any]:
    """获取驱动的便捷函数"""
    manager = get_driver_manager()
    return manager.get_driver(name)


def stop_driver(name: str) -> None:
    """停止驱动的便捷函数"""
    manager = get_driver_manager()
    manager.stop_driver(name)