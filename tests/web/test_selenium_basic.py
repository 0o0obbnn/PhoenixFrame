import pytest
from selenium.webdriver.common.by import By

# This test requires a running WebDriver and a browser.
# It will be skipped if the necessary components are not available.
@pytest.mark.selenium
def test_selenium_page_can_navigate_to_url(selenium_page):
    """
    Tests if the selenium_page fixture can navigate to a URL.
    """
    selenium_page.get("https://www.google.com")
    assert "Google" in selenium_page.title

@pytest.mark.selenium
def test_selenium_page_can_find_element(selenium_page):
    """
    Tests if the selenium_page fixture can find an element on a page.
    """
    selenium_page.get("https://www.google.com")
    element = selenium_page.find_element(By.NAME, "q")
    assert element is not None
