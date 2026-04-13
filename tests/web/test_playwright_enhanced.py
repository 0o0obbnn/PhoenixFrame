"""测试Playwright增强功能"""
import pytest
from unittest.mock import Mock, patch

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from src.phoenixframe.web.playwright_driver import PlaywrightDriver


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestPlaywrightEnhancedFeatures:
    """测试Playwright增强功能"""
    
    def test_set_device_not_found(self):
        """测试设置不存在的设备"""
        with patch('src.phoenixframe.web.playwright_driver.sync_playwright') as mock_sync_playwright:
            mock_playwright = Mock()
            mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
            mock_playwright.devices = {"iPhone 11": {}}
            
            driver = PlaywrightDriver()
            driver.start = Mock()
            driver.playwright = mock_playwright
            
            # 测试设置不存在的设备
            with pytest.raises(ValueError, match="Device 'NonExistentDevice' not found"):
                driver.set_device("NonExistentDevice")
    
    def test_set_viewport(self):
        """测试设置视口大小"""
        with patch('src.phoenixframe.web.playwright_driver.sync_playwright'):
            driver = PlaywrightDriver()
            mock_page = Mock()
            driver.page = mock_page
            
            # 测试设置视口大小
            driver.set_viewport(1920, 1080)
            mock_page.set_viewport_size.assert_called_with({"width": 1920, "height": 1080})
    
    def test_intercept_requests(self):
        """测试网络请求拦截"""
        with patch('src.phoenixframe.web.playwright_driver.sync_playwright'):
            driver = PlaywrightDriver()
            mock_page = Mock()
            driver.page = mock_page
            
            def handler(route):
                pass
                
            # 测试拦截请求
            driver.intercept_requests("**/*.{png,jpg,jpeg}", handler)
            mock_page.route.assert_called_with("**/*.{png,jpg,jpeg}", handler)
    
    def test_stop_intercepting_requests(self):
        """测试停止网络请求拦截"""
        with patch('src.phoenixframe.web.playwright_driver.sync_playwright'):
            driver = PlaywrightDriver()
            mock_page = Mock()
            driver.page = mock_page
            
            # 测试停止拦截请求
            driver.stop_intercepting_requests("**/*.{png,jpg,jpeg}")
            mock_page.unroute.assert_called_with("**/*.{png,jpg,jpeg}")