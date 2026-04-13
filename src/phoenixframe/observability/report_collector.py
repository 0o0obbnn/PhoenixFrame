"""报告数据收集器

提供测试执行过程中的数据收集功能，包括：
- 测试结果自动收集
- 生命周期事件监听
- 性能指标收集
- 错误和异常捕获
- 截图和日志关联
"""

import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING
from pathlib import Path
from contextlib import contextmanager

if TYPE_CHECKING:
    from ..core.lifecycle import LifecycleEvent, LifecycleEventData

from ..observability.logger import get_logger
from ..observability.tracer import get_tracer
from .report_generator import TestResult, TestSuite, ReportSummary, TestReport


class ReportCollector:
    """报告数据收集器"""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.tracer = get_tracer("ReportCollector")
        
        # 数据存储
        self._test_suites: Dict[str, TestSuite] = {}
        self._current_suite: Optional[TestSuite] = None
        self._current_test: Optional[TestResult] = None
        self._lock = threading.RLock()
        
        # 收集器配置
        self._auto_screenshot = True
        self._collect_logs = True
        self._collect_metrics = True
        self._max_log_entries = 1000
        
        # 事件回调
        self._callbacks: Dict[str, List[Callable]] = {
            'test_started': [],
            'test_completed': [],
            'suite_started': [],
            'suite_completed': [],
            'report_generated': []
        }
    
    def configure(self,
                 auto_screenshot: bool = True,
                 collect_logs: bool = True,
                 collect_metrics: bool = True,
                 max_log_entries: int = 1000):
        """配置收集器参数"""
        with self._lock:
            self._auto_screenshot = auto_screenshot
            self._collect_logs = collect_logs
            self._collect_metrics = collect_metrics
            self._max_log_entries = max_log_entries
            
        self.logger.debug("Report collector configured")
    
    def add_callback(self, event: str, callback: Callable):
        """添加事件回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable):
        """移除事件回调"""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
    
    def _trigger_callback(self, event: str, *args, **kwargs):
        """触发事件回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in callback for {event}: {e}")
    
    # === 生命周期事件处理 ===
    
    def on_lifecycle_event(self, event_data: Any):
        """处理生命周期事件"""
        try:
            # 延迟导入避免循环依赖
            from ..core.lifecycle import LifecycleEvent
            
            event = event_data.event if hasattr(event_data, 'event') else None
            data = event_data.data if hasattr(event_data, 'data') else {}
            
            with self._lock:
                if event == LifecycleEvent.BEFORE_INIT:
                    self._on_session_started(event_data)
                elif event == LifecycleEvent.AFTER_DISPOSE:
                    self._on_session_ended(event_data)
                elif event == LifecycleEvent.ERROR_OCCURRED:
                    self._on_error_occurred(event_data)
                    
        except Exception as e:
            self.logger.error(f"Error handling lifecycle event: {e}")
    
    def _on_session_started(self, event_data: Any):
        """处理会话开始事件"""
        data = event_data.data if hasattr(event_data, 'data') else {}
        session_name = data.get('session_name', 'Unknown Session')
        self.start_suite(session_name)
    
    def _on_session_ended(self, event_data: Any):
        """处理会话结束事件"""
        if self._current_suite:
            self.end_suite()
    
    def _on_error_occurred(self, event_data: Any):
        """处理错误事件"""
        if self._current_test:
            data = event_data.data if hasattr(event_data, 'data') else {}
            error_message = data.get('error', 'Unknown error')
            self.fail_test(error_message)
    
    # === 测试套件管理 ===
    
    def start_suite(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> TestSuite:
        """开始测试套件"""
        with self._lock:
            # 结束当前套件（如果存在）
            if self._current_suite:
                self.end_suite()
            
            suite = TestSuite(
                name=name,
                start_time=datetime.now(),
                metadata=metadata or {}
            )
            
            self._current_suite = suite
            self._test_suites[name] = suite
            
            self.logger.info(f"Started test suite: {name}")
            self._trigger_callback('suite_started', suite)
            
            return suite
    
    def end_suite(self) -> Optional[TestSuite]:
        """结束当前测试套件"""
        with self._lock:
            if not self._current_suite:
                return None
            
            # 结束当前测试（如果存在）
            if self._current_test:
                self.end_test()
            
            suite = self._current_suite
            suite.end_time = datetime.now()
            
            if suite.start_time:
                suite.duration = (suite.end_time - suite.start_time).total_seconds()
            
            self.logger.info(f"Ended test suite: {suite.name} "
                           f"({suite.total_tests} tests, {suite.duration:.2f}s)")
            
            self._trigger_callback('suite_completed', suite)
            self._current_suite = None
            
            return suite
    
    def get_suite(self, name: str) -> Optional[TestSuite]:
        """获取测试套件"""
        return self._test_suites.get(name)
    
    def list_suites(self) -> List[str]:
        """列出所有测试套件名称"""
        return list(self._test_suites.keys())
    
    # === 测试用例管理 ===
    
    def start_test(self, name: str, test_data: Optional[Dict[str, Any]] = None) -> TestResult:
        """开始测试用例"""
        with self._lock:
            # 结束当前测试（如果存在）
            if self._current_test:
                self.end_test()
            
            # 确保有活动的测试套件
            if not self._current_suite:
                self.start_suite("Default Suite")
            
            test = TestResult(
                name=name,
                status="running",
                start_time=datetime.now(),
                test_data=test_data or {},
                metadata={}
            )
            
            self._current_test = test
            self._current_suite.tests.append(test)
            
            self.logger.debug(f"Started test: {name}")
            self._trigger_callback('test_started', test)
            
            return test
    
    def end_test(self, status: Optional[str] = None) -> Optional[TestResult]:
        """结束当前测试用例"""
        with self._lock:
            if not self._current_test:
                return None
            
            test = self._current_test
            test.end_time = datetime.now()
            
            if test.start_time:
                test.duration = (test.end_time - test.start_time).total_seconds()
            
            # 设置状态
            if status:
                test.status = status
            elif test.status == "running":
                test.status = "passed"  # 默认为通过
            
            self.logger.debug(f"Ended test: {test.name} ({test.status}, {test.duration:.3f}s)")
            self._trigger_callback('test_completed', test)
            self._current_test = None
            
            return test
    
    def pass_test(self, message: Optional[str] = None):
        """标记当前测试为通过"""
        if self._current_test:
            self._current_test.status = "passed"
            if message:
                self._current_test.metadata['pass_message'] = message
    
    def fail_test(self, message: str, traceback: Optional[str] = None):
        """标记当前测试为失败"""
        if self._current_test:
            self._current_test.status = "failed"
            self._current_test.error_message = message
            self._current_test.error_traceback = traceback
            
            # 自动截图
            if self._auto_screenshot:
                self._take_screenshot_if_possible()
    
    def skip_test(self, reason: str):
        """跳过当前测试"""
        if self._current_test:
            self._current_test.status = "skipped"
            self._current_test.metadata['skip_reason'] = reason
    
    def error_test(self, message: str, traceback: Optional[str] = None):
        """标记当前测试为错误"""
        if self._current_test:
            self._current_test.status = "error"
            self._current_test.error_message = message
            self._current_test.error_traceback = traceback
            
            # 自动截图
            if self._auto_screenshot:
                self._take_screenshot_if_possible()
    
    # === 数据收集方法 ===
    
    def add_screenshot(self, screenshot_path: str):
        """添加截图到当前测试"""
        if self._current_test:
            self._current_test.screenshots.append(screenshot_path)
            self.logger.debug(f"Added screenshot: {screenshot_path}")
    
    def add_log(self, message: str):
        """添加日志到当前测试"""
        if self._current_test and self._collect_logs:
            self._current_test.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
            
            # 限制日志条目数量
            if len(self._current_test.logs) > self._max_log_entries:
                self._current_test.logs = self._current_test.logs[-self._max_log_entries:]
    
    def add_test_data(self, key: str, value: Any):
        """添加测试数据"""
        if self._current_test:
            self._current_test.test_data[key] = value
    
    def add_metadata(self, key: str, value: Any):
        """添加元数据"""
        if self._current_test:
            self._current_test.metadata[key] = value
    
    def _take_screenshot_if_possible(self):
        """尝试自动截图"""
        try:
            # 这里可以集成WebDriver截图功能
            from ..web.driver_manager import get_driver_manager
            
            driver_manager = get_driver_manager()
            drivers = driver_manager.list_drivers()
            
            if drivers:
                # 使用第一个可用的驱动进行截图
                driver_name = drivers[0]
                driver = driver_manager.get_driver(driver_name)
                
                if driver and hasattr(driver, 'get_screenshot_as_file'):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                    screenshot_path = f"screenshots/test_failure_{timestamp}.png"
                    
                    Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
                    driver.get_screenshot_as_file(screenshot_path)
                    self.add_screenshot(screenshot_path)
                    
        except Exception as e:
            self.logger.debug(f"Failed to take automatic screenshot: {e}")
    
    # === 报告生成 ===
    
    def generate_report(self, 
                       include_running: bool = False,
                       environment_info: Optional[Dict[str, Any]] = None,
                       config_info: Optional[Dict[str, Any]] = None) -> TestReport:
        """生成完整的测试报告"""
        with self._lock:
            # 复制套件数据
            suites = []
            total_tests = 0
            passed_tests = 0
            failed_tests = 0
            skipped_tests = 0
            error_tests = 0
            total_duration = 0.0
            earliest_start = None
            latest_end = None
            
            for suite in self._test_suites.values():
                # 过滤正在运行的测试
                if not include_running:
                    suite_tests = [t for t in suite.tests if t.status != "running"]
                else:
                    suite_tests = suite.tests[:]
                
                if suite_tests:
                    suite_copy = TestSuite(
                        name=suite.name,
                        tests=suite_tests,
                        start_time=suite.start_time,
                        end_time=suite.end_time,
                        duration=suite.duration,
                        setup_duration=suite.setup_duration,
                        teardown_duration=suite.teardown_duration,
                        metadata=suite.metadata.copy()
                    )
                    suites.append(suite_copy)
                    
                    # 累计统计
                    total_tests += suite_copy.total_tests
                    passed_tests += suite_copy.passed_tests
                    failed_tests += suite_copy.failed_tests
                    skipped_tests += suite_copy.skipped_tests
                    error_tests += suite_copy.error_tests
                    total_duration += suite_copy.duration
                    
                    # 时间范围
                    if suite.start_time:
                        if earliest_start is None or suite.start_time < earliest_start:
                            earliest_start = suite.start_time
                    
                    if suite.end_time:
                        if latest_end is None or suite.end_time > latest_end:
                            latest_end = suite.end_time
            
            # 创建摘要
            summary = ReportSummary(
                total_suites=len(suites),
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                skipped_tests=skipped_tests,
                error_tests=error_tests,
                total_duration=total_duration,
                start_time=earliest_start,
                end_time=latest_end,
                environment=environment_info or {},
                config=config_info or {}
            )
            
            # 创建报告
            report = TestReport(
                summary=summary,
                suites=suites,
                metadata={
                    'collector_version': '1.0.0',
                    'collection_time': datetime.now(),
                    'auto_screenshot': self._auto_screenshot,
                    'collect_logs': self._collect_logs,
                    'collect_metrics': self._collect_metrics
                }
            )
            
            self._trigger_callback('report_generated', report)
            return report
    
    def clear_data(self):
        """清空收集的数据"""
        with self._lock:
            self._test_suites.clear()
            self._current_suite = None
            self._current_test = None
            self.logger.info("Report collector data cleared")
    
    # === 上下文管理器 ===
    
    @contextmanager
    def test_context(self, name: str, test_data: Optional[Dict[str, Any]] = None):
        """测试上下文管理器"""
        test = self.start_test(name, test_data)
        try:
            yield test
            if test.status == "running":
                self.pass_test()
        except Exception as e:
            self.fail_test(str(e))
            raise
        finally:
            self.end_test()
    
    @contextmanager
    def suite_context(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """测试套件上下文管理器"""
        suite = self.start_suite(name, metadata)
        try:
            yield suite
        finally:
            self.end_suite()


# 全局报告收集器
_global_collector: Optional[ReportCollector] = None
_collector_lock = threading.Lock()


def get_report_collector() -> ReportCollector:
    """获取全局报告收集器"""
    global _global_collector
    if _global_collector is None:
        with _collector_lock:
            if _global_collector is None:
                _global_collector = ReportCollector()
    return _global_collector


def set_report_collector(collector: ReportCollector):
    """设置全局报告收集器"""
    global _global_collector
    with _collector_lock:
        _global_collector = collector


# 便捷函数
def start_test_suite(name: str, metadata: Optional[Dict[str, Any]] = None) -> TestSuite:
    """开始测试套件的便捷函数"""
    collector = get_report_collector()
    return collector.start_suite(name, metadata)


def end_test_suite() -> Optional[TestSuite]:
    """结束测试套件的便捷函数"""
    collector = get_report_collector()
    return collector.end_suite()


def start_test(name: str, test_data: Optional[Dict[str, Any]] = None) -> TestResult:
    """开始测试的便捷函数"""
    collector = get_report_collector()
    return collector.start_test(name, test_data)


def end_test(status: Optional[str] = None) -> Optional[TestResult]:
    """结束测试的便捷函数"""
    collector = get_report_collector()
    return collector.end_test(status)


def test_context(name: str, test_data: Optional[Dict[str, Any]] = None):
    """测试上下文的便捷函数"""
    collector = get_report_collector()
    return collector.test_context(name, test_data)


def suite_context(name: str, metadata: Optional[Dict[str, Any]] = None):
    """测试套件上下文的便捷函数"""
    collector = get_report_collector()
    return collector.suite_context(name, metadata)