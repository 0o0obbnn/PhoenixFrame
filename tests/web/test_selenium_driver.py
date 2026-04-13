"""测试Selenium WebDriver封装"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from src.phoenixframe.web.selenium_driver import SeleniumDriver, SeleniumPage


class TestSeleniumDriver:
    """测试Selenium WebDriver管理器"""
    
    def test_initialization_default(self):
        """测试默认初始化"""
        driver = SeleniumDriver()
        assert driver.browser == "chrome"
        assert driver.headless is False
        assert driver.options == {}
        assert driver.driver is None
    
    def test_initialization_custom(self):
        """测试自定义初始化"""
        options = {"window-size": "1920,1080", "disable-gpu": True}
        driver = SeleniumDriver(browser="Firefox", headless=True, options=options)
        
        assert driver.browser == "firefox"
        assert driver.headless is True
        assert driver.options == options
    
    @patch('src.phoenixframe.web.selenium_driver.webdriver.Chrome')
    @patch('src.phoenixframe.web.selenium_driver.ChromeOptions')
    def test_start_chrome_default(self, mock_chrome_options, mock_chrome):
        """测试启动Chrome浏览器（默认配置）"""
        mock_options = Mock()
        mock_chrome_options.return_value = mock_options
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        driver = SeleniumDriver()
        result = driver.start()
        
        assert result == mock_driver
        assert driver.driver == mock_driver
        
        # 验证选项设置
        mock_options.add_argument.assert_any_call("--no-sandbox")
        mock_options.add_argument.assert_any_call("--disable-dev-shm-usage")
        mock_chrome.assert_called_once_with(options=mock_options)
    
    @patch('src.phoenixframe.web.selenium_driver.webdriver.Chrome')
    @patch('src.phoenixframe.web.selenium_driver.ChromeOptions')
    def test_start_chrome_headless(self, mock_chrome_options, mock_chrome):
        """测试启动Chrome浏览器（无头模式）"""
        mock_options = Mock()
        mock_chrome_options.return_value = mock_options
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        driver = SeleniumDriver(headless=True)
        driver.start()
        
        # 验证无头模式选项
        mock_options.add_argument.assert_any_call("--headless")
    
    @patch('src.phoenixframe.web.selenium_driver.webdriver.Chrome')
    @patch('src.phoenixframe.web.selenium_driver.ChromeOptions')
    def test_start_chrome_custom_options(self, mock_chrome_options, mock_chrome):
        """测试启动Chrome浏览器（自定义选项）"""
        mock_options = Mock()
        mock_chrome_options.return_value = mock_options
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        custom_options = {
            "window-size": "1920,1080",
            "disable-gpu": True,
            "incognito": False
        }
        driver = SeleniumDriver(options=custom_options)
        driver.start()
        
        # 验证自定义选项
        mock_options.add_argument.assert_any_call("--window-size=1920,1080")
        mock_options.add_argument.assert_any_call("--disable-gpu")
        # incognito=False 不应该添加参数
    
    @patch('src.phoenixframe.web.selenium_driver.webdriver.Firefox')
    @patch('src.phoenixframe.web.selenium_driver.FirefoxOptions')
    def test_start_firefox(self, mock_firefox_options, mock_firefox):
        """测试启动Firefox浏览器"""
        mock_options = Mock()
        mock_firefox_options.return_value = mock_options
        mock_driver = Mock()
        mock_firefox.return_value = mock_driver
        
        driver = SeleniumDriver(browser="firefox", headless=True)
        result = driver.start()
        
        assert result == mock_driver
        assert driver.driver == mock_driver
        
        # 验证Firefox选项
        mock_options.add_argument.assert_called_with("--headless")
        mock_firefox.assert_called_once_with(options=mock_options)
    
    def test_start_unsupported_browser(self):
        """测试启动不支持的浏览器"""
        driver = SeleniumDriver(browser="safari")
        
        with pytest.raises(ValueError, match="Unsupported browser: safari"):
            driver.start()
    
    def test_start_already_started(self):
        """测试重复启动"""
        driver = SeleniumDriver()
        mock_driver = Mock()
        driver.driver = mock_driver
        
        result = driver.start()
        assert result == mock_driver
    
    def test_quit_with_driver(self):
        """测试关闭WebDriver"""
        driver = SeleniumDriver()
        mock_driver = Mock()
        driver.driver = mock_driver
        
        driver.quit()
        
        mock_driver.quit.assert_called_once()
        assert driver.driver is None
    
    def test_quit_without_driver(self):
        """测试关闭未启动的WebDriver"""
        driver = SeleniumDriver()
        # 不应该抛出异常
        driver.quit()
    
    def test_get_driver(self):
        """测试获取WebDriver实例"""
        driver = SeleniumDriver()
        mock_driver = Mock()
        driver.driver = mock_driver
        
        result = driver.get_driver()
        assert result == mock_driver
    
    def test_get_driver_none(self):
        """测试获取未启动的WebDriver实例"""
        driver = SeleniumDriver()
        result = driver.get_driver()
        assert result is None


class TestSeleniumPage:
    """测试基于Selenium的页面对象"""
    
    def test_initialization(self):
        """测试初始化"""
        mock_driver = Mock()
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait') as mock_wait:
            page = SeleniumPage(mock_driver)
            
            assert page.driver == mock_driver
            mock_wait.assert_called_with(mock_driver, 10)
    
    def test_navigate_with_url_parameter(self):
        """测试使用URL参数导航"""
        mock_driver = Mock()
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait'):
            page = SeleniumPage(mock_driver)
            page.navigate("https://example.com")
            
            mock_driver.get.assert_called_with("https://example.com")
    
    def test_navigate_with_instance_url(self):
        """测试使用实例URL导航"""
        mock_driver = Mock()
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait'):
            page = SeleniumPage(mock_driver)
            page.url = "https://test.com"
            page.navigate()
            
            mock_driver.get.assert_called_with("https://test.com")
    
    def test_navigate_no_url(self):
        """测试没有URL时导航"""
        mock_driver = Mock()
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait'):
            page = SeleniumPage(mock_driver)
            
            with pytest.raises(ValueError, match="URL is required"):
                page.navigate()
    
    @patch('src.phoenixframe.web.selenium_driver.WebDriverWait')
    def test_wait_for_page_load_success(self, mock_wait_class):
        """测试成功等待页面加载"""
        mock_driver = Mock()
        mock_driver.execute_script.return_value = "complete"
        
        mock_wait = Mock()
        mock_wait_class.return_value = mock_wait
        
        page = SeleniumPage(mock_driver)
        result = page.wait_for_page_load()
        
        assert result is True
        mock_wait.until.assert_called()
    
    @patch('src.phoenixframe.web.selenium_driver.WebDriverWait')
    def test_wait_for_page_load_timeout(self, mock_wait_class):
        """测试页面加载超时"""
        mock_driver = Mock()
        
        mock_wait = Mock()
        mock_wait.until.side_effect = TimeoutException()
        mock_wait_class.return_value = mock_wait
        
        page = SeleniumPage(mock_driver)
        result = page.wait_for_page_load()
        
        assert result is False
    
    def test_is_element_present_found(self):
        """测试元素存在"""
        mock_driver = Mock()
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait'):
            page = SeleniumPage(mock_driver)
            result = page.is_element_present(".test-element")
            
            assert result is True
            mock_driver.find_element.assert_called_with(
                page.driver.find_element.call_args[0][0], 
                ".test-element"
            )
    
    def test_is_element_present_not_found(self):
        """测试元素不存在"""
        mock_driver = Mock()
        mock_driver.find_element.side_effect = NoSuchElementException()
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait'):
            page = SeleniumPage(mock_driver)
            result = page.is_element_present(".test-element")
            
            assert result is False
    
    def test_click_element(self):
        """测试点击元素"""
        mock_driver = Mock()
        mock_wait = Mock()
        mock_element = Mock()
        mock_wait.until.return_value = mock_element
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait', return_value=mock_wait):
            page = SeleniumPage(mock_driver)
            page.click_element(".button")
            
            mock_element.click.assert_called_once()
    
    def test_input_text(self):
        """测试输入文本"""
        mock_driver = Mock()
        mock_wait = Mock()
        mock_element = Mock()
        mock_wait.until.return_value = mock_element
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait', return_value=mock_wait):
            page = SeleniumPage(mock_driver)
            page.input_text(".input", "test text")
            
            mock_element.clear.assert_called_once()
            mock_element.send_keys.assert_called_with("test text")
    
    def test_get_text(self):
        """测试获取元素文本"""
        mock_driver = Mock()
        mock_wait = Mock()
        mock_element = Mock()
        mock_element.text = "element text"
        mock_wait.until.return_value = mock_element
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait', return_value=mock_wait):
            page = SeleniumPage(mock_driver)
            result = page.get_text(".text-element")
            
            assert result == "element text"
    
    def test_wait_for_element(self):
        """测试等待元素出现"""
        mock_driver = Mock()
        mock_element = Mock()
        
        with patch('src.phoenixframe.web.selenium_driver.WebDriverWait') as mock_wait_class:
            mock_wait = Mock()
            mock_wait.until.return_value = mock_element
            mock_wait_class.return_value = mock_wait
            
            page = SeleniumPage(mock_driver)
            result = page.wait_for_element(".wait-element", timeout=15)
            
            assert result == mock_element
            mock_wait_class.assert_called_with(mock_driver, 15)
