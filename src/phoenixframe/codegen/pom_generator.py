from .core import CodeGenerator

class POMGenerator(CodeGenerator):
    """Generates Page Object Model (POM) code and data files from structured UI interaction data."""
    def generate(self, data: list) -> dict:
        """Generates Python POM code and YAML data from UI interaction data.

        Returns a dictionary with keys like 'pom_code', 'test_code', 'data_yaml'.
        """
        pom_code_lines = [
            "from playwright.sync_api import Page, expect # Or async_playwright for async",
            "",
            "class BasePage:",
            "    def __init__(self, page: Page):",
            "        self.page = page",
            "",
        ]

        test_code_lines = [
            "import pytest",
            "from playwright.sync_api import Page # Or async_playwright for async",
            "# from .your_pom_file import YourPageObject # Assuming POM is in a separate file",
            "",
            "# This is auto-generated test code. Please review and enhance as needed.",
            "",
        ]

        data_yaml_content = {"test_data": {}}

        # Simple example: identify locators and actions
        for i, interaction in enumerate(data):
            if interaction["type"] == "page_interaction":
                method = interaction["method"]
                args = interaction["args"]
                # keywords = interaction["keywords"]  # Currently unused

                # Example: Convert page.locator("selector").click()
                if method == "click" and args:
                    selector = args[0].strip("'\"")
                    # Add to POM (simplified)
                    pom_code_lines.append(f"    def click_element_{i}(self):\n        self.page.locator(\"{selector}\").click()\n")
                    # Add to test
                    test_code_lines.append(f"def test_ui_action_{i}(page: Page):\n    # your_page = YourPageObject(page)\n    # your_page.click_element_{i}()\n")

                elif method == "fill" and args and len(args) > 1:
                    selector = args[0].strip("'\"")
                    value = args[1].strip("'\"")
                    data_key = f"input_value_{i}"
                    data_yaml_content["test_data"][data_key] = value

                    pom_code_lines.append(f"    def fill_element_{i}(self, value):\n        self.page.locator(\"{selector}\").fill(value)\n")
                    test_code_lines.append(f"def test_ui_action_{i}(page: Page, test_data):\n    # your_page = YourPageObject(page)\n    # your_page.fill_element_{i}(test_data['{data_key}'])\n")

        return {
            "pom_code": "\n".join(pom_code_lines),
            "test_code": "\n".join(test_code_lines),
            "data_yaml": data_yaml_content
        }