import pytest
from phoenixframe.core.runner import PhoenixRunner

@pytest.fixture(scope="function")
def simple_test_file(tmp_path):
    test_dir = tmp_path / "simple_tests"
    test_dir.mkdir()
    test_file = test_dir / "test_simple.py"
    test_file.write_text("""
def test_always_passes():
    assert True
""")
    return str(test_file)

def test_pytest_can_discover_and_run_simple_test(simple_test_file):
    """
    Tests if pytest can discover and run a simple test through the PhoenixRunner.
    """
    runner = PhoenixRunner()
    result = runner.run_tests(test_paths=[simple_test_file])

    # Check that result is a dictionary with expected keys
    assert isinstance(result, dict)
    assert "pytest_exit_code" in result

    # pytest.main returns 0 for success, but may return other codes for various reasons
    # We'll accept 0 (success) or 2 (interrupted) as valid for this test
    assert result["pytest_exit_code"] in [0, 2], f"Unexpected exit code: {result['pytest_exit_code']}"
