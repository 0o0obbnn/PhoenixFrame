import pytest

# Adjust the import path to be relative to the project structure
from phoenixframe.core.config import load_config, ConfigModel

@pytest.fixture(scope="function")
def mock_phoenix_yaml(tmp_path):
    """Creates a temporary phoenix.yaml file for testing."""
    config_content = """
    app_name: MyTestApp
    version: "0.1"
    environments:
      dev:
        base_url: http://dev.api.example.com
      prod:
        base_url: http://prod.api.example.com
    """
    config_file = tmp_path / "phoenix.yaml"
    config_file.write_text(config_content)
    return config_file

def test_load_config_basic_loading(mock_phoenix_yaml):
    """
    Tests if the load_config function can correctly load a basic YAML file.
    """
    config = load_config(mock_phoenix_yaml)
    assert isinstance(config, ConfigModel)
    assert config.app_name == "MyTestApp"
    assert config.version == "0.1"
    assert "dev" in config.environments
    assert config.environments["dev"].base_url == "http://dev.api.example.com"

def test_load_config_with_missing_optional_fields(tmp_path):
    """
    Tests if load_config correctly uses default values for missing optional fields.
    """
    config_content = """
    app_name: AnotherApp
    """
    config_file = tmp_path / "phoenix.yaml"
    config_file.write_text(config_content)
    config = load_config(config_file)
    assert config.app_name == "AnotherApp"
    assert config.version == "1.0"  # Should use Pydantic default
    # Default environments should contain "default" environment
    assert "default" in config.environments

def test_load_config_with_invalid_yaml(tmp_path):
    """
    Tests if load_config raises a ValueError (wrapping ValidationError) for an invalid YAML structure.
    """
    invalid_config_content = """
    app_name: InvalidApp
    version: 1.0
    environments:
      - dev: # This is a list, but a dict is expected
          base_url: http://dev.api.example.com
    """
    config_file = tmp_path / "invalid_phoenix.yaml"
    config_file.write_text(invalid_config_content)
    with pytest.raises(ValueError, match="Configuration validation failed"):
        load_config(config_file)

def test_load_config_with_env_override(tmp_path, monkeypatch):
    """
    Tests if load_config correctly overrides config values with environment variables.
    """
    config_content = """
    app_name: DefaultApp
    environments:
      test:
        base_url: http://default.example.com
    reporting:
      allure:
        enabled: false
    """
    config_file = tmp_path / "phoenix.yaml"
    config_file.write_text(config_content)

    # Mock environment variable
    monkeypatch.setenv("PHOENIX_ENVIRONMENTS_TEST_BASE_URL", "http://overridden.example.com")
    monkeypatch.setenv("PHOENIX_REPORTING_ALLURE_ENABLED", "true")

    config = load_config(config_file)
    assert config.app_name == "DefaultApp"
    assert config.environments["test"].base_url == "http://overridden.example.com"
    assert config.reporting.allure["enabled"] is True

def test_reporting_config_default_values(tmp_path):
    """
    Tests if ReportingConfig uses correct default values when not specified.
    """
    config_content = """
    app_name: TestReportingDefaults
    """
    config_file = tmp_path / "phoenix.yaml"
    config_file.write_text(config_content)

    config = load_config(config_file)
    assert config.reporting.allure["enabled"] is True
    assert config.reporting.allure["report_dir"] == "allure-report"
    assert config.reporting.allure["results_dir"] == "allure-results"
