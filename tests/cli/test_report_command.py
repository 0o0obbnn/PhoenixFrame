from click.testing import CliRunner
from unittest.mock import patch
from phoenixframe.cli import main as phoenix_cli_entrypoint

@patch("subprocess.run")
def test_phoenix_report_invokes_allure_serve(mock_subprocess_run):
    """
    Tests if the 'phoenix report' command invokes 'allure serve'.
    """
    runner = CliRunner()
    result = runner.invoke(phoenix_cli_entrypoint, ["report"])
    mock_subprocess_run.assert_called_once_with(["allure", "serve", "allure-results"], check=True)
    assert result.exit_code == 0
