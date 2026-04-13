"""测试Playwright Driver封装"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.phoenixframe.web.playwright_driver import PlaywrightDriver, PlaywrightPage


class TestPlaywrightDriver:
    """测试Playwright Driver管理器"""
    
    def test_playwright_not_available(self):
        """测试Playwright不可用时的错误"""
        with patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', False):
            with pytest.raises(ImportError, match="Playwright is not installed"):
                PlaywrightDriver()
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    def test_initialization_default(self):
        """测试默认初始化"""
        driver = PlaywrightDriver()
        assert driver.browser_name == "chromium"
        assert driver.headless is False
        assert driver.options == {}
        assert driver.playwright is None
        assert driver.browser is None
        assert driver.context is None
        assert driver.page is None
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    def test_initialization_custom(self):
        """测试自定义初始化"""
        options = {"slow_mo": 100, "devtools": True}
        driver = PlaywrightDriver(browser="Firefox", headless=True, options=options)
        
        assert driver.browser_name == "firefox"
        assert driver.headless is True
        assert driver.options == options
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    @patch('src.phoenixframe.web.playwright_driver.sync_playwright')
    def test_start_chromium(self, mock_sync_playwright):
        """测试启动Chromium浏览器"""
        # 模拟playwright对象链
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        driver = PlaywrightDriver(browser="chromium", headless=True)
        result = driver.start()
        
        assert result == mock_page
        assert driver.playwright == mock_playwright
        assert driver.browser == mock_browser
        assert driver.context == mock_context
        assert driver.page == mock_page
        
        # 验证调用
        mock_playwright.chromium.launch.assert_called_with(headless=True)
        mock_browser.new_context.assert_called_once()
        mock_context.new_page.assert_called_once()
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    @patch('src.phoenixframe.web.playwright_driver.sync_playwright')
    def test_start_firefox(self, mock_sync_playwright):
        """测试启动Firefox浏览器"""
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.firefox.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        driver = PlaywrightDriver(browser="firefox")
        driver.start()
        
        mock_playwright.firefox.launch.assert_called_with(headless=False)
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    @patch('src.phoenixframe.web.playwright_driver.sync_playwright')
    def test_start_webkit(self, mock_sync_playwright):
        """测试启动WebKit浏览器"""
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.webkit.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        driver = PlaywrightDriver(browser="webkit")
        driver.start()
        
        mock_playwright.webkit.launch.assert_called_with(headless=False)
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    @patch('src.phoenixframe.web.playwright_driver.sync_playwright')
    def test_start_with_options(self, mock_sync_playwright):
        """测试使用自定义选项启动"""
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        options = {"slow_mo": 100, "devtools": True}
        driver = PlaywrightDriver(options=options)
        driver.start()
        
        mock_playwright.chromium.launch.assert_called_with(
            headless=False, 
            slow_mo=100, 
            devtools=True
        )
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    def test_start_unsupported_browser(self):
        """测试启动不支持的浏览器"""
        driver = PlaywrightDriver(browser="safari")
        
        with patch('src.phoenixframe.web.playwright_driver.sync_playwright'):
            with pytest.raises(ValueError, match="Unsupported browser: safari"):
                driver.start()
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    def test_start_already_started(self):
        """测试重复启动"""
        driver = PlaywrightDriver()
        mock_page = Mock()
        driver.page = mock_page
        
        result = driver.start()
        assert result == mock_page
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    def test_quit_full_cleanup(self):
        """测试完整清理"""
        driver = PlaywrightDriver()
        
        # 模拟所有组件
        mock_page = Mock()
        mock_context = Mock()
        mock_browser = Mock()
        mock_playwright = Mock()
        
        driver.page = mock_page
        driver.context = mock_context
        driver.browser = mock_browser
        driver.playwright = mock_playwright
        
        driver.quit()
        
        # 验证清理顺序
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        
        # 验证重置
        assert driver.page is None
        assert driver.context is None
        assert driver.browser is None
        assert driver.playwright is None
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    def test_quit_partial_cleanup(self):
        """测试部分清理"""
        driver = PlaywrightDriver()
        
        # 只设置部分组件
        mock_browser = Mock()
        driver.browser = mock_browser
        
        driver.quit()
        
        # 只清理存在的组件
        mock_browser.close.assert_called_once()
        assert driver.browser is None
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    def test_get_page(self):
        """测试获取Page实例"""
        driver = PlaywrightDriver()
        mock_page = Mock()
        driver.page = mock_page
        
        result = driver.get_page()
        assert result == mock_page
    
    @patch('src.phoenixframe.web.playwright_driver.PLAYWRIGHT_AVAILABLE', True)
    def test_get_page_none(self):
        """测试获取未启动的Page实例"""
        driver = PlaywrightDriver()
        result = driver.get_page()
        assert result is None


class TestPlaywrightPage:
    """测试基于Playwright的页面对象"""
    
    def test_initialization(self):
        """测试初始化"""
        mock_page = Mock()
        page = PlaywrightPage(mock_page)
        
        assert page.driver == mock_page
    
    def test_navigate_with_url_parameter(self):
        """测试使用URL参数导航"""
        mock_page = Mock()
        page = PlaywrightPage(mock_page)
        page.navigate("https://example.com")
        
        mock_page.goto.assert_called_with("https://example.com")
    
    def test_navigate_with_instance_url(self):
        """测试使用实例URL导航"""
        mock_page = Mock()
        page = PlaywrightPage(mock_page)
        page.url = "https://test.com"
        page.navigate()
        
        mock_page.goto.assert_called_with("https://test.com")
    
    def test_navigate_no_url(self):
        """测试没有URL时导航"""
        mock_page = Mock()
        page = PlaywrightPage(mock_page)
        
        with pytest.raises(ValueError, match="URL is required"):
            page.navigate()
    
    def test_wait_for_page_load_success(self):
        """测试成功等待页面加载"""
        mock_page = Mock()
        page = PlaywrightPage(mock_page)
        
        result = page.wait_for_page_load(timeout=5)
        
        assert result is True
        mock_page.wait_for_load_state.assert_called_with("networkidle", timeout=5000)
    
    def test_wait_for_page_load_exception(self):
        """测试页面加载异常"""
        mock_page = Mock()
        mock_page.wait_for_load_state.side_effect = Exception("Timeout")
        page = PlaywrightPage(mock_page)
        
        result = page.wait_for_page_load()
        
        assert result is False
    
    def test_is_element_present_found(self):
        """测试元素存在"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_page.locator.return_value = mock_locator
        
        page = PlaywrightPage(mock_page)
        result = page.is_element_present(".test-element")
        
        assert result is True
        mock_page.locator.assert_called_with(".test-element")
    
    def test_is_element_present_not_found(self):
        """测试元素不存在"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_locator.count.return_value = 0
        mock_page.locator.return_value = mock_locator
        
        page = PlaywrightPage(mock_page)
        result = page.is_element_present(".test-element")
        
        assert result is False
    
    def test_is_element_present_exception(self):
        """测试元素检查异常"""
        mock_page = Mock()
        mock_page.locator.side_effect = Exception("Locator error")
        
        page = PlaywrightPage(mock_page)
        result = page.is_element_present(".test-element")
        
        assert result is False
    
    def test_click_element(self):
        """测试点击元素"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value = mock_locator
        
        page = PlaywrightPage(mock_page)
        page.click_element(".button")
        
        mock_page.locator.assert_called_with(".button")
        mock_locator.click.assert_called_once()
    
    def test_input_text(self):
        """测试输入文本"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value = mock_locator
        
        page = PlaywrightPage(mock_page)
        page.input_text(".input", "test text")
        
        mock_page.locator.assert_called_with(".input")
        mock_locator.clear.assert_called_once()
        mock_locator.fill.assert_called_with("test text")
    
    def test_get_text(self):
        """测试获取元素文本"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_locator.text_content.return_value = "element text"
        mock_page.locator.return_value = mock_locator
        
        page = PlaywrightPage(mock_page)
        result = page.get_text(".text-element")
        
        assert result == "element text"
        mock_page.locator.assert_called_with(".text-element")
    
    def test_get_text_none(self):
        """测试获取空文本"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_locator.text_content.return_value = None
        mock_page.locator.return_value = mock_locator
        
        page = PlaywrightPage(mock_page)
        result = page.get_text(".text-element")
        
        assert result == ""
    
    def test_wait_for_element(self):
        """测试等待元素出现"""
        mock_page = Mock()
        mock_element = Mock()
        mock_page.wait_for_selector.return_value = mock_element
        
        page = PlaywrightPage(mock_page)
        result = page.wait_for_element(".wait-element", timeout=15)
        
        assert result == mock_element
        mock_page.wait_for_selector.assert_called_with(".wait-element", timeout=15000)
    
    def test_screenshot_with_path(self):
        """测试截图到文件"""
        mock_page = Mock()
        
        page = PlaywrightPage(mock_page)
        
        with patch('builtins.open', mock_open(read_data=b'screenshot_data')) as mock_file:
            result = page.screenshot("/path/to/screenshot.png")
            
            assert result == b'screenshot_data'
            mock_page.screenshot.assert_called_with(path="/path/to/screenshot.png")
            mock_file.assert_called_with("/path/to/screenshot.png", 'rb')
    
    def test_screenshot_without_path(self):
        """测试截图到内存"""
        mock_page = Mock()
        mock_page.screenshot.return_value = b'screenshot_bytes'
        
        page = PlaywrightPage(mock_page)
        result = page.screenshot()
        
        assert result == b'screenshot_bytes'
        mock_page.screenshot.assert_called_with()


# 需要导入mock_open
from unittest.mock import mock_open
