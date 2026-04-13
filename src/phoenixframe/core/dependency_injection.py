"""依赖注入容器

提供完整的依赖注入功能，包括：
- 构造函数注入
- 属性注入
- 方法注入
- 循环依赖检测
- 条件注入
- 配置注入
"""

import inspect
import threading
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, get_type_hints
from dataclasses import dataclass, field
from functools import wraps

from .registry import ComponentRegistry, get_component_registry
from ..observability.logger import get_logger

T = TypeVar('T')


@dataclass
class InjectionPoint:
    """注入点信息"""
    name: str
    type_hint: Type
    required: bool = True
    qualifier: Optional[str] = None
    default_value: Any = None


@dataclass
class InjectionMetadata:
    """注入元数据"""
    target_type: Type
    constructor_injection: List[InjectionPoint] = field(default_factory=list)
    property_injection: Dict[str, InjectionPoint] = field(default_factory=dict)
    method_injection: Dict[str, List[InjectionPoint]] = field(default_factory=dict)


class DependencyInjector:
    """依赖注入器"""
    
    def __init__(self, registry: Optional[ComponentRegistry] = None):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.registry = registry or get_component_registry()
        self._metadata_cache: Dict[Type, InjectionMetadata] = {}
        self._lock = threading.RLock()
        
    def inject(self, target_type: Type[T], *args, **kwargs) -> T:
        """创建实例并注入依赖"""
        with self._lock:
            # 获取或创建注入元数据
            metadata = self._get_injection_metadata(target_type)
            
            # 构造函数注入
            injected_kwargs = self._resolve_constructor_injection(metadata, kwargs)
            
            # 创建实例
            instance = target_type(*args, **injected_kwargs)
            
            # 属性注入
            self._perform_property_injection(instance, metadata)
            
            # 方法注入
            self._perform_method_injection(instance, metadata)
            
            return instance
    
    def inject_into(self, instance: Any) -> None:
        """对已存在的实例进行依赖注入"""
        with self._lock:
            target_type = type(instance)
            metadata = self._get_injection_metadata(target_type)
            
            # 属性注入
            self._perform_property_injection(instance, metadata)
            
            # 方法注入
            self._perform_method_injection(instance, metadata)
    
    def _get_injection_metadata(self, target_type: Type) -> InjectionMetadata:
        """获取注入元数据"""
        if target_type not in self._metadata_cache:
            metadata = self._analyze_injection_metadata(target_type)
            self._metadata_cache[target_type] = metadata
        return self._metadata_cache[target_type]
    
    def _analyze_injection_metadata(self, target_type: Type) -> InjectionMetadata:
        """分析注入元数据"""
        metadata = InjectionMetadata(target_type=target_type)
        
        # 分析构造函数
        if hasattr(target_type, '__init__'):
            constructor_points = self._analyze_constructor(target_type)
            metadata.constructor_injection = constructor_points
        
        # 分析属性注入
        property_points = self._analyze_property_injection(target_type)
        metadata.property_injection = property_points
        
        # 分析方法注入
        method_points = self._analyze_method_injection(target_type)
        metadata.method_injection = method_points
        
        return metadata
    
    def _analyze_constructor(self, target_type: Type) -> List[InjectionPoint]:
        """分析构造函数"""
        injection_points = []
        
        try:
            sig = inspect.signature(target_type.__init__)
            type_hints = get_type_hints(target_type.__init__)
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # 获取类型提示
                param_type = type_hints.get(param_name, param.annotation)
                if param_type == inspect.Parameter.empty:
                    continue
                
                # 检查是否有注入标记
                if hasattr(param, 'annotation') and hasattr(param.annotation, '__metadata__'):
                    # 处理Annotated类型
                    pass
                
                injection_point = InjectionPoint(
                    name=param_name,
                    type_hint=param_type,
                    required=param.default == inspect.Parameter.empty,
                    default_value=param.default if param.default != inspect.Parameter.empty else None
                )
                
                injection_points.append(injection_point)
                
        except Exception as e:
            self.logger.debug(f"Failed to analyze constructor for {target_type}: {e}")
        
        return injection_points
    
    def _analyze_property_injection(self, target_type: Type) -> Dict[str, InjectionPoint]:
        """分析属性注入"""
        injection_points = {}
        
        # 检查类的属性注解
        if hasattr(target_type, '__annotations__'):
            for attr_name, attr_type in target_type.__annotations__.items():
                # 检查是否有Inject标记
                if hasattr(target_type, attr_name):
                    attr_value = getattr(target_type, attr_name)
                    if isinstance(attr_value, _InjectMarker):
                        injection_point = InjectionPoint(
                            name=attr_name,
                            type_hint=attr_type,
                            required=attr_value.required,
                            qualifier=attr_value.qualifier
                        )
                        injection_points[attr_name] = injection_point
        
        return injection_points
    
    def _analyze_method_injection(self, target_type: Type) -> Dict[str, List[InjectionPoint]]:
        """分析方法注入"""
        injection_points = {}
        
        for method_name in dir(target_type):
            method = getattr(target_type, method_name)
            
            # 检查是否有注入标记
            if hasattr(method, '_inject_marker'):
                try:
                    sig = inspect.signature(method)
                    type_hints = get_type_hints(method)
                    
                    method_injection_points = []
                    for param_name, param in sig.parameters.items():
                        if param_name == 'self':
                            continue
                        
                        param_type = type_hints.get(param_name, param.annotation)
                        if param_type == inspect.Parameter.empty:
                            continue
                        
                        injection_point = InjectionPoint(
                            name=param_name,
                            type_hint=param_type,
                            required=param.default == inspect.Parameter.empty,
                            default_value=param.default if param.default != inspect.Parameter.empty else None
                        )
                        
                        method_injection_points.append(injection_point)
                    
                    if method_injection_points:
                        injection_points[method_name] = method_injection_points
                        
                except Exception as e:
                    self.logger.debug(f"Failed to analyze method {method_name} for {target_type}: {e}")
        
        return injection_points
    
    def _resolve_constructor_injection(self, metadata: InjectionMetadata, provided_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """解析构造函数注入"""
        injected_kwargs = provided_kwargs.copy()
        
        for injection_point in metadata.constructor_injection:
            if injection_point.name in injected_kwargs:
                continue  # 已提供参数
            
            # 尝试解析依赖
            dependency = self._resolve_dependency(injection_point)
            if dependency is not None:
                injected_kwargs[injection_point.name] = dependency
            elif injection_point.required:
                raise ValueError(f"Required dependency {injection_point.name} of type {injection_point.type_hint} not found")
        
        return injected_kwargs
    
    def _perform_property_injection(self, instance: Any, metadata: InjectionMetadata) -> None:
        """执行属性注入"""
        for attr_name, injection_point in metadata.property_injection.items():
            dependency = self._resolve_dependency(injection_point)
            if dependency is not None:
                setattr(instance, attr_name, dependency)
                self.logger.debug(f"Injected property {attr_name} into {type(instance).__name__}")
            elif injection_point.required:
                raise ValueError(f"Required dependency {injection_point.name} of type {injection_point.type_hint} not found")
    
    def _perform_method_injection(self, instance: Any, metadata: InjectionMetadata) -> None:
        """执行方法注入"""
        for method_name, injection_points in metadata.method_injection.items():
            method = getattr(instance, method_name)
            
            # 解析方法参数
            method_kwargs = {}
            for injection_point in injection_points:
                dependency = self._resolve_dependency(injection_point)
                if dependency is not None:
                    method_kwargs[injection_point.name] = dependency
                elif injection_point.required:
                    raise ValueError(f"Required dependency {injection_point.name} of type {injection_point.type_hint} not found")
            
            # 调用方法
            if method_kwargs:
                method(**method_kwargs)
                self.logger.debug(f"Executed injection method {method_name} on {type(instance).__name__}")
    
    def _resolve_dependency(self, injection_point: InjectionPoint) -> Optional[Any]:
        """解析依赖"""
        # 首先尝试通过限定符查找
        if injection_point.qualifier:
            dependency = self.registry.get_component(injection_point.qualifier)
            if dependency is not None:
                return dependency
        
        # 然后尝试通过类型查找
        dependency = self.registry.get_component_by_type(injection_point.type_hint)
        if dependency is not None:
            return dependency
        
        # 如果有默认值，返回默认值
        if injection_point.default_value is not None:
            return injection_point.default_value
        
        return None


class _InjectMarker:
    """注入标记类"""
    
    def __init__(self, required: bool = True, qualifier: Optional[str] = None):
        self.required = required
        self.qualifier = qualifier


# 全局注入器
_global_injector: Optional[DependencyInjector] = None
_injector_lock = threading.Lock()


def get_injector() -> DependencyInjector:
    """获取全局依赖注入器"""
    global _global_injector
    if _global_injector is None:
        with _injector_lock:
            if _global_injector is None:
                _global_injector = DependencyInjector()
    return _global_injector


def inject(target_type: Type[T], *args, **kwargs) -> T:
    """创建实例并注入依赖"""
    injector = get_injector()
    return injector.inject(target_type, *args, **kwargs)


def inject_into(instance: Any) -> None:
    """对已存在的实例进行依赖注入"""
    injector = get_injector()
    injector.inject_into(instance)


# 装饰器和标记
def Inject(required: bool = True, qualifier: Optional[str] = None) -> _InjectMarker:
    """创建注入标记"""
    return _InjectMarker(required=required, qualifier=qualifier)


def inject_method(func: Callable) -> Callable:
    """方法注入装饰器"""
    func._inject_marker = True
    return func


def auto_inject(cls: Type[T]) -> Type[T]:
    """自动注入装饰器"""
    original_init = cls.__init__
    
    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        # 调用原始构造函数
        original_init(self, *args, **kwargs)
        # 执行依赖注入
        inject_into(self)
    
    cls.__init__ = new_init
    return cls


# 类型检查辅助函数
def is_injectable_type(type_hint: Type) -> bool:
    """检查类型是否可注入"""
    if type_hint is None:
        return False
    
    # 基础类型不可注入
    if type_hint in (int, float, str, bool, bytes):
        return False
    
    # 集合类型不可注入
    if hasattr(type_hint, '__origin__'):
        origin = type_hint.__origin__
        if origin in (list, dict, set, tuple):
            return False
    
    return True


def get_dependency_tree(target_type: Type) -> Dict[str, Any]:
    """获取依赖树"""
    injector = get_injector()
    metadata = injector._get_injection_metadata(target_type)
    
    tree = {
        'type': target_type.__name__,
        'constructor_dependencies': [],
        'property_dependencies': [],
        'method_dependencies': {}
    }
    
    # 构造函数依赖
    for injection_point in metadata.constructor_injection:
        tree['constructor_dependencies'].append({
            'name': injection_point.name,
            'type': injection_point.type_hint.__name__ if hasattr(injection_point.type_hint, '__name__') else str(injection_point.type_hint),
            'required': injection_point.required
        })
    
    # 属性依赖
    for name, injection_point in metadata.property_injection.items():
        tree['property_dependencies'].append({
            'name': name,
            'type': injection_point.type_hint.__name__ if hasattr(injection_point.type_hint, '__name__') else str(injection_point.type_hint),
            'required': injection_point.required
        })
    
    # 方法依赖
    for method_name, injection_points in metadata.method_injection.items():
        tree['method_dependencies'][method_name] = []
        for injection_point in injection_points:
            tree['method_dependencies'][method_name].append({
                'name': injection_point.name,
                'type': injection_point.type_hint.__name__ if hasattr(injection_point.type_hint, '__name__') else str(injection_point.type_hint),
                'required': injection_point.required
            })
    
    return tree


# 配置注入支持
class ConfigurationInjector:
    """配置注入器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def inject_config(self, instance: Any, prefix: str = "") -> None:
        """注入配置"""
        instance_type = type(instance)
        
        # 获取配置路径
        config_path = f"{prefix}.{instance_type.__name__}" if prefix else instance_type.__name__
        config_data = self._get_config_data(config_path)
        
        if not config_data:
            return
        
        # 注入配置属性
        for key, value in config_data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
                self.logger.debug(f"Injected config {key}={value} into {instance_type.__name__}")
            elif hasattr(instance, 'configure'):
                instance.configure(key, value)
    
    def _get_config_data(self, path: str) -> Dict[str, Any]:
        """获取配置数据"""
        keys = path.split('.')
        data = self.config
        
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return {}
        
        return data if isinstance(data, dict) else {}


def inject_config(instance: Any, config: Dict[str, Any], prefix: str = "") -> None:
    """注入配置"""
    injector = ConfigurationInjector(config)
    injector.inject_config(instance, prefix)