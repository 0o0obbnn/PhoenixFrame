from phoenixframe.core.runner import PhoenixRunner

def mock_test_function():
    assert True

def test_phoenix_runner_executes_simple_test():
    """
    Tests if the PhoenixRunner can execute a simple test function.
    """
    runner = PhoenixRunner()
    result = runner.run_tests(test_functions=[mock_test_function])
    assert result["passed_count"] == 1
