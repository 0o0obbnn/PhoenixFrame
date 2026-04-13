"""高级性能监控系统

提供深度性能分析和监控功能，包括：
- 实时性能指标收集和分析
- 内存使用和泄漏检测
- CPU性能瓶颈分析
- 网络和磁盘IO监控
- 自动性能报告生成
- 性能趋势分析和预警
"""

import gc
import os
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple
import json
import statistics
import psutil

from .metrics import get_metrics_collector, MetricsCollector
from ..observability.logger import get_logger


@dataclass
class PerformanceSnapshot:
    """性能快照数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    thread_count: int
    process_count: int
    load_average: Optional[Tuple[float, float, float]] = None
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class MemoryProfile:
    """内存分析结果"""
    current_usage_mb: float
    peak_usage_mb: float
    objects_count: Dict[str, int]
    top_allocations: List[Tuple[str, int, str]]  # (filename, lineno, trace)
    memory_growth_rate_mb_per_min: float
    potential_leaks: List[str]


@dataclass
class CPUProfile:
    """CPU分析结果"""
    avg_usage_percent: float
    peak_usage_percent: float
    usage_distribution: Dict[str, float]  # 时间段分布
    top_processes: List[Tuple[str, float]]  # (process_name, cpu_percent)
    bottleneck_indicators: List[str]


@dataclass
class PerformanceAlert:
    """性能告警"""
    timestamp: datetime
    severity: str  # 'low', 'medium', 'high', 'critical'
    category: str  # 'memory', 'cpu', 'disk', 'network', 'custom'
    message: str
    current_value: float
    threshold_value: float
    recommended_action: str


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, 
                 sample_interval: float = 1.0,
                 history_size: int = 1000,
                 enable_memory_tracing: bool = True):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.sample_interval = sample_interval
        self.history_size = history_size
        self.enable_memory_tracing = enable_memory_tracing
        
        # 性能数据存储
        self.snapshots: deque = deque(maxlen=history_size)
        self.alerts: deque = deque(maxlen=100)
        
        # 监控状态
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # 告警阈值
        self.thresholds = {
            'cpu_percent': 85.0,
            'memory_percent': 90.0,
            'disk_usage_percent': 95.0,
            'memory_growth_rate': 50.0,  # MB/min
            'response_time_degradation': 100.0,  # 响应时间增长百分比
            'error_rate': 10.0  # 错误率百分比
        }
        
        # 性能基线
        self.baseline: Optional[Dict[str, float]] = None
        
        # 内存追踪
        if enable_memory_tracing:
            tracemalloc.start()
        
        # 集成现有指标系统
        self.metrics_collector = get_metrics_collector()
    
    def set_thresholds(self, **thresholds):
        """设置告警阈值"""
        self.thresholds.update(thresholds)
        self.logger.info(f"Updated performance thresholds: {thresholds}")
    
    def start_monitoring(self):
        """开始性能监控"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """停止性能监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self._monitoring:
            try:
                snapshot = self._capture_snapshot()
                
                with self._lock:
                    self.snapshots.append(snapshot)
                
                # 检查告警条件
                alerts = self._check_alerts(snapshot)
                for alert in alerts:
                    self._trigger_alert(alert)
                
                time.sleep(self.sample_interval)
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")
                time.sleep(self.sample_interval)
    
    def _capture_snapshot(self) -> PerformanceSnapshot:
        """捕获性能快照"""
        # 系统指标
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        # 进程和线程信息
        current_process = psutil.Process()
        thread_count = current_process.num_threads()
        process_count = len(psutil.pids())
        
        # 负载平均值（仅Unix系统）
        load_avg = None
        try:
            load_avg = os.getloadavg()
        except (AttributeError, OSError):
            pass  # Windows系统不支持
        
        # 自定义指标
        custom_metrics = {}
        metrics_summary = self.metrics_collector.get_summary()
        
        # 添加测试相关指标
        test_metrics = metrics_summary.get('test_metrics', {})
        if test_metrics.get('test_count', 0) > 0:
            custom_metrics['test_pass_rate'] = (
                test_metrics.get('test_passed', 0) / test_metrics['test_count'] * 100
            )
            
            if test_metrics.get('test_duration_samples'):
                durations = list(test_metrics['test_duration_samples'])
                custom_metrics['avg_test_duration'] = statistics.mean(durations)
                custom_metrics['test_duration_p95'] = statistics.quantiles(durations, n=20)[18]  # 95th percentile
        
        # 添加API相关指标
        api_metrics = metrics_summary.get('api_metrics', {})
        if api_metrics.get('api_request_count', 0) > 0:
            custom_metrics['api_error_rate'] = (
                api_metrics.get('api_error_count', 0) / api_metrics['api_request_count'] * 100
            )
            
            if api_metrics.get('api_request_duration_samples'):
                durations = list(api_metrics['api_request_duration_samples'])
                custom_metrics['avg_api_response_time'] = statistics.mean(durations)
        
        return PerformanceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            memory_available_mb=memory.available / 1024 / 1024,
            disk_usage_percent=(disk.used / disk.total) * 100,
            network_bytes_sent=net_io.bytes_sent,
            network_bytes_recv=net_io.bytes_recv,
            thread_count=thread_count,
            process_count=process_count,
            load_average=load_avg,
            custom_metrics=custom_metrics
        )
    
    def _check_alerts(self, snapshot: PerformanceSnapshot) -> List[PerformanceAlert]:
        """检查告警条件"""
        alerts = []
        
        # CPU告警
        if snapshot.cpu_percent > self.thresholds['cpu_percent']:
            alerts.append(PerformanceAlert(
                timestamp=snapshot.timestamp,
                severity='high' if snapshot.cpu_percent > 95 else 'medium',
                category='cpu',
                message=f"High CPU usage detected: {snapshot.cpu_percent:.1f}%",
                current_value=snapshot.cpu_percent,
                threshold_value=self.thresholds['cpu_percent'],
                recommended_action="Check for CPU-intensive processes and consider optimization"
            ))
        
        # 内存告警
        if snapshot.memory_percent > self.thresholds['memory_percent']:
            alerts.append(PerformanceAlert(
                timestamp=snapshot.timestamp,
                severity='critical' if snapshot.memory_percent > 95 else 'high',
                category='memory',
                message=f"High memory usage detected: {snapshot.memory_percent:.1f}%",
                current_value=snapshot.memory_percent,
                threshold_value=self.thresholds['memory_percent'],
                recommended_action="Check for memory leaks and optimize memory usage"
            ))
        
        # 磁盘告警
        if snapshot.disk_usage_percent > self.thresholds['disk_usage_percent']:
            alerts.append(PerformanceAlert(
                timestamp=snapshot.timestamp,
                severity='critical',
                category='disk',
                message=f"High disk usage detected: {snapshot.disk_usage_percent:.1f}%",
                current_value=snapshot.disk_usage_percent,
                threshold_value=self.thresholds['disk_usage_percent'],
                recommended_action="Clean up disk space or increase storage capacity"
            ))
        
        # 内存增长率告警
        memory_growth_rate = self._calculate_memory_growth_rate()
        if memory_growth_rate and memory_growth_rate > self.thresholds['memory_growth_rate']:
            alerts.append(PerformanceAlert(
                timestamp=snapshot.timestamp,
                severity='medium',
                category='memory',
                message=f"High memory growth rate detected: {memory_growth_rate:.1f} MB/min",
                current_value=memory_growth_rate,
                threshold_value=self.thresholds['memory_growth_rate'],
                recommended_action="Investigate potential memory leaks"
            ))
        
        # 自定义指标告警
        test_pass_rate = snapshot.custom_metrics.get('test_pass_rate')
        if test_pass_rate is not None and test_pass_rate < 95.0:
            alerts.append(PerformanceAlert(
                timestamp=snapshot.timestamp,
                severity='medium',
                category='custom',
                message=f"Low test pass rate detected: {test_pass_rate:.1f}%",
                current_value=test_pass_rate,
                threshold_value=95.0,
                recommended_action="Review failed tests and fix issues"
            ))
        
        api_error_rate = snapshot.custom_metrics.get('api_error_rate')
        if api_error_rate is not None and api_error_rate > self.thresholds['error_rate']:
            alerts.append(PerformanceAlert(
                timestamp=snapshot.timestamp,
                severity='high',
                category='custom',
                message=f"High API error rate detected: {api_error_rate:.1f}%",
                current_value=api_error_rate,
                threshold_value=self.thresholds['error_rate'],
                recommended_action="Check API endpoints and fix errors"
            ))
        
        return alerts
    
    def _calculate_memory_growth_rate(self) -> Optional[float]:
        """计算内存增长率（MB/分钟）"""
        if len(self.snapshots) < 10:  # 需要足够的数据点
            return None
        
        recent_snapshots = list(self.snapshots)[-60:]  # 最近60个快照
        if len(recent_snapshots) < 2:
            return None
        
        # 计算时间跨度（分钟）
        time_span = (recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp).total_seconds() / 60
        if time_span <= 0:
            return None
        
        # 计算内存增长
        memory_growth = recent_snapshots[-1].memory_used_mb - recent_snapshots[0].memory_used_mb
        
        return memory_growth / time_span
    
    def _trigger_alert(self, alert: PerformanceAlert):
        """触发告警"""
        with self._lock:
            self.alerts.append(alert)
        
        # 记录告警日志
        level_map = {
            'low': 'debug',
            'medium': 'warning', 
            'high': 'error',
            'critical': 'critical'
        }
        
        log_level = level_map.get(alert.severity, 'info')
        getattr(self.logger, log_level)(
            f"Performance Alert [{alert.severity.upper()}]: {alert.message}"
        )
        
        # 记录到指标系统
        self.metrics_collector.record_metric(
            "performance_alert", 1, "count",
            {
                "severity": alert.severity,
                "category": alert.category
            }
        )
    
    def analyze_memory_usage(self) -> MemoryProfile:
        """分析内存使用情况"""
        if not self.enable_memory_tracing:
            self.logger.warning("Memory tracing is not enabled")
            return MemoryProfile(0, 0, {}, [], 0, [])
        
        # 获取当前内存统计
        current, peak = tracemalloc.get_traced_memory()
        current_mb = current / 1024 / 1024
        peak_mb = peak / 1024 / 1024
        
        # 获取对象统计
        objects_count = {}
        for obj_type in [list, dict, set, tuple, str]:
            objects_count[obj_type.__name__] = len(gc.get_objects())
        
        # 获取顶级内存分配
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        top_allocations = []
        for stat in top_stats[:10]:
            top_allocations.append((
                stat.traceback.format()[0] if stat.traceback.format() else "unknown",
                stat.size,
                str(stat.traceback)
            ))
        
        # 计算内存增长率
        memory_growth_rate = self._calculate_memory_growth_rate() or 0
        
        # 检测潜在内存泄漏
        potential_leaks = []
        if memory_growth_rate > 10:  # MB/min
            potential_leaks.append(f"Continuous memory growth: {memory_growth_rate:.1f} MB/min")
        
        # 检查大对象
        if len(top_allocations) > 0 and top_allocations[0][1] > 100 * 1024 * 1024:  # > 100MB
            potential_leaks.append("Large memory allocation detected")
        
        return MemoryProfile(
            current_usage_mb=current_mb,
            peak_usage_mb=peak_mb,
            objects_count=objects_count,
            top_allocations=top_allocations,
            memory_growth_rate_mb_per_min=memory_growth_rate,
            potential_leaks=potential_leaks
        )
    
    def analyze_cpu_usage(self, time_window_minutes: int = 10) -> CPUProfile:
        """分析CPU使用情况"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        recent_snapshots = [
            s for s in self.snapshots 
            if s.timestamp >= cutoff_time
        ]
        
        if not recent_snapshots:
            return CPUProfile(0, 0, {}, [], [])
        
        # 计算CPU统计
        cpu_values = [s.cpu_percent for s in recent_snapshots]
        avg_usage = statistics.mean(cpu_values)
        peak_usage = max(cpu_values)
        
        # CPU使用分布
        usage_distribution = {
            'low (0-25%)': len([v for v in cpu_values if v <= 25]) / len(cpu_values) * 100,
            'medium (25-50%)': len([v for v in cpu_values if 25 < v <= 50]) / len(cpu_values) * 100,
            'high (50-75%)': len([v for v in cpu_values if 50 < v <= 75]) / len(cpu_values) * 100,
            'critical (75-100%)': len([v for v in cpu_values if v > 75]) / len(cpu_values) * 100
        }
        
        # 获取占用CPU最多的进程
        top_processes = []
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                proc.info['cpu_percent'] = proc.cpu_percent()
                processes.append(proc.info)
            
            # 按CPU使用率排序
            processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            top_processes = [(p['name'], p['cpu_percent'] or 0) for p in processes[:5]]
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # 瓶颈指标
        bottleneck_indicators = []
        if peak_usage > 90:
            bottleneck_indicators.append("CPU utilization consistently high")
        if usage_distribution['critical (75-100%)'] > 50:
            bottleneck_indicators.append("More than 50% of time in critical CPU usage")
        if len(recent_snapshots) > 0 and recent_snapshots[-1].load_average:
            load_avg = recent_snapshots[-1].load_average[0]  # 1分钟负载
            cpu_count = psutil.cpu_count()
            if load_avg > cpu_count * 0.8:
                bottleneck_indicators.append(f"High load average: {load_avg:.2f}")
        
        return CPUProfile(
            avg_usage_percent=avg_usage,
            peak_usage_percent=peak_usage,
            usage_distribution=usage_distribution,
            top_processes=top_processes,
            bottleneck_indicators=bottleneck_indicators
        )
    
    def establish_baseline(self, duration_minutes: int = 5):
        """建立性能基线"""
        self.logger.info(f"Establishing performance baseline over {duration_minutes} minutes...")
        
        baseline_snapshots = []
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < duration_minutes * 60:
            snapshot = self._capture_snapshot()
            baseline_snapshots.append(snapshot)
            time.sleep(self.sample_interval)
        
        if not baseline_snapshots:
            self.logger.warning("No baseline snapshots captured")
            return
        
        # 计算基线指标
        self.baseline = {
            'cpu_percent_avg': statistics.mean([s.cpu_percent for s in baseline_snapshots]),
            'cpu_percent_p95': statistics.quantiles([s.cpu_percent for s in baseline_snapshots], n=20)[18],
            'memory_percent_avg': statistics.mean([s.memory_percent for s in baseline_snapshots]),
            'memory_used_mb_avg': statistics.mean([s.memory_used_mb for s in baseline_snapshots]),
            'response_time_avg': statistics.mean([
                s.custom_metrics.get('avg_test_duration', 0) for s in baseline_snapshots
                if s.custom_metrics.get('avg_test_duration', 0) > 0
            ]) or 0
        }
        
        self.logger.info(f"Baseline established: {self.baseline}")
    
    def detect_performance_regression(self) -> List[str]:
        """检测性能回归"""
        if not self.baseline:
            return ["No baseline established for comparison"]
        
        if len(self.snapshots) < 10:
            return ["Insufficient data for regression analysis"]
        
        regressions = []
        recent_snapshots = list(self.snapshots)[-60:]  # 最近60个快照
        
        # CPU回归
        recent_cpu = statistics.mean([s.cpu_percent for s in recent_snapshots])
        if recent_cpu > self.baseline['cpu_percent_avg'] * 1.2:  # 20%增长
            regressions.append(
                f"CPU usage regression: {recent_cpu:.1f}% vs baseline {self.baseline['cpu_percent_avg']:.1f}%"
            )
        
        # 内存回归
        recent_memory = statistics.mean([s.memory_used_mb for s in recent_snapshots])
        if recent_memory > self.baseline['memory_used_mb_avg'] * 1.15:  # 15%增长
            regressions.append(
                f"Memory usage regression: {recent_memory:.1f}MB vs baseline {self.baseline['memory_used_mb_avg']:.1f}MB"
            )
        
        # 响应时间回归
        recent_response_times = [
            s.custom_metrics.get('avg_test_duration', 0) for s in recent_snapshots
            if s.custom_metrics.get('avg_test_duration', 0) > 0
        ]
        
        if recent_response_times and self.baseline['response_time_avg'] > 0:
            recent_response_time = statistics.mean(recent_response_times)
            if recent_response_time > self.baseline['response_time_avg'] * 1.5:  # 50%增长
                regressions.append(
                    f"Response time regression: {recent_response_time:.3f}s vs baseline {self.baseline['response_time_avg']:.3f}s"
                )
        
        return regressions
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.snapshots:
            return {"status": "No performance data available"}
        
        latest_snapshot = self.snapshots[-1]
        
        # 内存分析
        memory_profile = self.analyze_memory_usage()
        
        # CPU分析
        cpu_profile = self.analyze_cpu_usage()
        
        # 性能回归检测
        regressions = self.detect_performance_regression()
        
        # 活跃告警
        active_alerts = [
            {
                "timestamp": alert.timestamp.isoformat(),
                "severity": alert.severity,
                "category": alert.category,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold": alert.threshold_value
            }
            for alert in list(self.alerts)[-10:]  # 最近10个告警
        ]
        
        return {
            "timestamp": latest_snapshot.timestamp.isoformat(),
            "current_status": {
                "cpu_percent": latest_snapshot.cpu_percent,
                "memory_percent": latest_snapshot.memory_percent,
                "memory_used_mb": latest_snapshot.memory_used_mb,
                "disk_usage_percent": latest_snapshot.disk_usage_percent,
                "thread_count": latest_snapshot.thread_count,
                "custom_metrics": latest_snapshot.custom_metrics
            },
            "memory_profile": {
                "current_usage_mb": memory_profile.current_usage_mb,
                "peak_usage_mb": memory_profile.peak_usage_mb,
                "growth_rate_mb_per_min": memory_profile.memory_growth_rate_mb_per_min,
                "potential_leaks": memory_profile.potential_leaks
            },
            "cpu_profile": {
                "avg_usage_percent": cpu_profile.avg_usage_percent,
                "peak_usage_percent": cpu_profile.peak_usage_percent,
                "usage_distribution": cpu_profile.usage_distribution,
                "bottleneck_indicators": cpu_profile.bottleneck_indicators
            },
            "performance_regressions": regressions,
            "active_alerts": active_alerts,
            "monitoring_stats": {
                "total_snapshots": len(self.snapshots),
                "monitoring_duration_minutes": (
                    (latest_snapshot.timestamp - self.snapshots[0].timestamp).total_seconds() / 60
                    if len(self.snapshots) > 1 else 0
                ),
                "sample_interval": self.sample_interval
            }
        }
    
    def export_performance_report(self, file_path: str):
        """导出性能报告"""
        report_data = {
            "report_timestamp": datetime.now().isoformat(),
            "performance_summary": self.get_performance_summary(),
            "baseline": self.baseline,
            "thresholds": self.thresholds,
            "raw_snapshots": [
                {
                    "timestamp": s.timestamp.isoformat(),
                    "cpu_percent": s.cpu_percent,
                    "memory_percent": s.memory_percent,
                    "memory_used_mb": s.memory_used_mb,
                    "disk_usage_percent": s.disk_usage_percent,
                    "custom_metrics": s.custom_metrics
                }
                for s in list(self.snapshots)[-100:]  # 最近100个快照
            ]
        }
        
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Performance report exported to: {file_path}")


class PerformanceProfiler:
    """性能分析器 - 用于代码级性能分析"""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.profiles: Dict[str, List[float]] = defaultdict(list)
        self._active_timers: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def start_timer(self, name: str):
        """开始计时"""
        with self._lock:
            self._active_timers[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        """结束计时并返回耗时"""
        with self._lock:
            if name in self._active_timers:
                duration = time.time() - self._active_timers.pop(name)
                self.profiles[name].append(duration)
                return duration
            return 0.0
    
    def profile_function(self, func_name: str):
        """函数装饰器用于性能分析"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                self.start_timer(func_name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = self.end_timer(func_name)
                    self.logger.debug(f"Function {func_name} took {duration:.4f}s")
            return wrapper
        return decorator
    
    def get_profile_summary(self) -> Dict[str, Dict[str, float]]:
        """获取性能分析摘要"""
        summary = {}
        
        with self._lock:
            for name, durations in self.profiles.items():
                if durations:
                    summary[name] = {
                        'count': len(durations),
                        'total_time': sum(durations),
                        'avg_time': statistics.mean(durations),
                        'min_time': min(durations),
                        'max_time': max(durations),
                        'p95_time': statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations)
                    }
        
        return summary
    
    def clear_profiles(self):
        """清除分析数据"""
        with self._lock:
            self.profiles.clear()
            self._active_timers.clear()


# 全局实例
_performance_analyzer: Optional[PerformanceAnalyzer] = None
_performance_profiler: Optional[PerformanceProfiler] = None


def get_performance_analyzer() -> PerformanceAnalyzer:
    """获取性能分析器实例"""
    global _performance_analyzer
    if _performance_analyzer is None:
        _performance_analyzer = PerformanceAnalyzer()
    return _performance_analyzer


def get_performance_profiler() -> PerformanceProfiler:
    """获取性能分析器实例"""
    global _performance_profiler
    if _performance_profiler is None:
        _performance_profiler = PerformanceProfiler()
    return _performance_profiler


def start_performance_monitoring(sample_interval: float = 1.0, **thresholds):
    """开始性能监控"""
    analyzer = get_performance_analyzer()
    analyzer.sample_interval = sample_interval
    if thresholds:
        analyzer.set_thresholds(**thresholds)
    analyzer.start_monitoring()


def stop_performance_monitoring():
    """停止性能监控"""
    analyzer = get_performance_analyzer()
    analyzer.stop_monitoring()


def get_performance_summary() -> Dict[str, Any]:
    """获取性能摘要"""
    analyzer = get_performance_analyzer()
    return analyzer.get_performance_summary()


def export_performance_report(file_path: str):
    """导出性能报告"""
    analyzer = get_performance_analyzer()
    analyzer.export_performance_report(file_path)


def profile_function(name: str):
    """性能分析装饰器"""
    profiler = get_performance_profiler()
    return profiler.profile_function(name)