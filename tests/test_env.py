from click.testing import CliRunner
from phoenixframe.cli import main
import os

def test_env_list_command(tmp_path):
    """Tests that the env list command runs and lists environments."""
    # Create a mock phoenix.yaml in a temporary directory
    mock_config_content = """
environments:
  default:
    base_url: http://localhost:8080
  staging:
    base_url: http://staging.example.com
"""
    mock_config_path = tmp_path / "phoenix.yaml"
    mock_config_path.write_text(mock_config_content)

    # Change current working directory to tmp_path for the test
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["env", "list"])

    # Restore original working directory
    os.chdir(original_cwd)

    assert result.exit_code == 0
    assert "Listing environments from phoenix.yaml" in result.output
    assert "default" in result.output # This will be more specific once env.py is fully implemented
