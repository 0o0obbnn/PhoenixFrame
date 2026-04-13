"""性能监控集成

为测试执行和Web自动化提供深度性能监控集成，包括：
- 测试执行性能监控
- Web操作性能分析
- 自动瓶颈检测
- 性能优化建议
- 实时性能告警
"""

import functools
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from .performance_monitor import get_performance_analyzer, get_performance_profiler
from .metrics import get_metrics_collector
from ..observability.logger import get_logger


class PerformanceMonitoringMixin:
    """性能监控混入类"""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.performance_analyzer = get_performance_analyzer()
        self.performance_profiler = get_performance_profiler()
        self.metrics_collector = get_metrics_collector()
        self._operation_start_times: Dict[str, float] = {}
    
    def start_operation_timing(self, operation_name: str):
        """开始操作计时"""
        self._operation_start_times[operation_name] = time.time()
        self.performance_profiler.start_timer(operation_name)
    
    def end_operation_timing(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """结束操作计时"""
        if operation_name in self._operation_start_times:
            duration = time.time() - self._operation_start_times.pop(operation_name)
            self.performance_profiler.end_timer(operation_name)
            
            # 记录到指标系统
            labels = {"operation": operation_name}
            if metadata:
                labels.update(metadata)
            
            self.metrics_collector.record_metric(
                "operation_duration", duration, "seconds", labels
            )
            
            # 检查性能异常
            self._check_performance_anomaly(operation_name, duration, metadata)
            
            return duration
        return 0.0
    
    def _check_performance_anomaly(self, operation_name: str, duration: float, metadata: Optional[Dict[str, Any]] = None):
        """检查性能异常"""
        # 获取历史性能数据
        profile_summary = self.performance_profiler.get_profile_summary()
        
        if operation_name in profile_summary:
            stats = profile_summary[operation_name]
            avg_time = stats['avg_time']
            p95_time = stats['p95_time']
            
            # 检查是否超过平均时间的3倍
            if duration > avg_time * 3:
                self.logger.warning(
                    f"Performance anomaly detected: {operation_name} took {duration:.3f}s "
                    f"(avg: {avg_time:.3f}s, 3x threshold: {avg_time * 3:.3f}s)"
                )
                
                # 记录异常指标
                self.metrics_collector.record_metric(
                    "performance_anomaly", 1, "count",
                    {"operation": operation_name, "severity": "high"}
                )
            
            # 检查是否超过P95
            elif duration > p95_time * 1.5:
                self.logger.info(
                    f"Performance degradation: {operation_name} took {duration:.3f}s "
                    f"(p95: {p95_time:.3f}s)"
                )
                
                # 记录性能退化
                self.metrics_collector.record_metric(
                    "performance_degradation", 1, "count",
                    {"operation": operation_name, "severity": "medium"}
                )
    
    @contextmanager
    def monitor_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """操作监控上下文管理器"""
        self.start_operation_timing(operation_name)
        try:
            yield
        finally:
            self.end_operation_timing(operation_name, metadata)


def performance_monitor(operation_name: Optional[str] = None, track_memory: bool = False):
    """性能监控装饰器"""
    def decorator(func: Callable):
        name = operation_name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = get_performance_profiler()
            metrics_collector = get_metrics_collector()
            
            # 开始监控
            start_time = time.time()
            profiler.start_timer(name)
            
            # 内存监控（如果启用）
            start_memory = None
            if track_memory:
                try:
                    import psutil
                    process = psutil.Process()
                    start_memory = process.memory_info().rss / 1024 / 1024  # MB
                except ImportError:
                    pass
            
            try:
                result = func(*args, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                # 结束监控
                duration = profiler.end_timer(name)
                
                # 记录指标
                labels = {"function": name, "status": status}
                metrics_collector.record_metric("function_duration", duration, "seconds", labels)
                metrics_collector.record_metric("function_calls", 1, "count", labels)
                
                # 内存监控
                if track_memory and start_memory is not None:
                    try:
                        import psutil
                        process = psutil.Process()
                        end_memory = process.memory_info().rss / 1024 / 1024  # MB
                        memory_delta = end_memory - start_memory
                        
                        metrics_collector.record_metric(
                            "function_memory_delta", memory_delta, "mb", labels
                        )
                        
                        if memory_delta > 50:  # 超过50MB增长
                            logger = get_logger("performance_monitor")
                            logger.warning(
                                f"High memory usage in {name}: {memory_delta:.1f}MB increase"
                            )
                    except ImportError:
                        pass
        
        return wrapper
    return decorator


class TestPerformanceMonitor(PerformanceMonitoringMixin):
    """测试性能监控器"""
    
    def __init__(self):
        super().__init__()
        self.test_timings: Dict[str, Dict[str, float]] = {}
        self.slow_tests_threshold = 10.0  # 慢测试阈值（秒）
    
    def start_test_monitoring(self, test_name: str):
        """开始测试监控"""
        self.test_timings[test_name] = {
            "start_time": time.time(),
            "setup_duration": 0.0,
            "execution_duration": 0.0,
            "teardown_duration": 0.0
        }
        
        self.start_operation_timing(f"test.{test_name}")
        self.metrics_collector.record_test_start(test_name)
    
    def mark_test_phase(self, test_name: str, phase: str):
        """标记测试阶段"""
        if test_name in self.test_timings:
            current_time = time.time()
            start_time = self.test_timings[test_name]["start_time"]
            
            if phase == "setup_complete":
                self.test_timings[test_name]["setup_duration"] = current_time - start_time
            elif phase == "execution_complete":
                setup_duration = self.test_timings[test_name]["setup_duration"]
                self.test_timings[test_name]["execution_duration"] = current_time - start_time - setup_duration
    
    def end_test_monitoring(self, test_name: str, outcome: str):
        """结束测试监控"""
        if test_name not in self.test_timings:
            return
        
        total_duration = self.end_operation_timing(f"test.{test_name}")
        test_timing = self.test_timings[test_name]
        
        # 计算teardown时间
        execution_time = test_timing["setup_duration"] + test_timing["execution_duration"]
        test_timing["teardown_duration"] = total_duration - execution_time
        
        # 记录详细指标
        self.metrics_collector.record_test_end(test_name, outcome, total_duration)
        
        # 记录各阶段时间
        for phase, duration in test_timing.items():
            if phase != "start_time":
                self.metrics_collector.record_metric(
                    f"test_{phase}", duration, "seconds",
                    {"test_name": test_name, "outcome": outcome}
                )
        
        # 检查慢测试
        if total_duration > self.slow_tests_threshold:
            self.logger.warning(
                f"Slow test detected: {test_name} took {total_duration:.2f}s "
                f"(threshold: {self.slow_tests_threshold}s)"
            )
            
            self.metrics_collector.record_metric(
                "slow_test", 1, "count",
                {"test_name": test_name, "duration": total_duration}
            )
        
        # 分析测试性能
        self._analyze_test_performance(test_name, test_timing, outcome)
        
        # 清理
        del self.test_timings[test_name]
    
    def _analyze_test_performance(self, test_name: str, timing: Dict[str, float], outcome: str):
        """分析测试性能"""
        total_duration = timing["setup_duration"] + timing["execution_duration"] + timing["teardown_duration"]
        
        # 计算各阶段占比
        setup_ratio = timing["setup_duration"] / total_duration if total_duration > 0 else 0
        execution_ratio = timing["execution_duration"] / total_duration if total_duration > 0 else 0
        teardown_ratio = timing["teardown_duration"] / total_duration if total_duration > 0 else 0
        
        # 性能优化建议
        suggestions = []
        
        if setup_ratio > 0.3:  # setup超过30%
            suggestions.append("Setup time is high, consider optimizing test initialization")
        
        if teardown_ratio > 0.2:  # teardown超过20%
            suggestions.append("Teardown time is high, consider optimizing cleanup")
        
        if execution_ratio < 0.5:  # 实际执行时间少于50%
            suggestions.append("Test overhead is high, actual test logic takes less than 50% of total time")
        
        if suggestions:
            self.logger.info(f"Performance suggestions for {test_name}: {'; '.join(suggestions)}")
            
            for suggestion in suggestions:
                self.metrics_collector.record_metric(
                    "test_performance_suggestion", 1, "count",
                    {"test_name": test_name, "suggestion": suggestion}
                )


class WebPerformanceMonitor(PerformanceMonitoringMixin):
    """Web自动化性能监控器"""
    
    def __init__(self):
        super().__init__()
        self.page_load_threshold = 5.0  # 页面加载阈值（秒）
        self.element_operation_threshold = 2.0  # 元素操作阈值（秒）
    
    def monitor_page_load(self, url: str):
        """监控页面加载性能"""
        @contextmanager
        def page_load_monitor():
            start_time = time.time()
            self.start_operation_timing(f"page_load.{url}")
            
            try:
                yield
                outcome = "success"
            except Exception as e:
                outcome = "error"
                raise
            finally:
                duration = self.end_operation_timing(f"page_load.{url}")
                
                # 记录页面加载指标
                self.metrics_collector.record_metric(
                    "page_load_duration", duration, "seconds",
                    {"url": url, "outcome": outcome}
                )
                
                # 检查慢页面加载
                if duration > self.page_load_threshold:
                    self.logger.warning(
                        f"Slow page load: {url} took {duration:.2f}s "
                        f"(threshold: {self.page_load_threshold}s)"
                    )
                    
                    self.metrics_collector.record_metric(
                        "slow_page_load", 1, "count",
                        {"url": url, "duration": duration}
                    )
        
        return page_load_monitor()
    
    def monitor_element_operation(self, operation: str, element: str = ""):
        """监控元素操作性能"""
        @contextmanager
        def element_operation_monitor():
            operation_id = f"{operation}.{element}" if element else operation
            start_time = time.time()
            self.start_operation_timing(f"element_operation.{operation_id}")
            
            try:
                yield
                outcome = "success"
            except Exception as e:
                outcome = "error"
                raise
            finally:
                duration = self.end_operation_timing(f"element_operation.{operation_id}")
                
                # 记录元素操作指标
                self.metrics_collector.record_web_action(operation, duration, outcome, element)
                
                # 检查慢元素操作
                if duration > self.element_operation_threshold:
                    self.logger.warning(
                        f"Slow element operation: {operation} on {element} took {duration:.2f}s "
                        f"(threshold: {self.element_operation_threshold}s)"
                    )
                    
                    self.metrics_collector.record_metric(
                        "slow_element_operation", 1, "count",
                        {"operation": operation, "element": element, "duration": duration}
                    )
        
        return element_operation_monitor()
    
    def analyze_web_performance(self) -> Dict[str, Any]:
        """分析Web性能"""
        profile_summary = self.performance_profiler.get_profile_summary()
        
        # 筛选Web相关操作
        page_load_ops = {k: v for k, v in profile_summary.items() if k.startswith("page_load.")}
        element_ops = {k: v for k, v in profile_summary.items() if k.startswith("element_operation.")}
        
        analysis = {
            "page_loads": {
                "total_count": sum(stats["count"] for stats in page_load_ops.values()),
                "avg_duration": statistics.mean([stats["avg_time"] for stats in page_load_ops.values()]) if page_load_ops else 0,
                "slowest_pages": sorted([
                    (k.replace("page_load.", ""), v["max_time"])
                    for k, v in page_load_ops.items()
                ], key=lambda x: x[1], reverse=True)[:5]
            },
            "element_operations": {
                "total_count": sum(stats["count"] for stats in element_ops.values()),
                "avg_duration": statistics.mean([stats["avg_time"] for stats in element_ops.values()]) if element_ops else 0,
                "slowest_operations": sorted([
                    (k.replace("element_operation.", ""), v["max_time"])
                    for k, v in element_ops.items()
                ], key=lambda x: x[1], reverse=True)[:5]
            }
        }
        
        return analysis


# 全局实例
_test_performance_monitor: Optional[TestPerformanceMonitor] = None
_web_performance_monitor: Optional[WebPerformanceMonitor] = None


def get_test_performance_monitor() -> TestPerformanceMonitor:
    """获取测试性能监控器"""
    global _test_performance_monitor
    if _test_performance_monitor is None:
        _test_performance_monitor = TestPerformanceMonitor()
    return _test_performance_monitor


def get_web_performance_monitor() -> WebPerformanceMonitor:
    """获取Web性能监控器"""
    global _web_performance_monitor
    if _web_performance_monitor is None:
        _web_performance_monitor = WebPerformanceMonitor()
    return _web_performance_monitor


# 便捷上下文管理器
def monitor_test_performance(test_name: str):
    """测试性能监控上下文管理器"""
    @contextmanager
    def test_monitor():
        monitor = get_test_performance_monitor()
        monitor.start_test_monitoring(test_name)
        try:
            yield monitor
            outcome = "passed"
        except Exception:
            outcome = "failed"
            raise
        finally:
            monitor.end_test_monitoring(test_name, outcome)
    
    return test_monitor()


def monitor_page_load(url: str):
    """页面加载性能监控上下文管理器"""
    monitor = get_web_performance_monitor()
    return monitor.monitor_page_load(url)


def monitor_element_operation(operation: str, element: str = ""):
    """元素操作性能监控上下文管理器"""
    monitor = get_web_performance_monitor()
    return monitor.monitor_element_operation(operation, element)


# 便捷装饰器
def monitor_web_method(operation_name: Optional[str] = None):
    """Web方法性能监控装饰器"""
    def decorator(func: Callable):
        name = operation_name or func.__name__
        
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            element = args[0] if args and isinstance(args[0], str) else ""
            
            with monitor_element_operation(name, element):
                return func(self, *args, **kwargs)
        
        return wrapper
    return decorator