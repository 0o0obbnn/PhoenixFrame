from phoenixframe.core.hooks import register_hook, trigger_hook, HookEvents

def test_lifecycle_hook_triggers_registered_function():
    """
    Tests if the lifecycle hook mechanism can trigger a registered function.
    """
    # A simple flag to check if the hook was called
    called = {"on_test_run_start": False}

    def mock_on_test_run_start_hook():
        called["on_test_run_start"] = True

    # Register the hook
    register_hook(HookEvents.ON_TEST_RUN_START, mock_on_test_run_start_hook)

    # Trigger the hook
    trigger_hook(HookEvents.ON_TEST_RUN_START)

    # Assert that the hook was called
    assert called["on_test_run_start"] is True
