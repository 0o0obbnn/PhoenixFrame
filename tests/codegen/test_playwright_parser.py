import pytest
from phoenixframe.codegen.playwright_parser import PlaywrightParser

def test_playwright_parser_basic_script():
    """Tests PlaywrightParser with a basic codegen script."""
    script_content = """
from playwright.sync_api import Page, expect

def test_example(page: Page) -> None:
    page.goto("https://www.google.com/")
    page.locator("body").fill("test query")
    page.locator('input[name="btnK"]').click()
    expect(page).to_have_url("https://www.google.com/search?q=test+query")
"""
    parser = PlaywrightParser()
    parsed_data = parser.parse(script_content)

    assert len(parsed_data) == 4

    assert parsed_data[0]["method"] == "goto"
    assert parsed_data[0]["args"] == ["'https://www.google.com/'"]

    assert parsed_data[1]["method"] == "fill"
    assert parsed_data[1]["args"] == ["'body'", "'test query'"]

    assert parsed_data[2]["method"] == "click"
    assert parsed_data[2]["args"] == ["'input[name=\"btnK\"]'"]

    assert parsed_data[3]["method"] == "to_have_url"
    assert parsed_data[3]["args"] == ["'https://www.google.com/search?q=test+query'"]

def test_playwright_parser_empty_script():
    """Tests PlaywrightParser with an empty script."""
    script_content = """
"""
    parser = PlaywrightParser()
    parsed_data = parser.parse(script_content)
    assert len(parsed_data) == 0

def test_playwright_parser_invalid_syntax():
    """Tests PlaywrightParser with a script containing invalid Python syntax."""
    script_content = "def test_invalid(page): page.click("""
    parser = PlaywrightParser()
    with pytest.raises(ValueError, match="Invalid Python script syntax"):
        parser.parse(script_content)
