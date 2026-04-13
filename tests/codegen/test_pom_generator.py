from phoenixframe.codegen.pom_generator import POMGenerator

def test_pom_generator_basic_interactions():
    """Tests POMGenerator with basic UI interactions."""
    parsed_data = [
        {
            "type": "page_interaction",
            "method": "goto",
            "args": ["'https://example.com'"],
            "keywords": {},
            "line_no": 1
        },
        {
            "type": "page_interaction",
            "method": "fill",
            "args": ["'#username'", "'testuser'"],
            "keywords": {},
            "line_no": 2
        },
        {
            "type": "page_interaction",
            "method": "click",
            "args": ["'#submit'"],
            "keywords": {},
            "line_no": 3
        }
    ]

    generator = POMGenerator()
    generated_assets = generator.generate(parsed_data)

    assert "pom_code" in generated_assets
    assert "test_code" in generated_assets
    assert "data_yaml" in generated_assets

    # Verify POM code content
    pom_code = generated_assets["pom_code"]
    assert "class BasePage:" in pom_code
    assert "def click_element_2(self):" in pom_code # Index 2 for click
    assert "self.page.locator(\"#submit\").click()" in pom_code
    assert "def fill_element_1(self, value):" in pom_code # Index 1 for fill
    assert "self.page.locator(\"#username\").fill(value)" in pom_code

    # Verify test code content
    test_code = generated_assets["test_code"]
    assert "def test_ui_action_1(page: Page, test_data):" in test_code # Index 1 for fill
    assert "# your_page.fill_element_1(test_data['input_value_1'])" in test_code

    # Verify data YAML content
    data_yaml = generated_assets["data_yaml"]
    assert "test_data" in data_yaml
    assert "input_value_1" in data_yaml["test_data"]
    assert data_yaml["test_data"]["input_value_1"] == "testuser"

def test_pom_generator_empty_data():
    """Tests POMGenerator with empty parsed data."""
    parsed_data = []
    generator = POMGenerator()
    generated_assets = generator.generate(parsed_data)

    assert "pom_code" in generated_assets
    assert "test_code" in generated_assets
    assert "data_yaml" in generated_assets

    # Ensure no specific interaction code is generated
    assert "click_element" not in generated_assets["pom_code"]
    assert "fill_element" not in generated_assets["pom_code"]
    assert "test_ui_action" not in generated_assets["test_code"]
    assert generated_assets["data_yaml"] == {"test_data": {}}
