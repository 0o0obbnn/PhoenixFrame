"""并行测试执行器

提供高性能的并行测试执行功能，包括：
- 多进程/多线程并行执行
- 智能任务分配和负载均衡
- 资源隔离和冲突避免
- 实时进度监控和结果聚合
- 失败重试和错误恢复
"""

import os
import time
import queue
import threading
import multiprocessing as mp
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, Tuple
from datetime import datetime
import psutil

from ..core.lifecycle import LifecycleManager
from ..observability.logger import get_logger
from ..observability.metrics import get_meter
from ..observability.report_collector import get_report_collector


class ExecutionStrategy(Enum):
    """执行策略枚举"""
    SEQUENTIAL = "sequential"         # 顺序执行
    THREAD_POOL = "thread_pool"      # 线程池并行
    PROCESS_POOL = "process_pool"    # 进程池并行
    MIXED = "mixed"                  # 混合模式
    ADAPTIVE = "adaptive"            # 自适应模式


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    worker_id: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds()


@dataclass
class ExecutionTask:
    """执行任务"""
    task_id: str
    func: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[float] = None
    retry_attempts: int = 0
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.task_id)
    
    def __eq__(self, other):
        return isinstance(other, ExecutionTask) and self.task_id == other.task_id


@dataclass
class ExecutionConfig:
    """执行配置"""
    strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE
    max_workers: Optional[int] = None
    worker_timeout: float = 300.0  # 5分钟
    task_timeout: float = 60.0     # 1分钟
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_progress_tracking: bool = True
    enable_resource_monitoring: bool = True
    chunk_size: int = 1
    memory_limit_mb: Optional[int] = None
    cpu_limit_percent: Optional[float] = None


class ExecutionMonitor:
    """执行监控器"""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.meter = get_meter("ParallelExecutor")
        self._metrics = {
            'tasks_total': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_retrying': 0,
            'workers_active': 0,
            'memory_usage_mb': 0.0,
            'cpu_usage_percent': 0.0
        }
        self._lock = threading.RLock()
        self._start_time = datetime.now()
    
    def update_metrics(self, **kwargs):
        """更新监控指标"""
        with self._lock:
            self._metrics.update(kwargs)
    
    def increment_metric(self, name: str, value: int = 1):
        """增加指标值"""
        with self._lock:
            if name in self._metrics:
                self._metrics[name] += value
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取当前指标"""
        with self._lock:
            current_time = datetime.now()
            elapsed = (current_time - self._start_time).total_seconds()
            
            metrics = self._metrics.copy()
            metrics.update({
                'elapsed_time': elapsed,
                'throughput': metrics['tasks_completed'] / elapsed if elapsed > 0 else 0,
                'success_rate': (metrics['tasks_completed'] / metrics['tasks_total'] * 100) 
                               if metrics['tasks_total'] > 0 else 0
            })
            return metrics
    
    def log_progress(self):
        """记录进度信息"""
        metrics = self.get_metrics()
        self.logger.info(
            f"执行进度: {metrics['tasks_completed']}/{metrics['tasks_total']} "
            f"({metrics['success_rate']:.1f}% 成功率), "
            f"活跃工作线程: {metrics['workers_active']}, "
            f"吞吐量: {metrics['throughput']:.2f} tasks/sec"
        )


class BaseParallelExecutor(ABC):
    """并行执行器基类"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self.logger = None  # 延迟初始化日志记录器
        self.monitor = ExecutionMonitor()
        self.report_collector = get_report_collector()
        
        # 任务管理
        self._tasks: Dict[str, ExecutionTask] = {}
        self._results: Dict[str, TaskResult] = {}
        self._task_queue = queue.PriorityQueue()
        self._completed_tasks = set()
        self._failed_tasks = set()
        
        # 状态控制
        self._is_running = False
        self._is_cancelled = False
        self._lock = threading.RLock()
        
        # 生命周期管理
        self._lifecycle = LifecycleManager("ParallelExecutor")
    
    def _get_logger(self):
        """获取日志记录器"""
        if self.logger is None:
            from ..observability.logger import get_logger
            self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        return self.logger
    
    @abstractmethod
    def _execute_task(self, task: ExecutionTask) -> TaskResult:
        """执行单个任务（子类实现）"""
        pass
    
    def add_task(self, task: ExecutionTask) -> None:
        """添加任务"""
        with self._lock:
            if self._is_running:
                raise RuntimeError("Cannot add tasks while executor is running")
            
            self._tasks[task.task_id] = task
            self.logger.debug(f"Added task: {task.task_id}")
    
    def add_tasks(self, tasks: List[ExecutionTask]) -> None:
        """批量添加任务"""
        for task in tasks:
            self.add_task(task)
    
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False
    
    def get_task(self, task_id: str) -> Optional[ExecutionTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        return self._results.get(task_id)
    
    def get_all_results(self) -> Dict[str, TaskResult]:
        """获取所有任务结果"""
        return self._results.copy()
    
    def _validate_dependencies(self) -> List[str]:
        """验证任务依赖关系"""
        issues = []
        
        for task in self._tasks.values():
            for dep_id in task.dependencies:
                if dep_id not in self._tasks:
                    issues.append(f"Task {task.task_id} depends on non-existent task {dep_id}")
        
        # 检查循环依赖（简单检查）
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            if task_id in rec_stack:
                return True
            if task_id in visited:
                return False
            
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = self._tasks.get(task_id)
            if task:
                for dep_id in task.dependencies:
                    if has_cycle(dep_id):
                        return True
            
            rec_stack.remove(task_id)
            return False
        
        for task_id in self._tasks:
            if has_cycle(task_id):
                issues.append(f"Circular dependency detected involving task {task_id}")
                break
        
        return issues
    
    def _get_ready_tasks(self) -> List[ExecutionTask]:
        """获取准备执行的任务"""
        ready_tasks = []
        
        for task in self._tasks.values():
            # 检查是否已完成或失败
            if task.task_id in self._completed_tasks or task.task_id in self._failed_tasks:
                continue
            
            # 检查依赖是否满足
            dependencies_met = all(
                dep_id in self._completed_tasks for dep_id in task.dependencies
            )
            
            if dependencies_met:
                ready_tasks.append(task)
        
        # 按优先级排序
        ready_tasks.sort(key=lambda t: t.priority.value, reverse=True)
        return ready_tasks
    
    def _handle_task_completion(self, result: TaskResult):
        """处理任务完成"""
        with self._lock:
            self._results[result.task_id] = result
            
            if result.status == TaskStatus.COMPLETED:
                self._completed_tasks.add(result.task_id)
                self.monitor.increment_metric('tasks_completed')
                self.logger.debug(f"Task completed: {result.task_id}")
            elif result.status == TaskStatus.FAILED:
                self._failed_tasks.add(result.task_id)
                self.monitor.increment_metric('tasks_failed')
                self.logger.warning(f"Task failed: {result.task_id}, error: {result.error}")
    
    def _should_retry_task(self, task: ExecutionTask, result: TaskResult) -> bool:
        """判断是否应该重试任务"""
        return (result.status == TaskStatus.FAILED and 
                result.retry_count < task.retry_attempts)
    
    def execute(self) -> Dict[str, TaskResult]:
        """执行所有任务"""
        with self._lock:
            if self._is_running:
                raise RuntimeError("Executor is already running")
            
            # 验证依赖关系
            issues = self._validate_dependencies()
            if issues:
                raise ValueError(f"Task dependency issues: {'; '.join(issues)}")
            
            self._is_running = True
            self._is_cancelled = False
            
            # 初始化监控
            self.monitor.update_metrics(
                tasks_total=len(self._tasks),
                tasks_completed=0,
                tasks_failed=0,
                tasks_retrying=0
            )
        
        try:
            self.logger.info(f"Starting execution of {len(self._tasks)} tasks with strategy: {self.config.strategy}")
            
            # 开始执行
            start_time = datetime.now()
            self._do_execute()
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            self.logger.info(f"Execution completed in {duration:.2f} seconds")
            
            # 记录最终统计
            metrics = self.monitor.get_metrics()
            self.logger.info(
                f"Final results: {metrics['tasks_completed']} completed, "
                f"{metrics['tasks_failed']} failed, "
                f"{metrics['success_rate']:.1f}% success rate"
            )
            
            return self._results.copy()
            
        finally:
            with self._lock:
                self._is_running = False
    
    @abstractmethod
    def _do_execute(self):
        """执行实现（子类实现）"""
        pass
    
    def cancel(self):
        """取消执行"""
        with self._lock:
            self._is_cancelled = True
            self.logger.info("Execution cancelled")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._is_running
    
    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self._is_cancelled


class ThreadPoolExecutor_Custom(BaseParallelExecutor):
    """基于线程池的并行执行器"""
    
    def __init__(self, config: ExecutionConfig):
        super().__init__(config)
        self._max_workers = config.max_workers or min(32, (os.cpu_count() or 1) + 4)
    
    def _execute_task(self, task: ExecutionTask) -> TaskResult:
        """执行单个任务"""
        result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now(),
            worker_id=threading.current_thread().name
        )
        
        try:
            # 执行任务函数
            result.result = task.func(*task.args, **task.kwargs)
            result.status = TaskStatus.COMPLETED
            
        except Exception as e:
            result.error = e
            result.status = TaskStatus.FAILED
            self.logger.error(f"Task {task.task_id} failed: {e}")
            
        finally:
            result.end_time = datetime.now()
            result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def _do_execute(self):
        """使用线程池执行任务"""
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            self.monitor.update_metrics(workers_active=self._max_workers)
            
            # 提交所有准备好的任务
            future_to_task = {}
            
            while True:
                # 获取准备执行的任务
                ready_tasks = self._get_ready_tasks()
                
                # 提交新任务
                for task in ready_tasks:
                    if (task.task_id not in future_to_task and 
                        task.task_id not in self._completed_tasks and
                        task.task_id not in self._failed_tasks):
                        
                        future = executor.submit(self._execute_task, task)
                        future_to_task[future] = task
                        self.logger.debug(f"Submitted task: {task.task_id}")
                
                # 检查是否有任务完成
                completed_futures = []
                for future in as_completed(future_to_task.keys(), timeout=0.1):
                    completed_futures.append(future)
                
                # 处理完成的任务
                for future in completed_futures:
                    task = future_to_task.pop(future)
                    try:
                        result = future.result()
                        self._handle_task_completion(result)
                        
                        # 检查是否需要重试
                        if self._should_retry_task(task, result):
                            result.retry_count += 1
                            result.status = TaskStatus.RETRYING
                            self.monitor.increment_metric('tasks_retrying')
                            time.sleep(self.config.retry_delay)
                            
                            # 重新提交任务
                            future = executor.submit(self._execute_task, task)
                            future_to_task[future] = task
                            
                    except Exception as e:
                        self.logger.error(f"Error getting task result: {e}")
                
                # 检查是否所有任务都完成
                if (len(self._completed_tasks) + len(self._failed_tasks) >= len(self._tasks) or
                    self._is_cancelled):
                    break
                
                # 如果没有正在运行的任务且没有准备好的任务，则退出
                if not future_to_task and not ready_tasks:
                    break
            
            # 等待剩余任务完成
            for future in future_to_task:
                try:
                    result = future.result(timeout=self.config.worker_timeout)
                    task = future_to_task[future]
                    self._handle_task_completion(result)
                except Exception as e:
                    self.logger.error(f"Error waiting for task completion: {e}")


class ProcessPoolExecutor_Custom(BaseParallelExecutor):
    """基于进程池的并行执行器"""
    
    def __init__(self, config: ExecutionConfig):
        super().__init__(config)
        self._max_workers = config.max_workers or os.cpu_count() or 1
    
    def _execute_task(self, task: ExecutionTask) -> TaskResult:
        """执行单个任务（进程安全版本）"""
        result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now(),
            worker_id=f"Process-{os.getpid()}"
        )
        
        try:
            # 执行任务函数
            result.result = task.func(*task.args, **task.kwargs)
            result.status = TaskStatus.COMPLETED
            
        except Exception as e:
            result.error = e
            result.status = TaskStatus.FAILED
            
        finally:
            result.end_time = datetime.now()
            result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def _do_execute(self):
        """使用进程池执行任务"""
        with ProcessPoolExecutor(max_workers=self._max_workers) as executor:
            self.monitor.update_metrics(workers_active=self._max_workers)
            
            # 获取所有独立的任务（无依赖关系的任务）
            independent_tasks = [
                task for task in self._tasks.values() 
                if not task.dependencies
            ]
            
            # 提交独立任务
            future_to_task = {}
            for task in independent_tasks:
                future = executor.submit(_execute_task_wrapper, task)
                future_to_task[future] = task
                
            # 处理完成的任务
            for future in as_completed(future_to_task.keys()):
                task = future_to_task[future]
                try:
                    result = future.result()
                    self._handle_task_completion(result)
                except Exception as e:
                    self.logger.error(f"Error getting task result: {e}")


def _execute_task_wrapper(task: ExecutionTask) -> TaskResult:
    """任务执行包装器（用于进程池）"""
    result = TaskResult(
        task_id=task.task_id,
        status=TaskStatus.RUNNING,
        start_time=datetime.now(),
        worker_id=f"Process-{os.getpid()}"
    )
    
    try:
        result.result = task.func(*task.args, **task.kwargs)
        result.status = TaskStatus.COMPLETED
    except Exception as e:
        result.error = e
        result.status = TaskStatus.FAILED
    finally:
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
    
    return result


class AdaptiveParallelExecutor(BaseParallelExecutor):
    """自适应并行执行器"""
    
    def __init__(self, config: ExecutionConfig):
        super().__init__(config)
        self._thread_executor = ThreadPoolExecutor_Custom(config)
        self._process_executor = ProcessPoolExecutor_Custom(config)
    
    def _analyze_tasks(self) -> Dict[str, List[ExecutionTask]]:
        """分析任务特性并分类"""
        io_intensive = []      # IO密集型任务
        cpu_intensive = []     # CPU密集型任务
        mixed = []            # 混合型任务
        
        for task in self._tasks.values():
            task_type = task.metadata.get('task_type', 'mixed')
            
            if task_type == 'io_intensive':
                io_intensive.append(task)
            elif task_type == 'cpu_intensive':
                cpu_intensive.append(task)
            else:
                mixed.append(task)
        
        return {
            'io_intensive': io_intensive,
            'cpu_intensive': cpu_intensive,
            'mixed': mixed
        }
    
    def _do_execute(self):
        """自适应执行策略"""
        task_categories = self._analyze_tasks()
        
        # CPU密集型任务使用进程池
        if task_categories['cpu_intensive']:
            self.logger.info(f"Executing {len(task_categories['cpu_intensive'])} CPU-intensive tasks with process pool")
            cpu_config = ExecutionConfig(strategy=ExecutionStrategy.PROCESS_POOL)
            cpu_executor = ProcessPoolExecutor_Custom(cpu_config)
            
            for task in task_categories['cpu_intensive']:
                cpu_executor.add_task(task)
            
            cpu_results = cpu_executor.execute()
            self._results.update(cpu_results)
        
        # IO密集型和混合型任务使用线程池
        thread_tasks = task_categories['io_intensive'] + task_categories['mixed']
        if thread_tasks:
            self.logger.info(f"Executing {len(thread_tasks)} IO-intensive/mixed tasks with thread pool")
            thread_config = ExecutionConfig(strategy=ExecutionStrategy.THREAD_POOL)
            thread_executor = ThreadPoolExecutor_Custom(thread_config)
            
            for task in thread_tasks:
                thread_executor.add_task(task)
            
            thread_results = thread_executor.execute()
            self._results.update(thread_results)


class ParallelExecutorFactory:
    """并行执行器工厂"""
    
    @staticmethod
    def create_executor(config: ExecutionConfig) -> BaseParallelExecutor:
        """根据配置创建执行器"""
        if config.strategy == ExecutionStrategy.THREAD_POOL:
            return ThreadPoolExecutor_Custom(config)
        elif config.strategy == ExecutionStrategy.PROCESS_POOL:
            return ProcessPoolExecutor_Custom(config)
        elif config.strategy == ExecutionStrategy.ADAPTIVE:
            return AdaptiveParallelExecutor(config)
        else:
            raise ValueError(f"Unsupported execution strategy: {config.strategy}")


# 便捷函数
def execute_tasks_parallel(tasks: List[ExecutionTask], 
                          config: Optional[ExecutionConfig] = None) -> Dict[str, TaskResult]:
    """并行执行任务的便捷函数"""
    if config is None:
        config = ExecutionConfig()
    
    executor = ParallelExecutorFactory.create_executor(config)
    executor.add_tasks(tasks)
    return executor.execute()


def create_task(task_id: str, func: Callable, *args, **kwargs) -> ExecutionTask:
    """创建执行任务的便捷函数"""
    return ExecutionTask(
        task_id=task_id,
        func=func,
        args=args,
        kwargs=kwargs
    )