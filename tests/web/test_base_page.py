"""测试基础页面对象模型"""
import pytest
from unittest.mock import Mock
from src.phoenixframe.web.base_page import BasePage


class MockPage(BasePage):
    """模拟页面实现"""
    
    def navigate(self, url=None):
        self.driver.get(url or self.url)
    
    def wait_for_page_load(self, timeout=10):
        return True
    
    def is_element_present(self, locator):
        return True
    
    def click_element(self, locator):
        pass
    
    def input_text(self, locator, text):
        pass
    
    def get_text(self, locator):
        return "test text"


def test_base_page_initialization():
    """测试基础页面初始化"""
    mock_driver = Mock()
    page = MockPage(mock_driver)
    
    assert page.driver == mock_driver
    assert page.url is None


def test_base_page_navigate():
    """测试页面导航"""
    mock_driver = Mock()
    page = MockPage(mock_driver)
    
    # 测试使用参数URL导航
    page.navigate("https://example.com")
    mock_driver.get.assert_called_with("https://example.com")
    
    # 测试使用实例URL导航
    page.url = "https://default.com"
    page.navigate()
    mock_driver.get.assert_called_with("https://default.com")


def test_base_page_get_title():
    """测试获取页面标题"""
    mock_driver = Mock()
    mock_driver.title = "Test Page"
    page = MockPage(mock_driver)
    
    assert page.get_title() == "Test Page"


def test_base_page_get_current_url():
    """测试获取当前URL"""
    mock_driver = Mock()
    mock_driver.current_url = "https://current.com"
    page = MockPage(mock_driver)
    
    assert page.get_current_url() == "https://current.com"


def test_base_page_abstract_methods():
    """测试抽象方法实现"""
    mock_driver = Mock()
    page = MockPage(mock_driver)
    
    # 测试所有抽象方法都有实现
    assert page.wait_for_page_load() is True
    assert page.is_element_present("selector") is True
    page.click_element("selector")  # 不应抛出异常
    page.input_text("selector", "text")  # 不应抛出异常
    assert page.get_text("selector") == "test text"
