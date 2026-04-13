from typing import Dict, Callable, List, Any
from enum import Enum

class HookEvents(Enum):
    """Enumeration of all available hook events in PhoenixFrame."""
    ON_TEST_RUN_START = "on_test_run_start"
    ON_TEST_RUN_END = "on_test_run_end"
    ON_TEST_CASE_START = "on_test_case_start"
    ON_TEST_CASE_END = "on_test_case_end"
    ON_STEP_START = "on_step_start"
    ON_STEP_END = "on_step_end"

# Global hook registry: {event_name: [callbacks]}
_hook_registry: Dict[str, List[Callable]] = {}


def register_hook(event: str, callback: Callable) -> None:
    """
    Register a callback function for a specific hook event.
    
    Args:
        event: Name of the event to register for
        callback: Function to be called when the event is triggered
    """
    if event not in _hook_registry:
        _hook_registry[event] = []
    _hook_registry[event].append(callback)


def trigger_hook(event: str, **kwargs: Any) -> None:
    """
    Trigger all registered callbacks for a specific hook event.
    
    Args:
        event: Name of the event to trigger
        **kwargs: Keyword arguments to pass to the callback functions
    """
    if event in _hook_registry:
        for callback in _hook_registry[event]:
            try:
                callback(** kwargs)
            except Exception as e:
                # Log hook execution errors but don't interrupt the main flow
                print(f"Error executing {event} hook: {e}")


def clear_hooks(event: str = None) -> None:
    """
    Clear registered hooks for a specific event or all events.
    
    Args:
        event: If provided, only clear hooks for this event; otherwise clear all
    """
    if event:
        if event in _hook_registry:
            del _hook_registry[event]
    else:
        _hook_registry.clear()


def get_registered_hooks(event: str = None) -> Dict[str, List[Callable]]:
    """
    Get registered hooks for debugging purposes.
    
    Args:
        event: If provided, only return hooks for this event
    
    Returns:
        Dictionary of event names to list of callbacks
    """
    if event:
        return {event: _hook_registry.get(event, [])}
    return _hook_registry.copy()
