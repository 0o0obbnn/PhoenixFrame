"""增强 Web 驱动测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from phoenixframe.web.playwright_driver import PlaywrightDriver
from phoenixframe.web.base_driver import WaitStrategy, LocatorStrategy


class TestPlaywrightDriver:
    """Playwright 驱动测试"""
    
    @pytest.fixture
    def driver(self):
        """创建驱动实例"""
        return PlaywrightDriver(headless=True)
    
    def test_find_element_css(self, driver):
        """测试 CSS 选择器查找元素"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_page.locator.return_value.first = mock_element
            
            result = driver.find_element("button.submit", LocatorStrategy.CSS)
            
            mock_page.locator.assert_called_once_with("button.submit")
            assert result == mock_element
    
    def test_find_element_xpath(self, driver):
        """测试 XPath 选择器查找元素"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_page.locator.return_value.first = mock_element
            
            result = driver.find_element("//button[@class='submit']", LocatorStrategy.XPATH)
            
            mock_page.locator.assert_called_once_with("xpath=//button[@class='submit']")
            assert result == mock_element
    
    def test_find_element_id(self, driver):
        """测试 ID 选择器查找元素"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_page.locator.return_value.first = mock_element
            
            result = driver.find_element("submit-btn", LocatorStrategy.ID)
            
            mock_page.locator.assert_called_once_with("#submit-btn")
            assert result == mock_element
    
    def test_wait_for_element_explicit(self, driver):
        """测试显式等待元素"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_page.locator.return_value.first = mock_element
            
            result = driver.wait_for_element("button.submit", timeout=5, 
                                          strategy=WaitStrategy.EXPLICIT)
            
            mock_element.wait_for.assert_called_once_with(
                state="visible", timeout=5000
            )
            assert result == mock_element
    
    def test_wait_for_element_fluent(self, driver):
        """测试流式等待元素"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_page.locator.return_value.first = mock_element
            
            result = driver.wait_for_element("button.submit", timeout=5, 
                                          strategy=WaitStrategy.FLUENT)
            
            mock_element.wait_for.assert_called_once_with(
                state="attached", timeout=5000
            )
            assert result == mock_element
    
    def test_click_element(self, driver):
        """测试点击元素"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_page.locator.return_value.first = mock_element
            
            driver.click_element("button.submit")
            
            mock_page.locator.assert_called_once_with("button.submit")
            mock_element.click.assert_called_once()
    
    def test_input_text(self, driver):
        """测试输入文本"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_page.locator.return_value.first = mock_element
            
            driver.input_text("input[name='username']", "testuser")
            
            mock_page.locator.assert_called_once_with("input[name='username']")
            mock_element.clear.assert_called_once()
            mock_element.fill.assert_called_once_with("testuser")
    
    def test_get_element_text(self, driver):
        """测试获取元素文本"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_element.text_content.return_value = "Submit Button"
            mock_page.locator.return_value.first = mock_element
            
            result = driver.get_element_text("button.submit")
            
            assert result == "Submit Button"
            mock_page.locator.assert_called_once_with("button.submit")
    
    def test_get_element_attribute(self, driver):
        """测试获取元素属性"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_element.get_attribute.return_value = "submit"
            mock_page.locator.return_value.first = mock_element
            
            result = driver.get_element_attribute("button.submit", "type")
            
            assert result == "submit"
            mock_page.locator.assert_called_once_with("button.submit")
            mock_element.get_attribute.assert_called_once_with("type")
    
    def test_is_element_displayed(self, driver):
        """测试检查元素是否可见"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_element.is_visible.return_value = True
            mock_page.locator.return_value.first = mock_element
            
            result = driver.is_element_displayed("button.submit")
            
            assert result is True
            mock_page.locator.assert_called_once_with("button.submit")
            mock_element.is_visible.assert_called_once()
    
    def test_is_element_enabled(self, driver):
        """测试检查元素是否可用"""
        with patch.object(driver, 'page') as mock_page:
            mock_element = Mock()
            mock_element.is_enabled.return_value = True
            mock_page.locator.return_value.first = mock_element
            
            result = driver.is_element_enabled("button.submit")
            
            assert result is True
            mock_page.locator.assert_called_once_with("button.submit")
            mock_element.is_enabled.assert_called_once()
    
    def test_navigate_to(self, driver):
        """测试导航到 URL"""
        with patch.object(driver, 'page') as mock_page:
            driver._is_started = True
            
            driver.navigate_to("https://example.com")
            
            mock_page.goto.assert_called_once_with("https://example.com")
    
    def test_get_current_url(self, driver):
        """测试获取当前 URL"""
        with patch.object(driver, 'page') as mock_page:
            mock_page.url = "https://example.com"
            driver._is_started = True
            
            result = driver.get_current_url()
            
            assert result == "https://example.com"
    
    def test_get_page_title(self, driver):
        """测试获取页面标题"""
        with patch.object(driver, 'page') as mock_page:
            mock_page.title.return_value = "Example Page"
            driver._is_started = True
            
            result = driver.get_page_title()
            
            assert result == "Example Page"
            mock_page.title.assert_called_once()
    
    def test_take_screenshot(self, driver):
        """测试截图功能"""
        with patch.object(driver, 'page') as mock_page, \
             patch('os.makedirs') as mock_makedirs:
            
            driver._is_started = True
            
            result = driver.take_screenshot("test.png")
            
            assert result == "test.png"
            mock_page.screenshot.assert_called_once_with(path="test.png")
            mock_makedirs.assert_called_once()
    
    def test_execute_javascript(self, driver):
        """测试执行 JavaScript"""
        with patch.object(driver, 'page') as mock_page:
            mock_page.evaluate.return_value = "result"
            driver._is_started = True
            
            result = driver.execute_javascript("return document.title;")
            
            assert result == "result"
            mock_page.evaluate.assert_called_once_with("return document.title;")
    
    def test_switch_to_tab(self, driver):
        """测试切换标签页"""
        with patch.object(driver, 'context') as mock_context:
            mock_page1 = Mock()
            mock_page2 = Mock()
            mock_context.pages = [mock_page1, mock_page2]
            driver._is_started = True
            
            driver.switch_to_tab(1)
            
            assert driver.page == mock_page2
    
    def test_switch_to_tab_invalid_index(self, driver):
        """测试切换无效标签页索引"""
        with patch.object(driver, 'context') as mock_context:
            mock_context.pages = [Mock()]
            driver._is_started = True
            
            with pytest.raises(ValueError, match="Tab index 1 out of range"):
                driver.switch_to_tab(1)
    
    def test_get_network_logs(self, driver):
        """测试获取网络日志"""
        driver._network_logs = [
            {"url": "https://example.com", "method": "GET", "timestamp": 1234567890}
        ]
        
        logs = driver.get_network_logs()
        
        assert len(logs) == 1
        assert logs[0]["url"] == "https://example.com"
        assert logs[0]["method"] == "GET"
    
    def test_context_manager(self, driver):
        """测试上下文管理器"""
        with patch.object(driver, 'start') as mock_start, \
             patch.object(driver, 'stop') as mock_stop:
            
            with driver:
                mock_start.assert_called_once()
            
            mock_stop.assert_called_once()
    
    def test_driver_not_started_error(self, driver):
        """测试驱动未启动时的错误"""
        with pytest.raises(RuntimeError, match="Driver not started"):
            driver.navigate_to("https://example.com")
    
    def test_unsupported_locator_strategy(self, driver):
        """测试不支持的定位策略"""
        with pytest.raises(ValueError, match="Unsupported strategy"):
            driver.find_element("test", "invalid_strategy")
