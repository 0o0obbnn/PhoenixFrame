"""测试生命周期管理器

提供完整的测试生命周期管理功能，包括：
- 测试会话管理
- 资源分配和清理
- 生命周期事件钩子
- 状态跟踪和监控
"""

import asyncio
import threading
import weakref
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from ..observability.logger import get_logger
from ..observability.tracer import get_tracer


class LifecycleState(Enum):
    """生命周期状态枚举"""
    CREATED = "created"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    DISPOSING = "disposing"
    DISPOSED = "disposed"
    ERROR = "error"


class LifecycleEvent(Enum):
    """生命周期事件枚举"""
    BEFORE_INIT = "before_init"
    AFTER_INIT = "after_init"
    BEFORE_START = "before_start"
    AFTER_START = "after_start"
    BEFORE_STOP = "before_stop"
    AFTER_STOP = "after_stop"
    BEFORE_DISPOSE = "before_dispose"
    AFTER_DISPOSE = "after_dispose"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class LifecycleEventData:
    """生命周期事件数据"""
    event: LifecycleEvent
    source: 'LifecycleManager'
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


class LifecycleListener(ABC):
    """生命周期监听器接口"""
    
    @abstractmethod
    def on_lifecycle_event(self, event_data: LifecycleEventData) -> None:
        """处理生命周期事件"""
        pass


class LifecycleManager:
    """生命周期管理器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.state = LifecycleState.CREATED
        self.created_at = datetime.now()
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.tracer = get_tracer(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # 事件监听器
        self._listeners: Set[LifecycleListener] = set()
        
        # 状态变更历史
        self._state_history: List[tuple] = [(LifecycleState.CREATED, datetime.now())]
        
        # 锁保护状态变更
        self._lock = threading.RLock()
        
        # 错误信息
        self._error: Optional[Exception] = None
        
        # 资源管理
        self._resources: Dict[str, Any] = {}
        self._cleanup_handlers: List[Callable] = []
    
    def add_listener(self, listener: LifecycleListener) -> None:
        """添加生命周期监听器"""
        with self._lock:
            self._listeners.add(listener)
            self.logger.debug(f"Added lifecycle listener: {listener.__class__.__name__}")
    
    def remove_listener(self, listener: LifecycleListener) -> None:
        """移除生命周期监听器"""
        with self._lock:
            self._listeners.discard(listener)
            self.logger.debug(f"Removed lifecycle listener: {listener.__class__.__name__}")
    
    def _emit_event(self, event: LifecycleEvent, data: Optional[Dict[str, Any]] = None) -> None:
        """发送生命周期事件"""
        event_data = LifecycleEventData(
            event=event,
            source=self,
            data=data or {}
        )
        
        # 记录事件
        self.logger.info(f"Lifecycle event: {event.value} for {self.name}")
        
        # 通知监听器
        for listener in self._listeners:
            try:
                listener.on_lifecycle_event(event_data)
            except Exception as e:
                self.logger.error(f"Error in lifecycle listener {listener.__class__.__name__}: {e}")
    
    def _transition_to(self, new_state: LifecycleState, error: Optional[Exception] = None) -> None:
        """状态转换"""
        with self._lock:
            old_state = self.state
            self.state = new_state
            self._state_history.append((new_state, datetime.now()))
            
            if error:
                self._error = error
                self.state = LifecycleState.ERROR
                self._state_history.append((LifecycleState.ERROR, datetime.now()))
            
            self.logger.info(f"State transition: {old_state.value} -> {new_state.value} for {self.name}")
    
    def get_state(self) -> LifecycleState:
        """获取当前状态"""
        return self.state
    
    def get_error(self) -> Optional[Exception]:
        """获取错误信息"""
        return self._error
    
    def get_state_history(self) -> List[tuple]:
        """获取状态变更历史"""
        return self._state_history.copy()
    
    def is_running(self) -> bool:
        """检查是否在运行状态"""
        return self.state == LifecycleState.RUNNING
    
    def is_stopped(self) -> bool:
        """检查是否已停止"""
        return self.state in (LifecycleState.STOPPED, LifecycleState.DISPOSED)
    
    def is_error(self) -> bool:
        """检查是否有错误"""
        return self.state == LifecycleState.ERROR
    
    def add_resource(self, name: str, resource: Any) -> None:
        """添加需要管理的资源"""
        with self._lock:
            self._resources[name] = resource
            self.logger.debug(f"Added resource: {name}")
    
    def get_resource(self, name: str) -> Optional[Any]:
        """获取资源"""
        return self._resources.get(name)
    
    def add_cleanup_handler(self, handler: Callable) -> None:
        """添加清理处理器"""
        with self._lock:
            self._cleanup_handlers.append(handler)
            self.logger.debug(f"Added cleanup handler: {handler.__name__}")
    
    def initialize(self) -> None:
        """初始化"""
        with self._lock:
            if self.state != LifecycleState.CREATED:
                raise RuntimeError(f"Cannot initialize from state {self.state.value}")
            
            try:
                with self.tracer.trace_lifecycle_operation("initialize"):
                    self._transition_to(LifecycleState.INITIALIZING)
                    self._emit_event(LifecycleEvent.BEFORE_INIT)
                    
                    self._do_initialize()
                    
                    self._transition_to(LifecycleState.INITIALIZED)
                    self._emit_event(LifecycleEvent.AFTER_INIT)
                    
            except Exception as e:
                self._transition_to(LifecycleState.ERROR, e)
                self._emit_event(LifecycleEvent.ERROR_OCCURRED, {"error": str(e)})
                raise
    
    def start(self) -> None:
        """启动"""
        with self._lock:
            if self.state not in (LifecycleState.INITIALIZED, LifecycleState.STOPPED):
                raise RuntimeError(f"Cannot start from state {self.state.value}")
            
            try:
                with self.tracer.trace_lifecycle_operation("start"):
                    self._transition_to(LifecycleState.STARTING)
                    self._emit_event(LifecycleEvent.BEFORE_START)
                    
                    self._do_start()
                    
                    self._transition_to(LifecycleState.RUNNING)
                    self._emit_event(LifecycleEvent.AFTER_START)
                    
            except Exception as e:
                self._transition_to(LifecycleState.ERROR, e)
                self._emit_event(LifecycleEvent.ERROR_OCCURRED, {"error": str(e)})
                raise
    
    def stop(self) -> None:
        """停止"""
        with self._lock:
            if self.state not in (LifecycleState.RUNNING, LifecycleState.STARTING):
                return  # 已经停止或未启动
            
            try:
                with self.tracer.trace_lifecycle_operation("stop"):
                    self._transition_to(LifecycleState.STOPPING)
                    self._emit_event(LifecycleEvent.BEFORE_STOP)
                    
                    self._do_stop()
                    
                    self._transition_to(LifecycleState.STOPPED)
                    self._emit_event(LifecycleEvent.AFTER_STOP)
                    
            except Exception as e:
                self._transition_to(LifecycleState.ERROR, e)
                self._emit_event(LifecycleEvent.ERROR_OCCURRED, {"error": str(e)})
                raise
    
    def dispose(self) -> None:
        """销毁"""
        with self._lock:
            if self.state == LifecycleState.DISPOSED:
                return  # 已经销毁
            
            try:
                with self.tracer.trace_lifecycle_operation("dispose"):
                    # 先停止（如果正在运行）
                    if self.state == LifecycleState.RUNNING:
                        self.stop()
                    
                    self._transition_to(LifecycleState.DISPOSING)
                    self._emit_event(LifecycleEvent.BEFORE_DISPOSE)
                    
                    # 执行清理
                    self._do_dispose()
                    self._cleanup_resources()
                    
                    self._transition_to(LifecycleState.DISPOSED)
                    self._emit_event(LifecycleEvent.AFTER_DISPOSE)
                    
            except Exception as e:
                self._transition_to(LifecycleState.ERROR, e)
                self._emit_event(LifecycleEvent.ERROR_OCCURRED, {"error": str(e)})
                raise
    
    def _cleanup_resources(self) -> None:
        """清理资源"""
        # 执行清理处理器
        for handler in reversed(self._cleanup_handlers):
            try:
                handler()
            except Exception as e:
                self.logger.error(f"Error in cleanup handler {handler.__name__}: {e}")
        
        # 清理资源
        for name, resource in self._resources.items():
            try:
                if hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, 'dispose'):
                    resource.dispose()
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up resource {name}: {e}")
        
        self._resources.clear()
        self._cleanup_handlers.clear()
    
    def _do_initialize(self) -> None:
        """子类实现具体的初始化逻辑"""
        pass
    
    def _do_start(self) -> None:
        """子类实现具体的启动逻辑"""
        pass
    
    def _do_stop(self) -> None:
        """子类实现具体的停止逻辑"""
        pass
    
    def _do_dispose(self) -> None:
        """子类实现具体的销毁逻辑"""
        pass
    
    @contextmanager
    def lifecycle_context(self):
        """生命周期上下文管理器"""
        try:
            if self.state == LifecycleState.CREATED:
                self.initialize()
            if self.state == LifecycleState.INITIALIZED:
                self.start()
            yield self
        finally:
            try:
                if self.state == LifecycleState.RUNNING:
                    self.stop()
            finally:
                if self.state != LifecycleState.DISPOSED:
                    self.dispose()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self.lifecycle_context().__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        return self.lifecycle_context().__exit__(exc_type, exc_val, exc_tb)


class TestSessionManager(LifecycleManager):
    """测试会话管理器"""
    
    def __init__(self, session_id: str):
        super().__init__(f"TestSession-{session_id}")
        self.session_id = session_id
        self.test_cases: Dict[str, Any] = {}
        self.test_results: Dict[str, Any] = {}
        self.shared_data: Dict[str, Any] = {}
        
    def add_test_case(self, test_id: str, test_case: Any) -> None:
        """添加测试用例"""
        self.test_cases[test_id] = test_case
        self.logger.debug(f"Added test case: {test_id}")
    
    def get_test_case(self, test_id: str) -> Optional[Any]:
        """获取测试用例"""
        return self.test_cases.get(test_id)
    
    def set_test_result(self, test_id: str, result: Any) -> None:
        """设置测试结果"""
        self.test_results[test_id] = result
        self.logger.debug(f"Set test result for: {test_id}")
    
    def get_test_result(self, test_id: str) -> Optional[Any]:
        """获取测试结果"""
        return self.test_results.get(test_id)
    
    def set_shared_data(self, key: str, value: Any) -> None:
        """设置共享数据"""
        self.shared_data[key] = value
    
    def get_shared_data(self, key: str) -> Optional[Any]:
        """获取共享数据"""
        return self.shared_data.get(key)
    
    def _do_initialize(self) -> None:
        """初始化测试会话"""
        self.logger.info(f"Initializing test session: {self.session_id}")
        # 这里可以添加会话初始化逻辑
    
    def _do_start(self) -> None:
        """启动测试会话"""
        self.logger.info(f"Starting test session: {self.session_id}")
        # 这里可以添加会话启动逻辑
    
    def _do_stop(self) -> None:
        """停止测试会话"""
        self.logger.info(f"Stopping test session: {self.session_id}")
        # 这里可以添加会话停止逻辑
    
    def _do_dispose(self) -> None:
        """销毁测试会话"""
        self.logger.info(f"Disposing test session: {self.session_id}")
        self.test_cases.clear()
        self.test_results.clear()
        self.shared_data.clear()


class GlobalLifecycleManager:
    """全局生命周期管理器"""
    
    _instance: Optional['GlobalLifecycleManager'] = None
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
            self._managers: Dict[str, LifecycleManager] = {}
            self._managers_lock = threading.RLock()
    
    def register_manager(self, manager: LifecycleManager) -> None:
        """注册生命周期管理器"""
        with self._managers_lock:
            self._managers[manager.name] = manager
            self.logger.debug(f"Registered lifecycle manager: {manager.name}")
    
    def unregister_manager(self, name: str) -> None:
        """注销生命周期管理器"""
        with self._managers_lock:
            if name in self._managers:
                manager = self._managers.pop(name)
                # 确保管理器被正确清理
                if not manager.is_stopped():
                    try:
                        manager.dispose()
                    except Exception as e:
                        self.logger.error(f"Error disposing manager {name}: {e}")
                self.logger.debug(f"Unregistered lifecycle manager: {name}")
    
    def get_manager(self, name: str) -> Optional[LifecycleManager]:
        """获取生命周期管理器"""
        return self._managers.get(name)
    
    def get_all_managers(self) -> Dict[str, LifecycleManager]:
        """获取所有生命周期管理器"""
        with self._managers_lock:
            return self._managers.copy()
    
    def shutdown_all(self) -> None:
        """关闭所有管理器"""
        with self._managers_lock:
            for name, manager in list(self._managers.items()):
                try:
                    if not manager.is_stopped():
                        manager.dispose()
                except Exception as e:
                    self.logger.error(f"Error shutting down manager {name}: {e}")
            self._managers.clear()
            self.logger.info("All lifecycle managers shut down")


# 全局生命周期管理器实例
global_lifecycle_manager = GlobalLifecycleManager()


def create_test_session(session_id: str) -> TestSessionManager:
    """创建测试会话"""
    session_manager = TestSessionManager(session_id)
    global_lifecycle_manager.register_manager(session_manager)
    return session_manager


def get_test_session(session_id: str) -> Optional[TestSessionManager]:
    """获取测试会话"""
    manager = global_lifecycle_manager.get_manager(f"TestSession-{session_id}")
    return manager if isinstance(manager, TestSessionManager) else None


def cleanup_test_session(session_id: str) -> None:
    """清理测试会话"""
    global_lifecycle_manager.unregister_manager(f"TestSession-{session_id}")


@contextmanager
def test_session_context(session_id: str):
    """测试会话上下文管理器"""
    session = create_test_session(session_id)
    try:
        with session.lifecycle_context():
            yield session
    finally:
        cleanup_test_session(session_id)