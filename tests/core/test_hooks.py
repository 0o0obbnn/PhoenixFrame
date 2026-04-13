from phoenixframe.core.hooks import HookEvents, register_hook, trigger_hook, clear_hooks, get_registered_hooks

def test_register_and_trigger_hook():
    """Test registering and triggering a hook."""
    callback = Mock()
    event = HookEvents.ON_TEST_RUN_START.value

    register_hook(event, callback)
    trigger_hook(event, param1="value1")

    callback.assert_called_once_with(param1="value1")

def test_trigger_nonexistent_hook():
    """Test triggering a hook that has no registered callbacks."""
    # Should not raise any errors
    trigger_hook("nonexistent_event")

def test_multiple_callbacks_for_event():
    """Test multiple callbacks registered for the same event."""
    callback1 = Mock()
    callback2 = Mock()
    event = HookEvents.ON_TEST_RUN_END.value

    register_hook(event, callback1)
    register_hook(event, callback2)
    trigger_hook(event, exit_code=0)

    callback1.assert_called_once_with(exit_code=0)
    callback2.assert_called_once_with(exit_code=0)

def test_hook_exception_handling(capsys):
    """Test that hook exceptions are caught and logged without interrupting execution."""
    def failing_callback():
        raise ValueError("Intentional error")

    event = HookEvents.ON_TEST_CASE_END.value
    register_hook(event, failing_callback)
    register_hook(event, Mock())  # This should still execute

    trigger_hook(event)

    # Verify error was logged
    captured = capsys.readouterr()
    assert f"Error executing {event} hook: Intentional error" in captured.out

def test_clear_hooks():
    """Test clearing registered hooks."""
    callback = Mock()
    event1 = HookEvents.ON_STEP_START.value
    event2 = HookEvents.ON_STEP_END.value

    register_hook(event1, callback)
    register_hook(event2, callback)

    # Clear specific event
    clear_hooks(event1)
    assert len(get_registered_hooks(event1)[event1]) == 0
    assert len(get_registered_hooks(event2)[event2]) == 1

    # Clear all events
    clear_hooks()
    assert len(get_registered_hooks()) == 0

def test_get_registered_hooks():
    """Test retrieving registered hooks."""
    callback1 = Mock()
    callback2 = Mock()
    event = HookEvents.ON_TEST_CASE_START.value

    register_hook(event, callback1)
    register_hook(event, callback2)

    hooks = get_registered_hooks(event)
    assert len(hooks[event]) == 2
    assert callback1 in hooks[event]
    assert callback2 in hooks[event]

    all_hooks = get_registered_hooks()
    assert event in all_hooks
    assert len(all_hooks[event]) == 2

# Add Mock class since we're not importing unittest.mock in this test file
try:
    from unittest.mock import Mock
except ImportError:
    class Mock:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            pass

        def assert_called_once_with(self, *args, **kwargs):
            pass