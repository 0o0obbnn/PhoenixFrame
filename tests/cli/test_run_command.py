import pytest
from click.testing import CliRunner
from unittest.mock import patch
from src.phoenixframe.cli import main as phoenix_cli_entrypoint

@pytest.fixture(scope="function")
def simple_test_file(tmp_path):
    """Creates a simple test file for testing the run command."""
    test_file = tmp_path / "test_simple.py"
    test_file.write_text("def test_success(): assert True")
    return str(test_file)

@patch("src.phoenixframe.core.runner.PhoenixRunner")
def test_phoenix_run_invokes_runner(mock_runner_class, simple_test_file):
    """
    Tests if the 'phoenix run' command invokes the PhoenixRunner.
    """
    # Setup mock instance
    mock_runner_instance = mock_runner_class.return_value
    mock_runner_instance.run_tests.return_value = {"pytest_exit_code": 0}

    runner = CliRunner()
    result = runner.invoke(phoenix_cli_entrypoint, ["run", simple_test_file])

    # Verify the runner was instantiated and run_tests was called
    mock_runner_class.assert_called_once()
    mock_runner_instance.run_tests.assert_called_once_with(test_paths=[simple_test_file], pytest_extra_args=[])
    assert result.exit_code == 0
