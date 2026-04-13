"""核心架构模块

提供PhoenixFrame的核心架构组件：
- 生命周期管理
- 组件注册和依赖注入
- 插件系统
- 配置管理
- 并行执行系统
"""

from .lifecycle import (
    LifecycleState, LifecycleEvent, LifecycleEventData, LifecycleListener,
    LifecycleManager, TestSessionManager, GlobalLifecycleManager,
    global_lifecycle_manager, create_test_session, get_test_session,
    cleanup_test_session, test_session_context
)

from .registry import (
    ComponentScope, ComponentDefinition, ComponentInstance, ComponentRegistry,
    ComponentRegistryManager, registry_manager, get_component_registry,
    register_component, get_component, get_component_by_type, component, factory
)

from .dependency_injection import (
    InjectionPoint, InjectionMetadata, DependencyInjector, 
    get_injector, inject, inject_into, Inject, inject_method, auto_inject,
    is_injectable_type, get_dependency_tree, ConfigurationInjector, inject_config
)

from .plugin_manager import (
    PluginMetadata, PluginInterface, PluginContext, PluginInfo, PluginEvent,
    PluginManager, get_plugin_manager, load_plugins, get_plugin, plugin
)

from .config import (
    ConfigFormat, ConfigSource, ConfigMetadata, ConfigProvider,
    FileConfigProvider, EnvironmentConfigProvider,
    EnvironmentConfig, ReportingConfig, WebDriverConfig, LoggingConfig,
    DatabaseConfig, TestingConfig, SecurityConfig, PerformanceConfig,
    ObservabilityConfig, ConfigModel, PhoenixConfig,
    load_config, get_config, set_config, get_config_value, set_config_value
)

from .parallel_executor import (
    ExecutionStrategy, TaskPriority, TaskStatus, TaskResult, ExecutionTask,
    ExecutionConfig, ExecutionMonitor, BaseParallelExecutor,
    ThreadPoolExecutor_Custom, ProcessPoolExecutor_Custom, AdaptiveParallelExecutor,
    ParallelExecutorFactory, execute_tasks_parallel, create_task
)

# 可选导入测试执行器（可能依赖web模块）
try:
    from .test_executor import (
        TestCase, TestSuite, TestResourceManager, TestExecutor, TestDiscovery,
        create_test_executor, run_test_suite, discover_and_run_tests
    )
    TEST_EXECUTOR_AVAILABLE = True
except ImportError:
    TEST_EXECUTOR_AVAILABLE = False
    # 创建占位符
    TestCase = TestSuite = TestResourceManager = TestExecutor = TestDiscovery = None
    create_test_executor = run_test_suite = discover_and_run_tests = None

__all__ = [
    # 生命周期管理
    'LifecycleState', 'LifecycleEvent', 'LifecycleEventData', 'LifecycleListener',
    'LifecycleManager', 'TestSessionManager', 'GlobalLifecycleManager',
    'global_lifecycle_manager', 'create_test_session', 'get_test_session',
    'cleanup_test_session', 'test_session_context',
    
    # 组件注册
    'ComponentScope', 'ComponentDefinition', 'ComponentInstance', 'ComponentRegistry',
    'ComponentRegistryManager', 'registry_manager', 'get_component_registry',
    'register_component', 'get_component', 'get_component_by_type', 'component', 'factory',
    
    # 依赖注入
    'InjectionPoint', 'InjectionMetadata', 'DependencyInjector',
    'get_injector', 'inject', 'inject_into', 'Inject', 'inject_method', 'auto_inject',
    'is_injectable_type', 'get_dependency_tree', 'ConfigurationInjector', 'inject_config',
    
    # 插件系统
    'PluginMetadata', 'PluginInterface', 'PluginContext', 'PluginInfo', 'PluginEvent',
    'PluginManager', 'get_plugin_manager', 'load_plugins', 'get_plugin', 'plugin',
    
    # 配置管理
    'ConfigFormat', 'ConfigSource', 'ConfigMetadata', 'ConfigProvider',
    'FileConfigProvider', 'EnvironmentConfigProvider',
    'EnvironmentConfig', 'ReportingConfig', 'WebDriverConfig', 'LoggingConfig',
    'DatabaseConfig', 'TestingConfig', 'SecurityConfig', 'PerformanceConfig',
    'ObservabilityConfig', 'ConfigModel', 'PhoenixConfig',
    'load_config', 'get_config', 'set_config', 'get_config_value', 'set_config_value',
    
    # 并行执行系统
    'ExecutionStrategy', 'TaskPriority', 'TaskStatus', 'TaskResult', 'ExecutionTask',
    'ExecutionConfig', 'ExecutionMonitor', 'BaseParallelExecutor',
    'ThreadPoolExecutor_Custom', 'ProcessPoolExecutor_Custom', 'AdaptiveParallelExecutor',
    'ParallelExecutorFactory', 'execute_tasks_parallel', 'create_task',
    
    # 可用性标志
    'TEST_EXECUTOR_AVAILABLE',
]

# 只有在可用时才添加测试执行器到__all__
if TEST_EXECUTOR_AVAILABLE:
    __all__.extend([
        'TestCase', 'TestSuite', 'TestResourceManager', 'TestExecutor', 'TestDiscovery',
        'create_test_executor', 'run_test_suite', 'discover_and_run_tests'
    ])