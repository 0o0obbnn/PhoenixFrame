"""组件注册中心

提供统一的组件注册、发现和管理功能，包括：
- 组件类型注册
- 实例管理
- 依赖注入
- 生命周期管理
- 配置管理
"""

import inspect
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union

from .lifecycle import LifecycleManager, LifecycleState, global_lifecycle_manager
from ..observability.logger import get_logger

T = TypeVar('T')


class ComponentScope(str):
    """组件作用域"""
    SINGLETON = "singleton"  # 单例
    PROTOTYPE = "prototype"  # 原型（每次创建新实例）
    SESSION = "session"      # 会话作用域
    REQUEST = "request"      # 请求作用域


@dataclass
class ComponentDefinition:
    """组件定义"""
    name: str
    component_type: Type
    factory: Optional[Callable] = None
    scope: ComponentScope = ComponentScope.SINGLETON
    dependencies: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    description: Optional[str] = None
    lazy_init: bool = True
    
    def __post_init__(self):
        if self.factory is None:
            self.factory = self.component_type


@dataclass
class ComponentInstance:
    """组件实例"""
    definition: ComponentDefinition
    instance: Any
    created_at: float = field(default_factory=lambda: __import__('time').time())
    dependencies: Dict[str, Any] = field(default_factory=dict)


class ComponentRegistry:
    """组件注册中心"""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._definitions: Dict[str, ComponentDefinition] = {}
        self._instances: Dict[str, ComponentInstance] = {}
        self._lock = threading.RLock()
        self._aliases: Dict[str, str] = {}
        self._type_mappings: Dict[Type, str] = {}
        
    def register_component(self, 
                          name: str, 
                          component_type: Type, 
                          factory: Optional[Callable] = None,
                          scope: ComponentScope = ComponentScope.SINGLETON,
                          dependencies: Optional[List[str]] = None,
                          configuration: Optional[Dict[str, Any]] = None,
                          tags: Optional[Set[str]] = None,
                          description: Optional[str] = None,
                          lazy_init: bool = True) -> None:
        """注册组件"""
        with self._lock:
            definition = ComponentDefinition(
                name=name,
                component_type=component_type,
                factory=factory,
                scope=scope,
                dependencies=dependencies or [],
                configuration=configuration or {},
                tags=tags or set(),
                description=description,
                lazy_init=lazy_init
            )
            
            self._definitions[name] = definition
            self._type_mappings[component_type] = name
            
            self.logger.debug(f"Registered component: {name} ({component_type.__name__})")
            
            # 如果不是懒加载，立即创建实例
            if not lazy_init and scope == ComponentScope.SINGLETON:
                self._create_instance(name)
    
    def register_alias(self, alias: str, component_name: str) -> None:
        """注册组件别名"""
        with self._lock:
            if component_name not in self._definitions:
                raise ValueError(f"Component {component_name} not found")
            self._aliases[alias] = component_name
            self.logger.debug(f"Registered alias: {alias} -> {component_name}")
    
    def unregister_component(self, name: str) -> None:
        """注销组件"""
        with self._lock:
            if name in self._definitions:
                definition = self._definitions.pop(name)
                
                # 移除类型映射
                if definition.component_type in self._type_mappings:
                    del self._type_mappings[definition.component_type]
                
                # 移除别名
                aliases_to_remove = [alias for alias, comp_name in self._aliases.items() if comp_name == name]
                for alias in aliases_to_remove:
                    del self._aliases[alias]
                
                # 销毁实例
                if name in self._instances:
                    instance = self._instances.pop(name)
                    self._destroy_instance(instance)
                
                self.logger.debug(f"Unregistered component: {name}")
    
    def get_component(self, name: str) -> Optional[Any]:
        """获取组件实例"""
        with self._lock:
            # 处理别名
            actual_name = self._aliases.get(name, name)
            
            if actual_name not in self._definitions:
                return None
            
            definition = self._definitions[actual_name]
            
            # 单例模式
            if definition.scope == ComponentScope.SINGLETON:
                if actual_name not in self._instances:
                    self._create_instance(actual_name)
                return self._instances[actual_name].instance
            
            # 原型模式，每次创建新实例
            elif definition.scope == ComponentScope.PROTOTYPE:
                return self._create_prototype_instance(actual_name)
            
            # 其他作用域暂时按原型处理
            else:
                return self._create_prototype_instance(actual_name)
    
    def get_component_by_type(self, component_type: Type[T]) -> Optional[T]:
        """根据类型获取组件实例"""
        name = self._type_mappings.get(component_type)
        if name:
            return self.get_component(name)
        return None
    
    def get_all_components_by_tag(self, tag: str) -> List[Any]:
        """根据标签获取所有组件实例"""
        components = []
        with self._lock:
            for name, definition in self._definitions.items():
                if tag in definition.tags:
                    component = self.get_component(name)
                    if component:
                        components.append(component)
        return components
    
    def has_component(self, name: str) -> bool:
        """检查是否有指定组件"""
        actual_name = self._aliases.get(name, name)
        return actual_name in self._definitions
    
    def get_component_names(self) -> List[str]:
        """获取所有组件名称"""
        return list(self._definitions.keys())
    
    def get_component_definition(self, name: str) -> Optional[ComponentDefinition]:
        """获取组件定义"""
        actual_name = self._aliases.get(name, name)
        return self._definitions.get(actual_name)
    
    def _create_instance(self, name: str) -> ComponentInstance:
        """创建组件实例"""
        definition = self._definitions[name]
        
        try:
            # 解析依赖
            dependencies = self._resolve_dependencies(definition.dependencies)
            
            # 创建实例
            if definition.factory:
                # 检查工厂函数签名
                sig = inspect.signature(definition.factory)
                if len(sig.parameters) == 0:
                    # 无参数工厂
                    instance = definition.factory()
                else:
                    # 有参数工厂，尝试注入依赖
                    instance = self._invoke_with_dependencies(definition.factory, dependencies)
            else:
                # 直接实例化
                instance = definition.component_type()
            
            # 配置实例
            self._configure_instance(instance, definition.configuration)
            
            # 管理生命周期
            self._manage_lifecycle(instance, name)
            
            component_instance = ComponentInstance(
                definition=definition,
                instance=instance,
                dependencies=dependencies
            )
            
            self._instances[name] = component_instance
            
            self.logger.debug(f"Created instance for component: {name}")
            return component_instance
            
        except Exception as e:
            self.logger.error(f"Failed to create instance for component {name}: {e}")
            raise
    
    def _create_prototype_instance(self, name: str) -> Any:
        """创建原型实例"""
        definition = self._definitions[name]
        
        try:
            # 解析依赖
            dependencies = self._resolve_dependencies(definition.dependencies)
            
            # 创建实例
            if definition.factory:
                sig = inspect.signature(definition.factory)
                if len(sig.parameters) == 0:
                    instance = definition.factory()
                else:
                    instance = self._invoke_with_dependencies(definition.factory, dependencies)
            else:
                instance = definition.component_type()
            
            # 配置实例
            self._configure_instance(instance, definition.configuration)
            
            self.logger.debug(f"Created prototype instance for component: {name}")
            return instance
            
        except Exception as e:
            self.logger.error(f"Failed to create prototype instance for component {name}: {e}")
            raise
    
    def _resolve_dependencies(self, dependency_names: List[str]) -> Dict[str, Any]:
        """解析依赖"""
        dependencies = {}
        for dep_name in dependency_names:
            dep_instance = self.get_component(dep_name)
            if dep_instance is None:
                raise ValueError(f"Dependency {dep_name} not found")
            dependencies[dep_name] = dep_instance
        return dependencies
    
    def _invoke_with_dependencies(self, factory: Callable, dependencies: Dict[str, Any]) -> Any:
        """使用依赖注入调用工厂函数"""
        sig = inspect.signature(factory)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name in dependencies:
                kwargs[param_name] = dependencies[param_name]
            elif param.default != inspect.Parameter.empty:
                # 有默认值的参数可以忽略
                pass
            else:
                # 尝试根据类型匹配
                if param.annotation != inspect.Parameter.empty:
                    dep_instance = self.get_component_by_type(param.annotation)
                    if dep_instance:
                        kwargs[param_name] = dep_instance
        
        return factory(**kwargs)
    
    def _configure_instance(self, instance: Any, configuration: Dict[str, Any]) -> None:
        """配置实例"""
        for key, value in configuration.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
            elif hasattr(instance, 'configure'):
                instance.configure(key, value)
    
    def _manage_lifecycle(self, instance: Any, name: str) -> None:
        """管理生命周期"""
        if isinstance(instance, LifecycleManager):
            global_lifecycle_manager.register_manager(instance)
    
    def _destroy_instance(self, component_instance: ComponentInstance) -> None:
        """销毁实例"""
        instance = component_instance.instance
        
        # 如果实例是生命周期管理器，进行清理
        if isinstance(instance, LifecycleManager):
            if not instance.is_stopped():
                try:
                    instance.dispose()
                except Exception as e:
                    self.logger.error(f"Error disposing lifecycle manager: {e}")
        
        # 如果实例有cleanup方法，调用它
        elif hasattr(instance, 'cleanup'):
            try:
                instance.cleanup()
            except Exception as e:
                self.logger.error(f"Error calling cleanup method: {e}")
        
        # 如果实例有close方法，调用它
        elif hasattr(instance, 'close'):
            try:
                instance.close()
            except Exception as e:
                self.logger.error(f"Error calling close method: {e}")
    
    def shutdown(self) -> None:
        """关闭注册中心"""
        with self._lock:
            # 按依赖顺序反向销毁实例
            for name, instance in list(self._instances.items()):
                try:
                    self._destroy_instance(instance)
                except Exception as e:
                    self.logger.error(f"Error destroying instance {name}: {e}")
            
            self._instances.clear()
            self._definitions.clear()
            self._aliases.clear()
            self._type_mappings.clear()
            
            self.logger.info("Component registry shut down")


class ComponentRegistryManager:
    """组件注册中心管理器"""
    
    _instance: Optional['ComponentRegistryManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
            self._registries: Dict[str, ComponentRegistry] = {}
            self._registries_lock = threading.RLock()
            
            # 创建默认注册中心
            self._default_registry = ComponentRegistry()
            self._registries['default'] = self._default_registry
    
    def get_registry(self, name: str = 'default') -> ComponentRegistry:
        """获取注册中心"""
        with self._registries_lock:
            if name not in self._registries:
                self._registries[name] = ComponentRegistry()
            return self._registries[name]
    
    def create_registry(self, name: str) -> ComponentRegistry:
        """创建新的注册中心"""
        with self._registries_lock:
            if name in self._registries:
                raise ValueError(f"Registry {name} already exists")
            
            registry = ComponentRegistry()
            self._registries[name] = registry
            return registry
    
    def remove_registry(self, name: str) -> None:
        """移除注册中心"""
        if name == 'default':
            raise ValueError("Cannot remove default registry")
        
        with self._registries_lock:
            if name in self._registries:
                registry = self._registries.pop(name)
                registry.shutdown()
    
    def get_default_registry(self) -> ComponentRegistry:
        """获取默认注册中心"""
        return self._default_registry
    
    def shutdown_all(self) -> None:
        """关闭所有注册中心"""
        with self._registries_lock:
            for name, registry in list(self._registries.items()):
                try:
                    registry.shutdown()
                except Exception as e:
                    self.logger.error(f"Error shutting down registry {name}: {e}")
            self._registries.clear()
            self.logger.info("All component registries shut down")


# 全局组件注册中心管理器
registry_manager = ComponentRegistryManager()


def get_component_registry(name: str = 'default') -> ComponentRegistry:
    """获取组件注册中心"""
    return registry_manager.get_registry(name)


def register_component(name: str, 
                      component_type: Type, 
                      factory: Optional[Callable] = None,
                      scope: ComponentScope = ComponentScope.SINGLETON,
                      dependencies: Optional[List[str]] = None,
                      configuration: Optional[Dict[str, Any]] = None,
                      tags: Optional[Set[str]] = None,
                      description: Optional[str] = None,
                      lazy_init: bool = True,
                      registry_name: str = 'default') -> None:
    """注册组件到默认注册中心"""
    registry = get_component_registry(registry_name)
    registry.register_component(
        name=name,
        component_type=component_type,
        factory=factory,
        scope=scope,
        dependencies=dependencies,
        configuration=configuration,
        tags=tags,
        description=description,
        lazy_init=lazy_init
    )


def get_component(name: str, registry_name: str = 'default') -> Optional[Any]:
    """从默认注册中心获取组件"""
    registry = get_component_registry(registry_name)
    return registry.get_component(name)


def get_component_by_type(component_type: Type[T], registry_name: str = 'default') -> Optional[T]:
    """从默认注册中心根据类型获取组件"""
    registry = get_component_registry(registry_name)
    return registry.get_component_by_type(component_type)


# 装饰器支持
def component(name: Optional[str] = None, 
             scope: ComponentScope = ComponentScope.SINGLETON,
             dependencies: Optional[List[str]] = None,
             configuration: Optional[Dict[str, Any]] = None,
             tags: Optional[Set[str]] = None,
             description: Optional[str] = None,
             lazy_init: bool = True,
             registry_name: str = 'default'):
    """组件装饰器"""
    def decorator(cls):
        component_name = name or cls.__name__
        register_component(
            name=component_name,
            component_type=cls,
            scope=scope,
            dependencies=dependencies,
            configuration=configuration,
            tags=tags,
            description=description,
            lazy_init=lazy_init,
            registry_name=registry_name
        )
        return cls
    return decorator


def factory(component_name: str,
           scope: ComponentScope = ComponentScope.SINGLETON,
           dependencies: Optional[List[str]] = None,
           configuration: Optional[Dict[str, Any]] = None,
           tags: Optional[Set[str]] = None,
           description: Optional[str] = None,
           lazy_init: bool = True,
           registry_name: str = 'default'):
    """工厂函数装饰器"""
    def decorator(func):
        # 根据函数返回类型推断组件类型
        sig = inspect.signature(func)
        return_type = sig.return_annotation
        if return_type == inspect.Signature.empty:
            return_type = type(func())  # 尝试调用获取类型
        
        register_component(
            name=component_name,
            component_type=return_type,
            factory=func,
            scope=scope,
            dependencies=dependencies,
            configuration=configuration,
            tags=tags,
            description=description,
            lazy_init=lazy_init,
            registry_name=registry_name
        )
        return func
    return decorator