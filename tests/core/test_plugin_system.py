import pytest
import sys
from phoenixframe.core.plugin_manager import PluginManager

@pytest.fixture(scope="function")
def simple_plugin_file(tmp_path):
    """Creates a simple plugin file for testing."""
    plugin_dir = tmp_path / "my_simple_plugin"
    plugin_dir.mkdir()
    plugin_file = plugin_dir / "__init__.py"
    plugin_file.write_text("""
class MySimplePluginPlugin:
    def __init__(self):
        self.loaded = True
""")
    sys.path.insert(0, str(tmp_path))
    yield
    sys.path.pop(0)

def test_plugin_manager_loads_simple_plugin(simple_plugin_file):
    """
    Tests if the PluginManager can load a simple plugin.
    """
    manager = PluginManager()
    manager.load_plugin("my_simple_plugin")
    assert manager.is_plugin_loaded("my_simple_plugin")
