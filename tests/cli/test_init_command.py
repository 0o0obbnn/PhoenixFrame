import shutil
import pytest
from click.testing import CliRunner
import yaml

# Adjust the import path to be relative to the project structure
from phoenixframe.cli import main as phoenix_cli_entrypoint

@pytest.fixture(scope="function")
def temp_test_dir(tmp_path):
    """Creates a temporary directory to run the init command in."""
    project_name = "test_phoenix_project"
    project_path = tmp_path / project_name
    
    # Yield the parent temp path, as the command creates the project dir
    yield tmp_path

    # Cleanup after test
    if project_path.exists():
        shutil.rmtree(project_path)

def test_phoenix_init_creates_basic_structure(temp_test_dir):
    """
    Tests if the 'phoenix init' command creates the expected directories and files.
    """
    runner = CliRunner()
    project_name = "test_phoenix_project"
    project_path = temp_test_dir / project_name

    # Execute the init command
    result = runner.invoke(phoenix_cli_entrypoint, ["init", str(project_path)])
    
    # Verify command execution
    assert f"Project '{project_path}' initialized successfully." in result.output, f"Unexpected output: {result.output}"

    # Verify directories
    expected_dirs = [
        project_path / "src" / "phoenixframe",
        project_path / "tests",
        project_path / "configs",
        project_path / "data",
        project_path / "docs",
        project_path / "templates",
    ]
    for d in expected_dirs:
        assert d.is_dir(), f"Expected directory {d} was not created."

    # Verify files
    expected_files = [
        project_path / "pyproject.toml",
        project_path / "README.md",
        project_path / ".gitignore",
        project_path / "configs" / "phoenix.yaml",
    ]
    for f in expected_files:
        assert f.is_file(), f"Expected file {f} was not created."

    # Verify phoenix.yaml content
    config_file_path = project_path / "configs" / "phoenix.yaml"
    assert config_file_path.is_file()
    with open(config_file_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
        assert config_data["app_name"] == project_name
        assert config_data["version"] == "1.0"
        assert "environments" in config_data
        assert "default" in config_data["environments"]
