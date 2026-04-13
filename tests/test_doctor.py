from click.testing import CliRunner
from phoenixframe.cli import main

def test_doctor_command():
    """Tests that the doctor command runs without errors."""
    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 0
    assert "Running PhoenixFrame doctor..." in result.output
    assert "All checks passed." in result.output
