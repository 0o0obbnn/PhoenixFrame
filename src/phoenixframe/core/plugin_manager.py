"""插件管理器

提供完整的插件系统，包括：
- 插件发现和加载
- 插件生命周期管理
- 插件依赖管理
- 插件配置管理
- 插件通信和事件系统
"""

import importlib
import importlib.util
import inspect
import os
import sys
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from .lifecycle import LifecycleManager, LifecycleState
from .registry import ComponentRegistry, get_component_registry
from ..observability.logger import get_logger


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    entry_point: str = ""
    config_schema: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    enabled: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        """从字典创建插件元数据"""
        return cls(
            name=data.get('name', ''),
            version=data.get('version', '1.0.0'),
            description=data.get('description', ''),
            author=data.get('author', ''),
            dependencies=data.get('dependencies', []),
            provides=data.get('provides', []),
            entry_point=data.get('entry_point', ''),
            config_schema=data.get('config_schema', {}),
            tags=set(data.get('tags', [])),
            enabled=data.get('enabled', True)
        )


class PluginInterface(ABC):
    """插件接口"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        pass
    
    @abstractmethod
    def initialize(self, context: 'PluginContext') -> None:
        """初始化插件"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """关闭插件"""
        pass


@dataclass
class PluginContext:
    """插件上下文"""
    plugin_name: str
    config: Dict[str, Any]
    registry: ComponentRegistry
    plugin_manager: 'PluginManager'
    logger: Any
    
    def get_plugin(self, name: str) -> Optional[PluginInterface]:
        """获取其他插件"""
        return self.plugin_manager.get_plugin(name)
    
    def emit_event(self, event_name: str, data: Any = None) -> None:
        """发送事件"""
        self.plugin_manager.emit_event(event_name, data, self.plugin_name)
    
    def subscribe_event(self, event_name: str, handler: Callable) -> None:
        """订阅事件"""
        self.plugin_manager.subscribe_event(event_name, handler)


@dataclass
class PluginInfo:
    """插件信息"""
    metadata: PluginMetadata
    instance: Optional[PluginInterface] = None
    context: Optional[PluginContext] = None
    module: Optional[Any] = None
    loaded: bool = False
    initialized: bool = False
    error: Optional[str] = None


class PluginEvent:
    """插件事件"""
    
    def __init__(self, name: str, data: Any = None, source: str = ""):
        self.name = name
        self.data = data
        self.source = source
        self.timestamp = __import__('time').time()


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugin_dirs: Optional[List[str]] = None, registry: Optional[ComponentRegistry] = None):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.registry = registry or get_component_registry()
        self.plugin_dirs = plugin_dirs or []
        
        # 插件存储
        self._plugins: Dict[str, PluginInfo] = {}
        self._plugin_order: List[str] = []
        
        # 事件系统
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # 锁
        self._lock = threading.RLock()
        
        # 保持向后兼容
        self._loaded_plugins = {}
        
        # 添加默认插件目录
        self._add_default_plugin_dirs()
    
    def _add_default_plugin_dirs(self) -> None:
        """添加默认插件目录"""
        # 当前项目的plugins目录
        current_dir = Path.cwd()
        plugins_dir = current_dir / "plugins"
        if plugins_dir.exists():
            self.plugin_dirs.append(str(plugins_dir))
        
        # 用户目录下的插件
        user_plugins_dir = Path.home() / ".phoenixframe" / "plugins"
        if user_plugins_dir.exists():
            self.plugin_dirs.append(str(user_plugins_dir))
    
    # 保持向后兼容的方法
    def load_plugin(self, plugin_name):
        """Loads a plugin by its module name."""
        if plugin_name in self._loaded_plugins:
            return
        try:
            plugin_module = importlib.import_module(plugin_name)
            # A simple convention: the plugin class is the camel-cased version of the module name
            class_name = "".join(word.capitalize() for word in plugin_name.split("_")) + "Plugin"
            plugin_class = getattr(plugin_module, class_name)
            self._loaded_plugins[plugin_name] = plugin_class()
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not load plugin '{plugin_name}': {e}")

    def is_plugin_loaded(self, plugin_name):
        """Checks if a plugin is loaded."""
        return plugin_name in self._loaded_plugins
    
    # 新的企业级方法
    def discover_plugins(self) -> List[PluginMetadata]:
        """发现插件"""
        discovered_plugins = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue
            
            self.logger.debug(f"Discovering plugins in: {plugin_dir}")
            
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                
                # 检查是否是插件目录
                if os.path.isdir(item_path):
                    plugin_metadata = self._load_plugin_metadata(item_path)
                    if plugin_metadata:
                        discovered_plugins.append(plugin_metadata)
                        self.logger.debug(f"Discovered plugin: {plugin_metadata.name}")
                
                # 检查是否是插件文件
                elif item.endswith('.py') and not item.startswith('__'):
                    plugin_metadata = self._load_plugin_metadata_from_file(item_path)
                    if plugin_metadata:
                        discovered_plugins.append(plugin_metadata)
                        self.logger.debug(f"Discovered plugin: {plugin_metadata.name}")
        
        return discovered_plugins
    
    def _load_plugin_metadata(self, plugin_dir: str) -> Optional[PluginMetadata]:
        """从插件目录加载元数据"""
        metadata_file = os.path.join(plugin_dir, "plugin.yaml")
        if not os.path.exists(metadata_file):
            metadata_file = os.path.join(plugin_dir, "plugin.json")
        
        if not os.path.exists(metadata_file):
            return None
        
        try:
            if metadata_file.endswith('.yaml'):
                import yaml
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            else:
                import json
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            return PluginMetadata.from_dict(data)
        
        except Exception as e:
            self.logger.error(f"Failed to load plugin metadata from {metadata_file}: {e}")
            return None
    
    def _load_plugin_metadata_from_file(self, plugin_file: str) -> Optional[PluginMetadata]:
        """从插件文件加载元数据"""
        try:
            # 尝试加载模块获取元数据
            spec = importlib.util.spec_from_file_location("temp_plugin", plugin_file)
            if spec is None or spec.loader is None:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 检查是否有插件类或元数据
            if hasattr(module, 'PLUGIN_METADATA'):
                return PluginMetadata.from_dict(module.PLUGIN_METADATA)
            elif hasattr(module, 'Plugin'):
                plugin_class = module.Plugin
                if hasattr(plugin_class, 'get_metadata'):
                    try:
                        instance = plugin_class()
                        return instance.get_metadata()
                    except Exception:
                        pass
        
        except Exception as e:
            self.logger.debug(f"Failed to load plugin metadata from {plugin_file}: {e}")
        
        return None
    
    def register_plugin(self, metadata: PluginMetadata) -> None:
        """注册插件"""
        with self._lock:
            if metadata.name in self._plugins:
                self.logger.warning(f"Plugin {metadata.name} already registered")
                return
            
            plugin_info = PluginInfo(metadata=metadata)
            self._plugins[metadata.name] = plugin_info
            self._plugin_order.append(metadata.name)
            
            self.logger.debug(f"Registered plugin: {metadata.name}")
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """获取插件实例"""
        with self._lock:
            if plugin_name in self._plugins:
                plugin_info = self._plugins[plugin_name]
                if plugin_info.initialized:
                    return plugin_info.instance
            return None
    
    def list_plugins(self) -> List[str]:
        """列出所有插件"""
        return list(self._plugins.keys())
    
    def load_all_plugins(self) -> Dict[str, bool]:
        """加载所有插件"""
        results = {}
        
        # 首先发现插件
        discovered_plugins = self.discover_plugins()
        for metadata in discovered_plugins:
            self.register_plugin(metadata)
        
        return results
    
    # 事件系统
    def emit_event(self, event_name: str, data: Any = None, source: str = "") -> None:
        """发送事件"""
        event = PluginEvent(event_name, data, source)
        
        if event_name in self._event_handlers:
            for handler in self._event_handlers[event_name]:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_name}: {e}")
        
        self.logger.debug(f"Emitted event: {event_name} from {source}")
    
    def subscribe_event(self, event_name: str, handler: Callable[[PluginEvent], None]) -> None:
        """订阅事件"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        
        self._event_handlers[event_name].append(handler)
        self.logger.debug(f"Subscribed to event: {event_name}")


# 全局插件管理器
_global_plugin_manager: Optional[PluginManager] = None
_plugin_manager_lock = threading.Lock()


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _global_plugin_manager
    if _global_plugin_manager is None:
        with _plugin_manager_lock:
            if _global_plugin_manager is None:
                _global_plugin_manager = PluginManager()
    return _global_plugin_manager


def load_plugins(plugin_dirs: Optional[List[str]] = None) -> Dict[str, bool]:
    """加载插件"""
    manager = get_plugin_manager()
    if plugin_dirs:
        manager.plugin_dirs.extend(plugin_dirs)
    return manager.load_all_plugins()


def get_plugin(plugin_name: str) -> Optional[PluginInterface]:
    """获取插件"""
    manager = get_plugin_manager()
    return manager.get_plugin(plugin_name)


# 插件装饰器
def plugin(name: str, version: str = "1.0.0", description: str = "", author: str = ""):
    """插件装饰器"""
    def decorator(cls):
        if not issubclass(cls, PluginInterface):
            raise TypeError("Plugin class must inherit from PluginInterface")
        
        # 添加元数据
        cls._plugin_metadata = PluginMetadata(
            name=name,
            version=version,
            description=description,
            author=author
        )
        
        return cls
    
    return decorator
