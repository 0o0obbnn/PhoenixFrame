"""测试执行器

基于并行执行器的测试专用执行器，提供：
- 测试用例并行执行
- 测试套件管理
- 资源隔离和共享
- 结果收集和报告集成
- 失败重试和错误恢复
"""

import inspect
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union
import importlib.util
import threading
import time
from datetime import datetime

from .parallel_executor import (
    BaseParallelExecutor, ExecutionTask, TaskResult, ExecutionConfig, 
    ExecutionStrategy, TaskPriority, TaskStatus
)
from ..observability.logger import get_logger
from ..observability.report_collector import get_report_collector, test_context, suite_context
from ..web.driver_manager import get_driver_manager


@dataclass
class TestCase:
    """测试用例定义"""
    name: str
    func: Callable
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float = 60.0
    retry_attempts: int = 0
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parallel_safe: bool = True  # 是否可以并行执行
    
    def __post_init__(self):
        # 自动检测测试类型
        if hasattr(self.func, '__annotations__'):
            annotations = self.func.__annotations__
            if 'driver' in annotations or 'page' in annotations:
                self.metadata['requires_webdriver'] = True
        
        # 基于函数名设置默认标签
        if 'test_' in self.name.lower():
            if 'ui' in self.name.lower() or 'web' in self.name.lower():
                self.tags.append('ui')
            if 'api' in self.name.lower():
                self.tags.append('api')
            if 'unit' in self.name.lower():
                self.tags.append('unit')


@dataclass
class TestSuite:
    """测试套件定义"""
    name: str
    test_cases: List[TestCase] = field(default_factory=list)
    setup_suite: Optional[Callable] = None
    teardown_suite: Optional[Callable] = None
    parallel_execution: bool = True
    max_workers: Optional[int] = None
    shared_resources: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TestResourceManager:
    """测试资源管理器"""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._resources: Dict[str, Any] = {}
        self._resource_locks: Dict[str, threading.RLock] = {}
        self._lock = threading.RLock()
    
    def get_resource(self, name: str, factory: Optional[Callable] = None) -> Any:
        """获取或创建资源"""
        with self._lock:
            if name not in self._resources:
                if factory:
                    self._resources[name] = factory()
                    self._resource_locks[name] = threading.RLock()
                    self.logger.debug(f"Created resource: {name}")
                else:
                    return None
            
            return self._resources[name]
    
    def set_resource(self, name: str, resource: Any):
        """设置资源"""
        with self._lock:
            self._resources[name] = resource
            if name not in self._resource_locks:
                self._resource_locks[name] = threading.RLock()
            self.logger.debug(f"Set resource: {name}")
    
    def get_resource_lock(self, name: str) -> Optional[threading.RLock]:
        """获取资源锁"""
        return self._resource_locks.get(name)
    
    def remove_resource(self, name: str):
        """移除资源"""
        with self._lock:
            if name in self._resources:
                resource = self._resources.pop(name)
                self._resource_locks.pop(name, None)
                
                # 尝试清理资源
                if hasattr(resource, 'close'):
                    try:
                        resource.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing resource {name}: {e}")
                
                self.logger.debug(f"Removed resource: {name}")
    
    def clear_all(self):
        """清理所有资源"""
        with self._lock:
            for name in list(self._resources.keys()):
                self.remove_resource(name)


class TestExecutor(BaseParallelExecutor):
    """测试执行器"""
    
    def __init__(self, config: ExecutionConfig):
        super().__init__(config)
        self.resource_manager = TestResourceManager()
        self.report_collector = get_report_collector()
        self._current_suite: Optional[str] = None
        self._test_results: Dict[str, Dict[str, Any]] = {}
    
    def _get_logger(self):
        """获取日志记录器"""
        if self.logger is None:
            self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        return self.logger
    
    def add_test_suite(self, suite: TestSuite):
        """添加测试套件"""
        logger = self._get_logger()
        logger.info(f"Adding test suite: {suite.name} ({len(suite.test_cases)} tests)")
        
        # 设置共享资源
        for name, resource in suite.shared_resources.items():
            self.resource_manager.set_resource(f"{suite.name}.{name}", resource)
        
        # 转换测试用例为执行任务
        for test_case in suite.test_cases:
            task = self._create_test_task(suite, test_case)
            self.add_task(task)
    
    def _create_test_task(self, suite: TestSuite, test_case: TestCase) -> ExecutionTask:
        """创建测试任务"""
        task_id = f"{suite.name}.{test_case.name}"
        
        # 包装测试函数
        def test_wrapper():
            return self._execute_test_case(suite, test_case)
        
        return ExecutionTask(
            task_id=task_id,
            func=test_wrapper,
            priority=test_case.priority,
            timeout=test_case.timeout,
            retry_attempts=test_case.retry_attempts,
            dependencies=[f"{suite.name}.{dep}" for dep in test_case.dependencies],
            tags=test_case.tags,
            metadata={
                'suite_name': suite.name,
                'test_name': test_case.name,
                'parallel_safe': test_case.parallel_safe,
                **test_case.metadata
            }
        )
    
    def _execute_test_case(self, suite: TestSuite, test_case: TestCase) -> Dict[str, Any]:
        """执行单个测试用例"""
        test_id = f"{suite.name}.{test_case.name}"
        
        with test_context(test_case.name, test_case.parameters):
            try:
                self.logger.debug(f"Starting test: {test_id}")
                
                # 准备测试环境
                test_env = self._prepare_test_environment(suite, test_case)
                
                # 执行setup
                if test_case.setup:
                    self.logger.debug(f"Running setup for {test_id}")
                    test_case.setup()
                
                # 执行测试函数
                self.logger.debug(f"Running test function for {test_id}")
                
                # 检查函数签名并注入依赖
                result = self._execute_with_dependency_injection(
                    test_case.func, test_env
                )
                
                self.logger.info(f"Test passed: {test_id}")
                return {'status': 'passed', 'result': result, 'environment': test_env}
                
            except Exception as e:
                self.logger.error(f"Test failed: {test_id}, error: {e}")
                
                # 记录错误信息
                collector = get_report_collector()
                collector.fail_test(str(e), traceback.format_exc())
                
                return {
                    'status': 'failed', 
                    'error': str(e), 
                    'traceback': traceback.format_exc()
                }
                
            finally:
                # 执行teardown
                if test_case.teardown:
                    try:
                        self.logger.debug(f"Running teardown for {test_id}")
                        test_case.teardown()
                    except Exception as e:
                        self.logger.warning(f"Teardown failed for {test_id}: {e}")
                
                # 清理测试环境
                self._cleanup_test_environment(test_env)
    
    def _prepare_test_environment(self, suite: TestSuite, test_case: TestCase) -> Dict[str, Any]:
        """准备测试环境"""
        env = {}
        
        # 添加套件共享资源
        for name, resource in suite.shared_resources.items():
            env[name] = resource
        
        # 创建WebDriver（如果需要）
        if test_case.metadata.get('requires_webdriver'):
            driver_name = f"{suite.name}_{test_case.name}_{threading.current_thread().name}"
            
            try:
                driver_manager = get_driver_manager()
                driver = driver_manager.create_driver(
                    name=driver_name,
                    browser='chrome',
                    driver_type='selenium'
                )
                env['driver'] = driver
                env['_driver_name'] = driver_name
                
                self.logger.debug(f"Created WebDriver for {test_case.name}: {driver_name}")
                
            except Exception as e:
                self.logger.warning(f"Failed to create WebDriver for {test_case.name}: {e}")
        
        # 添加测试参数
        env.update(test_case.parameters)
        
        return env
    
    def _cleanup_test_environment(self, env: Dict[str, Any]):
        """清理测试环境"""
        # 清理WebDriver
        if '_driver_name' in env:
            try:
                driver_manager = get_driver_manager()
                driver_manager.stop_driver(env['_driver_name'])
                self.logger.debug(f"Cleaned up WebDriver: {env['_driver_name']}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup WebDriver: {e}")
    
    def _execute_with_dependency_injection(self, func: Callable, env: Dict[str, Any]) -> Any:
        """执行函数并注入依赖"""
        sig = inspect.signature(func)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name in env:
                kwargs[param_name] = env[param_name]
            elif param.annotation and param.annotation.__name__ in env:
                kwargs[param_name] = env[param.annotation.__name__]
        
        return func(**kwargs)
    
    def _execute_task(self, task: ExecutionTask) -> TaskResult:
        """执行测试任务"""
        result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now(),
            worker_id=threading.current_thread().name
        )
        
        try:
            # 执行测试
            test_result = task.func()
            result.result = test_result
            result.status = TaskStatus.COMPLETED
            
        except Exception as e:
            result.error = e
            result.status = TaskStatus.FAILED
            
        finally:
            result.end_time = datetime.now()
            result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def execute(self) -> Dict[str, TaskResult]:
        """执行所有任务"""
        logger = self._get_logger()
        
        self._is_running = True
        self._is_cancelled = False
        
        try:
            # 更新监控指标
            self.monitor.update_metrics(
                tasks_total=len(self._tasks),
                workers_active=0
            )
            
            # 使用简单执行作为默认方式
            results = {}
            for task_id, task in self._tasks.items():
                try:
                    result = task.func()
                    task_result = TaskResult(
                        task_id=task_id,
                        status=TaskStatus.COMPLETED,
                        result=result
                    )
                except Exception as e:
                    task_result = TaskResult(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        error=e
                    )
                results[task_id] = task_result
            
            self._results = results
            return results
            
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            raise
        finally:
            self._is_running = False
    
    def _do_execute(self):
        """执行所有测试"""
        # 使用线程池执行测试
        max_workers = self.config.max_workers or 4
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            self.monitor.update_metrics(workers_active=max_workers)
            
            future_to_task = {}
            
            while True:
                # 获取准备执行的任务
                ready_tasks = self._get_ready_tasks()
                
                # 提交新任务
                for task in ready_tasks:
                    if (task.task_id not in future_to_task and 
                        task.task_id not in self._completed_tasks and
                        task.task_id not in self._failed_tasks):
                        
                        # 检查是否可以并行执行
                        parallel_safe = task.metadata.get('parallel_safe', True)
                        if not parallel_safe and len(future_to_task) > 0:
                            continue  # 等待其他任务完成
                        
                        future = executor.submit(self._execute_task, task)
                        future_to_task[future] = task
                        self.logger.debug(f"Submitted test: {task.task_id}")
                
                # 处理完成的任务
                completed_futures = []
                for future in as_completed(future_to_task.keys(), timeout=0.1):
                    completed_futures.append(future)
                
                for future in completed_futures:
                    task = future_to_task.pop(future)
                    try:
                        result = future.result()
                        self._handle_task_completion(result)
                        
                        # 记录测试结果
                        suite_name = task.metadata.get('suite_name')
                        test_name = task.metadata.get('test_name')
                        if suite_name not in self._test_results:
                            self._test_results[suite_name] = {}
                        self._test_results[suite_name][test_name] = result
                        
                    except Exception as e:
                        self.logger.error(f"Error getting test result: {e}")
                
                # 检查完成条件
                if (len(self._completed_tasks) + len(self._failed_tasks) >= len(self._tasks) or
                    self._is_cancelled):
                    break
                
                if not future_to_task and not ready_tasks:
                    break
    
    def get_test_results_by_suite(self) -> Dict[str, Dict[str, TaskResult]]:
        """按套件获取测试结果"""
        return self._test_results.copy()


class TestDiscovery:
    """测试发现器"""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def discover_from_module(self, module) -> List[TestCase]:
        """从模块发现测试用例"""
        test_cases = []
        
        for name in dir(module):
            obj = getattr(module, name)
            
            if (callable(obj) and 
                name.startswith('test_') and 
                not name.startswith('test_suite')):
                
                test_case = TestCase(
                    name=name,
                    func=obj,
                    metadata={'module': module.__name__}
                )
                test_cases.append(test_case)
                
        self.logger.info(f"Discovered {len(test_cases)} test cases from {module.__name__}")
        return test_cases
    
    def discover_from_directory(self, directory: Union[str, Path]) -> Dict[str, List[TestCase]]:
        """从目录发现测试用例"""
        directory = Path(directory)
        discovered_tests = {}
        
        for py_file in directory.rglob('test_*.py'):
            module_name = py_file.stem
            
            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                test_cases = self.discover_from_module(module)
                if test_cases:
                    discovered_tests[module_name] = test_cases
                    
            except Exception as e:
                self.logger.error(f"Error loading module {py_file}: {e}")
        
        total_tests = sum(len(tests) for tests in discovered_tests.values())
        self.logger.info(f"Discovered {total_tests} test cases from {len(discovered_tests)} modules")
        
        return discovered_tests
    
    def create_test_suite(self, name: str, test_cases: List[TestCase], **kwargs) -> TestSuite:
        """创建测试套件"""
        return TestSuite(
            name=name,
            test_cases=test_cases,
            **kwargs
        )


# 便捷函数
def create_test_executor(max_workers: Optional[int] = None, 
                        strategy: ExecutionStrategy = ExecutionStrategy.THREAD_POOL) -> TestExecutor:
    """创建测试执行器的便捷函数"""
    config = ExecutionConfig(
        strategy=strategy,
        max_workers=max_workers,
        enable_progress_tracking=True,
        enable_resource_monitoring=True
    )
    return TestExecutor(config)


def run_test_suite(suite: TestSuite, 
                  max_workers: Optional[int] = None) -> Dict[str, TaskResult]:
    """运行测试套件的便捷函数"""
    executor = create_test_executor(max_workers)
    executor.add_test_suite(suite)
    return executor.execute()


def discover_and_run_tests(directory: Union[str, Path], 
                          max_workers: Optional[int] = None) -> Dict[str, Dict[str, TaskResult]]:
    """发现并运行测试的便捷函数"""
    discovery = TestDiscovery()
    discovered_tests = discovery.discover_from_directory(directory)
    
    executor = create_test_executor(max_workers)
    
    for module_name, test_cases in discovered_tests.items():
        suite = discovery.create_test_suite(module_name, test_cases)
        executor.add_test_suite(suite)
    
    executor.execute()
    return executor.get_test_results_by_suite()