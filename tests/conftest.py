import pytest
from src.phoenixframe.web.selenium_driver import SeleniumDriver, SeleniumPage
from src.phoenixframe.web.playwright_driver import PlaywrightDriver, PlaywrightPage
from src.phoenixframe.api.client import APIClient

@pytest.fixture(scope="function")
def selenium_driver():
    """Provides a Selenium WebDriver instance."""
    driver_manager = SeleniumDriver(browser="chrome", headless=True)
    driver = driver_manager.start()
    yield driver
    driver_manager.quit()

@pytest.fixture(scope="function")
def selenium_page(selenium_driver):
    """Provides a Selenium page object."""
    return SeleniumPage(selenium_driver)

@pytest.fixture(scope="function")
def playwright_driver():
    """Provides a Playwright driver instance."""
    try:
        driver_manager = PlaywrightDriver(browser="chromium", headless=True)
        page = driver_manager.start()
        yield driver_manager
    except ImportError:
        pytest.skip("Playwright not available")
    finally:
        driver_manager.quit()

@pytest.fixture(scope="function")
def playwright_page(playwright_driver):
    """Provides a Playwright page object."""
    page = playwright_driver.get_page()
    return PlaywrightPage(page)

@pytest.fixture(scope="function")
def api_client():
    """Provides an API client instance."""
    client = APIClient()
    yield client
    client.close()

# Legacy fixture for backward compatibility
@pytest.fixture(scope="function")
def selenium_page_legacy():
    """Legacy fixture - provides raw WebDriver for backward compatibility."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()
