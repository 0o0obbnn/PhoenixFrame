import pytest
from unittest.mock import patch
from phoenixframe.core.runner import PhoenixRunner
from phoenixframe.core.config import ConfigModel, ReportingConfig, EnvironmentConfig

@pytest.fixture
def mock_config():
    """Fixture to provide a mock configuration."""
    return ConfigModel(
        reporting=ReportingConfig(
            allure={"enabled": True, "results_dir": "test-allure-results"}
        ),
        environment=EnvironmentConfig(
            env="test",
            variables={}
        )
    )

@pytest.fixture
def runner():
    """Fixture to provide a PhoenixRunner instance."""
    return PhoenixRunner()

@patch('phoenixframe.core.runner.pytest.main')
@patch('phoenixframe.core.runner.get_config')
@patch('phoenixframe.core.runner.trigger_hook')
def test_run_tests_with_config(mock_trigger, mock_get_config, mock_pytest_main, runner, mock_config):
    """Test running tests with configuration integration."""
    # Setup mocks
    mock_get_config.return_value = mock_config
    mock_pytest_main.return_value = 0
    test_paths = ["tests/unit"]

    # Execute test run
    result = runner.run_tests(test_paths=test_paths)

    # Verify configuration was used
    mock_pytest_main.assert_called_once_with([
        "tests/unit",
        "--alluredir",
        "test-allure-results"
    ])
    assert result["pytest_exit_code"] == 0

    # Verify hooks were triggered
    mock_trigger.assert_any_call("on_test_run_start", config=mock_config)
    mock_trigger.assert_any_call("on_test_run_end", exit_code=0)
    assert mock_trigger.call_count == 2

@patch('phoenixframe.core.runner.pytest.main')
@patch('phoenixframe.core.runner.get_config')
@patch('phoenixframe.core.runner.trigger_hook')
def test_run_tests_with_extra_args(mock_trigger, mock_get_config, mock_pytest_main, runner, mock_config):
    """Test running tests with extra pytest arguments."""
    # Setup mocks
    mock_get_config.return_value = mock_config
    mock_pytest_main.return_value = 0
    test_paths = ["tests/integration"]
    extra_args = ["-v", "-k", "test_login"]

    # Execute test run
    result = runner.run_tests(test_paths=test_paths, pytest_extra_args=extra_args)

    # Verify all arguments were passed correctly
    expected_args = [
        "tests/integration",
        "--alluredir",
        "test-allure-results",
        "-v",
        "-k",
        "test_login"
    ]
    mock_pytest_main.assert_called_once_with(expected_args)
    assert result["pytest_exit_code"] == 0

@patch('phoenixframe.core.runner.pytest.main')
@patch('phoenixframe.core.runner.get_config')
def test_run_tests_without_allure(mock_get_config, mock_pytest_main, runner):
    """Test running tests when Allure is disabled."""
    # Setup mocks with Allure disabled
    config = ConfigModel(
        reporting=ReportingConfig(allure={"enabled": False}),
        environment=EnvironmentConfig()
    )
    mock_get_config.return_value = config
    mock_pytest_main.return_value = 1
    test_paths = ["tests/integration"]

    # Execute test run
    result = runner.run_tests(test_paths=test_paths)

    # Verify Allure arguments were not added
    mock_pytest_main.assert_called_once_with(["tests/integration"])
    assert result["pytest_exit_code"] == 1

@patch('phoenixframe.core.runner.pytest.main')
@patch('phoenixframe.core.runner.get_config')
def test_run_tests_without_test_paths(mock_get_config, mock_pytest_main, runner, mock_config):
    """Test running tests with no test paths specified."""
    mock_get_config.return_value = mock_config
    mock_pytest_main.return_value = 0

    # Execute test run with no paths
    result = runner.run_tests(test_paths=[])

    # Verify pytest was called with allure arguments only (since test_paths is empty)
    mock_pytest_main.assert_called_once_with(["--alluredir", "test-allure-results"])
    assert result["pytest_exit_code"] == 0

@patch('phoenixframe.core.runner.pytest.main')
@patch('phoenixframe.core.runner.get_config')
def test_run_tests_with_custom_allure_dir(mock_get_config, mock_pytest_main, runner):
    """Test running tests with custom Allure results directory."""
    # Setup mocks with custom Allure directory
    config = ConfigModel(
        reporting=ReportingConfig(
            allure={"enabled": True, "results_dir": "custom-allure-dir"}
        ),
        environment=EnvironmentConfig()
    )
    mock_get_config.return_value = config
    mock_pytest_main.return_value = 0

    # Execute test run
    result = runner.run_tests(test_paths=["tests/e2e"])

    # Verify custom directory was used
    mock_pytest_main.assert_called_once_with([
        "tests/e2e",
        "--alluredir",
        "custom-allure-dir"
    ])
    assert result["pytest_exit_code"] == 0