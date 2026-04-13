"""度量收集系统"""
import time
import psutil
import threading
import uuid
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timezone
from enum import Enum
from contextlib import contextmanager
import json
import os
import statistics

try:
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.resources import Resource
    OPENTELEMETRY_METRICS_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_METRICS_AVAILABLE = False
    metrics = None

try:
    import prometheus_client
    from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    prometheus_client = None


class MetricType(Enum):
    """度量类型枚举"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


class MetricUnit(Enum):
    """度量单位枚举"""
    NONE = ""
    SECONDS = "s"
    MILLISECONDS = "ms"
    MICROSECONDS = "us"
    NANOSECONDS = "ns"
    BYTES = "bytes"
    KILOBYTES = "kb"
    MEGABYTES = "mb"
    GIGABYTES = "gb"
    PERCENT = "%"
    COUNT = "count"
    REQUESTS_PER_SECOND = "req/s"
    OPERATIONS_PER_SECOND = "ops/s"


@dataclass
class MetricPoint:
    """度量数据点"""
    name: str
    value: float
    metric_type: MetricType = MetricType.GAUGE
    unit: MetricUnit = MetricUnit.NONE
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "unit": self.unit.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
            "description": self.description
        }


@dataclass
class MetricSummary:
    """度量汇总统计"""
    name: str
    count: int = 0
    sum: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    mean: float = 0.0
    median: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    
    def add_value(self, value: float):
        """添加数值"""
        self.count += 1
        self.sum += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.mean = self.sum / self.count
    
    def calculate_percentiles(self, values: List[float]):
        """计算百分位数"""
        if values:
            sorted_values = sorted(values)
            self.median = statistics.median(sorted_values)
            if len(sorted_values) >= 20:  # 至少20个数据点才计算百分位
                self.p95 = statistics.quantiles(sorted_values, n=20)[18]  # 95th percentile
                self.p99 = statistics.quantiles(sorted_values, n=100)[98]  # 99th percentile


class MetricsCollector:
    """增强的度量收集器"""
    
    def __init__(self, collection_interval: float = 10.0, max_buffer_size: int = 10000):
        self.collection_interval = collection_interval
        self.max_buffer_size = max_buffer_size
        self.metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_buffer_size))
        self.metric_summaries: Dict[str, MetricSummary] = {}
        self.collectors: List[Callable] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()
        
        # 计数器和累计器
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # 测试度量
        self.test_metrics = {
            "test_count": 0,
            "test_passed": 0,
            "test_failed": 0,
            "test_skipped": 0,
            "test_duration_total": 0.0,
            "test_duration_min": float('inf'),
            "test_duration_max": 0.0,
            "test_duration_samples": deque(maxlen=100)
        }
        
        # API度量
        self.api_metrics = {
            "api_request_count": 0,
            "api_request_duration_total": 0.0,
            "api_request_duration_min": float('inf'),
            "api_request_duration_max": 0.0,
            "api_request_duration_samples": deque(maxlen=100),
            "api_response_codes": defaultdict(int),
            "api_error_count": 0
        }
        
        # Web度量
        self.web_metrics = {
            "web_action_count": 0,
            "web_action_duration_total": 0.0,
            "web_action_duration_min": float('inf'),
            "web_action_duration_max": 0.0,
            "web_action_duration_samples": deque(maxlen=100),
            "web_action_types": defaultdict(int),
            "web_error_count": 0
        }
        
        # 自动添加系统度量收集器
        self.add_collector(self._collect_system_metrics)
        
    def add_collector(self, collector: Callable):
        """添加度量收集器"""
        with self.lock:
            self.collectors.append(collector)
    
    def remove_collector(self, collector: Callable):
        """移除度量收集器"""
        with self.lock:
            if collector in self.collectors:
                self.collectors.remove(collector)
    
    def record_metric(self, metric_point: MetricPoint):
        """记录单个度量点"""
        with self.lock:
            # 添加到缓冲区
            self.metrics_buffer[metric_point.name].append(metric_point)
            
            # 更新汇总统计
            if metric_point.name not in self.metric_summaries:
                self.metric_summaries[metric_point.name] = MetricSummary(metric_point.name)
            
            summary = self.metric_summaries[metric_point.name]
            summary.add_value(metric_point.value)
            
            # 根据度量类型更新相应的存储
            if metric_point.metric_type == MetricType.COUNTER:
                self._counters[metric_point.name] += metric_point.value
            elif metric_point.metric_type == MetricType.GAUGE:
                self._gauges[metric_point.name] = metric_point.value
            elif metric_point.metric_type in (MetricType.HISTOGRAM, MetricType.TIMER):
                self._histograms[metric_point.name].append(metric_point.value)
                # 保持最近的1000个值
                if len(self._histograms[metric_point.name]) > 1000:
                    self._histograms[metric_point.name] = self._histograms[metric_point.name][-1000:]
    
    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None,
               description: str = ""):
        """记录计数器度量"""
        metric = MetricPoint(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            unit=MetricUnit.COUNT,
            labels=labels or {},
            description=description
        )
        self.record_metric(metric)
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None,
             unit: MetricUnit = MetricUnit.NONE, description: str = ""):
        """记录仪表度量"""
        metric = MetricPoint(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            unit=unit,
            labels=labels or {},
            description=description
        )
        self.record_metric(metric)
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None,
                 unit: MetricUnit = MetricUnit.NONE, description: str = ""):
        """记录直方图度量"""
        metric = MetricPoint(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            unit=unit,
            labels=labels or {},
            description=description
        )
        self.record_metric(metric)
    
    @contextmanager
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None,
             unit: MetricUnit = MetricUnit.MILLISECONDS, description: str = ""):
        """计时器上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            # 转换为指定单位
            if unit == MetricUnit.MILLISECONDS:
                duration *= 1000
            elif unit == MetricUnit.MICROSECONDS:
                duration *= 1000000
            elif unit == MetricUnit.NANOSECONDS:
                duration *= 1000000000
            
            metric = MetricPoint(
                name=name,
                value=duration,
                metric_type=MetricType.TIMER,
                unit=unit,
                labels=labels or {},
                description=description
            )
            self.record_metric(metric)
    
    def _collect_system_metrics(self):
        """收集系统度量"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.gauge("system_cpu_usage", cpu_percent, unit=MetricUnit.PERCENT)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            self.gauge("system_memory_usage", memory.percent, unit=MetricUnit.PERCENT)
            self.gauge("system_memory_used", memory.used, unit=MetricUnit.BYTES)
            self.gauge("system_memory_available", memory.available, unit=MetricUnit.BYTES)
            
            # 进程信息
            process = psutil.Process()
            process_memory = process.memory_info()
            self.gauge("process_memory_rss", process_memory.rss, unit=MetricUnit.BYTES)
            self.gauge("process_memory_vms", process_memory.vms, unit=MetricUnit.BYTES)
            
            # 线程数
            self.gauge("process_thread_count", process.num_threads(), unit=MetricUnit.COUNT)
            
            # 文件描述符（Linux/Unix）
            try:
                fd_count = process.num_fds()
                self.gauge("process_open_fds", fd_count, unit=MetricUnit.COUNT)
            except (AttributeError, OSError):
                # Windows不支持num_fds或权限不足
                pass
            
        except Exception as e:
            # 系统度量收集失败不应该影响其他功能
            pass
    
    def collect_all(self):
        """执行所有度量收集器"""
        with self.lock:
            for collector in self.collectors:
                try:
                    collector()
                except Exception as e:
                    # 记录错误但不中断收集过程
                    pass
    
    def record_test_start(self, test_name: str) -> None:
        """记录测试开始"""
        with self.lock:
            self.test_metrics["test_count"] += 1
            self.counter("test_started", 1.0, {"test_name": test_name})
    
    def record_test_end(self, test_name: str, outcome: str, duration: float) -> None:
        """记录测试结束"""
        with self.lock:
            # 更新测试结果统计
            if outcome == "passed":
                self.test_metrics["test_passed"] += 1
            elif outcome == "failed":
                self.test_metrics["test_failed"] += 1
            elif outcome == "skipped":
                self.test_metrics["test_skipped"] += 1
            
            # 更新持续时间统计
            self.test_metrics["test_duration_total"] += duration
            self.test_metrics["test_duration_min"] = min(self.test_metrics["test_duration_min"], duration)
            self.test_metrics["test_duration_max"] = max(self.test_metrics["test_duration_max"], duration)
            self.test_metrics["test_duration_samples"].append(duration)
            
            # 记录度量
            self.histogram("test_duration", duration, {"test_name": test_name, "outcome": outcome}, MetricUnit.SECONDS)
            self.counter("test_completed", 1.0, {"test_name": test_name, "outcome": outcome})
    
    def record_api_request(self, method: str, url: str, duration: float, status_code: int, 
                          error: Optional[str] = None) -> None:
        """记录API请求"""
        with self.lock:
            self.api_metrics["api_request_count"] += 1
            self.api_metrics["api_request_duration_total"] += duration
            self.api_metrics["api_request_duration_min"] = min(self.api_metrics["api_request_duration_min"], duration)
            self.api_metrics["api_request_duration_max"] = max(self.api_metrics["api_request_duration_max"], duration)
            self.api_metrics["api_request_duration_samples"].append(duration)
            self.api_metrics["api_response_codes"][status_code] += 1
            
            if error:
                self.api_metrics["api_error_count"] += 1
            
            # 记录度量
            labels = {"method": method, "status_code": str(status_code)}
            if error:
                labels["error"] = "true"
            
            self.histogram("api_request_duration", duration, labels, MetricUnit.SECONDS)
            self.counter("api_request_total", 1.0, labels)
    
    def record_web_action(self, action: str, duration: float, outcome: str, element: str = "") -> None:
        """记录Web操作"""
        with self.lock:
            self.web_metrics["web_action_count"] += 1
            self.web_metrics["web_action_duration_total"] += duration
            self.web_metrics["web_action_duration_min"] = min(self.web_metrics["web_action_duration_min"], duration)
            self.web_metrics["web_action_duration_max"] = max(self.web_metrics["web_action_duration_max"], duration)
            self.web_metrics["web_action_duration_samples"].append(duration)
            self.web_metrics["web_action_types"][action] += 1
            
            if outcome == "failed" or outcome == "error":
                self.web_metrics["web_error_count"] += 1
            
            # 记录度量
            labels = {"action": action, "outcome": outcome}
            if element:
                labels["element"] = element
            
            self.histogram("web_action_duration", duration, labels, MetricUnit.SECONDS)
            self.counter("web_action_total", 1.0, labels)
    
    def get_metric_summary(self, name: str) -> Optional[MetricSummary]:
        """获取度量汇总统计"""
        with self.lock:
            if name in self.metric_summaries:
                summary = self.metric_summaries[name]
                # 重新计算百分位数
                if name in self._histograms:
                    summary.calculate_percentiles(self._histograms[name])
                return summary
            return None
    
    def get_all_summaries(self) -> Dict[str, MetricSummary]:
        """获取所有度量汇总"""
        with self.lock:
            summaries = {}
            for name, summary in self.metric_summaries.items():
                if name in self._histograms:
                    summary.calculate_percentiles(self._histograms[name])
                summaries[name] = summary
            return summaries
    
    def get_current_values(self) -> Dict[str, Any]:
        """获取当前度量值"""
        with self.lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histogram_counts": {k: len(v) for k, v in self._histograms.items()}
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取度量摘要"""
        with self.lock:
            return {
                "test_metrics": dict(self.test_metrics),
                "api_metrics": dict(self.api_metrics),
                "web_metrics": dict(self.web_metrics),
                "collection_interval": self.collection_interval,
                "total_metric_types": len(self.metrics_buffer),
                "total_data_points": sum(len(values) for values in self.metrics_buffer.values())
            }
    
    def export_metrics(self, format_type: str = "json") -> str:
        """导出度量数据"""
        with self.lock:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summaries": {name: {
                    "count": summary.count,
                    "sum": summary.sum,
                    "min": summary.min if summary.min != float('inf') else None,
                    "max": summary.max if summary.max != float('-inf') else None,
                    "mean": summary.mean,
                    "median": summary.median,
                    "p95": summary.p95,
                    "p99": summary.p99
                } for name, summary in self.metric_summaries.items()},
                "current_values": self.get_current_values(),
                "summary": self.get_summary()
            }
            
            if format_type.lower() == "json":
                return json.dumps(data, indent=2, default=str)
            else:
                return str(data)
    
    def export_to_file(self, file_path: str) -> None:
        """导出度量到文件"""
        with self.lock:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": self.get_summary(),
                "metrics": {
                    name: [point.to_dict() for point in values]
                    for name, values in self.metrics_buffer.items()
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def clear_metrics(self):
        """清除所有度量数据"""
        with self.lock:
            self.metrics_buffer.clear()
            self.metric_summaries.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            
            # 重置内置统计
            self.test_metrics = {
                "test_count": 0,
                "test_passed": 0,
                "test_failed": 0,
                "test_skipped": 0,
                "test_duration_total": 0.0,
                "test_duration_min": float('inf'),
                "test_duration_max": 0.0,
                "test_duration_samples": deque(maxlen=100)
            }
            
            self.api_metrics = {
                "api_request_count": 0,
                "api_request_duration_total": 0.0,
                "api_request_duration_min": float('inf'),
                "api_request_duration_max": 0.0,
                "api_request_duration_samples": deque(maxlen=100),
                "api_response_codes": defaultdict(int),
                "api_error_count": 0
            }
            
            self.web_metrics = {
                "web_action_count": 0,
                "web_action_duration_total": 0.0,
                "web_action_duration_min": float('inf'),
                "web_action_duration_max": 0.0,
                "web_action_duration_samples": deque(maxlen=100),
                "web_action_types": defaultdict(int),
                "web_error_count": 0
            }
    
    def start_collection(self):
        """开始自动度量收集"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.thread.start()
    
    def stop_collection(self):
        """停止自动度量收集"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
    
    def _collection_loop(self):
        """度量收集循环"""
        while self.running:
            try:
                self.collect_all()
                time.sleep(self.collection_interval)
            except Exception as e:
                time.sleep(1)  # 出错时短暂休眠


class PrometheusMetricsCollector:
    """Prometheus兼容的度量收集器"""
    
    def __init__(self):
        self.metrics_collector = None
        self.meter_provider = None
        self.meter = None
        self.instruments = {}
        
    def setup(self, otlp_endpoint: Optional[str] = None, console_export: bool = False) -> None:
        """设置Prometheus度量收集"""
        if not OPENTELEMETRY_METRICS_AVAILABLE:
            print("Warning: OpenTelemetry metrics not available. Install with: pip install opentelemetry-sdk")
            return
        
        # 创建资源
        resource = Resource.create({
            "service.name": "phoenixframe",
            "service.version": "3.2.0",
        })
        
        # 创建导出器
        readers = []
        
        if otlp_endpoint:
            otlp_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
            readers.append(PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=10000))
        elif os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            otlp_exporter = OTLPMetricExporter()
            readers.append(PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=10000))
        
        if console_export or os.getenv("PHOENIX_METRICS_CONSOLE", "false").lower() == "true":
            console_exporter = ConsoleMetricExporter()
            readers.append(PeriodicExportingMetricReader(console_exporter, export_interval_millis=10000))
        
        # 创建MeterProvider
        self.meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(self.meter_provider)
        
        # 创建Meter
        self.meter = metrics.get_meter("phoenixframe")
        
        # 创建度量仪表
        self._create_instruments()
        
        print("Prometheus-compatible metrics collection initialized")
    
    def _create_instruments(self) -> None:
        """创建度量仪表"""
        if not self.meter:
            return
        
        # 计数器
        self.instruments["test_counter"] = self.meter.create_counter(
            "phoenixframe_test_total",
            description="Total number of tests",
            unit="1"
        )
        
        self.instruments["api_request_counter"] = self.meter.create_counter(
            "phoenixframe_api_request_total",
            description="Total number of API requests",
            unit="1"
        )
        
        self.instruments["web_action_counter"] = self.meter.create_counter(
            "phoenixframe_web_action_total",
            description="Total number of web actions",
            unit="1"
        )
        
        # 直方图
        self.instruments["test_duration_histogram"] = self.meter.create_histogram(
            "phoenixframe_test_duration_seconds",
            description="Test duration in seconds",
            unit="s"
        )
        
        self.instruments["api_duration_histogram"] = self.meter.create_histogram(
            "phoenixframe_api_request_duration_seconds",
            description="API request duration in seconds",
            unit="s"
        )
        
        self.instruments["web_action_duration_histogram"] = self.meter.create_histogram(
            "phoenixframe_web_action_duration_seconds",
            description="Web action duration in seconds",
            unit="s"
        )
        
        # 量表
        self.instruments["system_cpu_gauge"] = self.meter.create_gauge(
            "phoenixframe_system_cpu_percent",
            description="System CPU usage percentage",
            unit="%"
        )
        
        self.instruments["system_memory_gauge"] = self.meter.create_gauge(
            "phoenixframe_system_memory_percent",
            description="System memory usage percentage",
            unit="%"
        )
    
    def record_test_metric(self, outcome: str, duration: float, labels: Dict[str, str] = None) -> None:
        """记录测试度量"""
        if not self.instruments:
            return
        
        attributes = {"outcome": outcome}
        if labels:
            attributes.update(labels)
        
        self.instruments["test_counter"].add(1, attributes)
        self.instruments["test_duration_histogram"].record(duration, attributes)
    
    def record_api_metric(self, method: str, status_code: int, duration: float, labels: Dict[str, str] = None) -> None:
        """记录API度量"""
        if not self.instruments:
            return
        
        attributes = {"method": method, "status_code": str(status_code)}
        if labels:
            attributes.update(labels)
        
        self.instruments["api_request_counter"].add(1, attributes)
        self.instruments["api_duration_histogram"].record(duration, attributes)
    
    def record_web_metric(self, action: str, outcome: str, duration: float, labels: Dict[str, str] = None) -> None:
        """记录Web度量"""
        if not self.instruments:
            return
        
        attributes = {"action": action, "outcome": outcome}
        if labels:
            attributes.update(labels)
        
        self.instruments["web_action_counter"].add(1, attributes)
        self.instruments["web_action_duration_histogram"].record(duration, attributes)
    
    def record_system_metric(self, cpu_percent: float, memory_percent: float) -> None:
        """记录系统度量"""
        if not self.instruments:
            return
        
        self.instruments["system_cpu_gauge"].set(cpu_percent)
        self.instruments["system_memory_gauge"].set(memory_percent)
    
    def shutdown(self) -> None:
        """关闭度量收集"""
        if self.meter_provider:
            self.meter_provider.shutdown()


# 全局实例
_metrics_collector: Optional[MetricsCollector] = None
_prometheus_collector: Optional[PrometheusMetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取度量收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_prometheus_collector() -> PrometheusMetricsCollector:
    """获取Prometheus度量收集器实例"""
    global _prometheus_collector
    if _prometheus_collector is None:
        _prometheus_collector = PrometheusMetricsCollector()
    return _prometheus_collector


def setup_metrics(collection_interval: float = 10.0, 
                 otlp_endpoint: Optional[str] = None,
                 console_export: bool = False,
                 prometheus_export: bool = False) -> None:
    """设置度量收集"""
    # 设置基础度量收集器
    collector = get_metrics_collector()
    collector.collection_interval = collection_interval
    collector.start()
    
    # 设置Prometheus兼容收集器
    if prometheus_export:
        prometheus_collector = get_prometheus_collector()
        prometheus_collector.setup(otlp_endpoint, console_export)
    
    print(f"Metrics collection initialized with interval: {collection_interval}s")


def record_test_metric(test_name: str, outcome: str, duration: float, labels: Dict[str, str] = None) -> None:
    """记录测试度量"""
    collector = get_metrics_collector()
    collector.record_test_end(test_name, outcome, duration)
    
    # 同时记录到Prometheus
    prometheus_collector = get_prometheus_collector()
    prometheus_collector.record_test_metric(outcome, duration, labels)


def record_api_metric(method: str, url: str, status_code: int, duration: float, labels: Dict[str, str] = None) -> None:
    """记录API度量"""
    collector = get_metrics_collector()
    collector.record_api_request(method, url, duration, status_code)
    
    # 同时记录到Prometheus
    prometheus_collector = get_prometheus_collector()
    prometheus_collector.record_api_metric(method, status_code, duration, labels)


def record_web_metric(action: str, outcome: str, duration: float, labels: Dict[str, str] = None) -> None:
    """记录Web度量"""
    collector = get_metrics_collector()
    collector.record_web_action(action, duration, outcome)
    
    # 同时记录到Prometheus
    prometheus_collector = get_prometheus_collector()
    prometheus_collector.record_web_metric(action, outcome, duration, labels)


def get_metrics_summary() -> Dict[str, Any]:
    """获取度量摘要"""
    collector = get_metrics_collector()
    return collector.get_summary()


def export_metrics(file_path: str) -> None:
    """导出度量到文件"""
    collector = get_metrics_collector()
    collector.export_to_file(file_path)


def shutdown_metrics() -> None:
    """关闭度量收集"""
    global _metrics_collector, _prometheus_collector
    
    if _metrics_collector:
        _metrics_collector.stop()
    
    if _prometheus_collector:
        _prometheus_collector.shutdown()


# 兼容性别名，保持向后兼容
class MockMeter:
    """模拟度量器，当OpenTelemetry不可用时使用"""
    
    def create_counter(self, name: str, **kwargs):
        return MockCounter(name)
    
    def create_histogram(self, name: str, **kwargs):
        return MockHistogram(name)
    
    def create_gauge(self, name: str, **kwargs):
        return MockGauge(name)


class MockCounter:
    """模拟计数器"""
    
    def __init__(self, name: str):
        self.name = name
        self.value = 0
    
    def add(self, amount: float, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.value += amount


class MockHistogram:
    """模拟直方图"""
    
    def __init__(self, name: str):
        self.name = name
        self.values = []
    
    def record(self, amount: float, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.values.append(amount)


class MockGauge:
    """模拟仪表"""
    
    def __init__(self, name: str):
        self.name = name
        self.value = 0
    
    def set(self, amount: float, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.value = amount


class PhoenixMetrics:
    """PhoenixFrame度量收集器 - 兼容性包装"""
    
    def __init__(self, name: str):
        self.name = name
        self.collector = get_metrics_collector()
        
        if OPENTELEMETRY_METRICS_AVAILABLE:
            self.meter = metrics.get_meter(name)
        else:
            self.meter = MockMeter()
        
        # 创建常用度量
        self._test_counter = self.meter.create_counter(
            "test_cases_total",
            description="Total number of test cases executed"
        )
        
        self._test_duration = self.meter.create_histogram(
            "test_duration_seconds",
            description="Test case execution duration in seconds"
        )
        
        self._api_request_counter = self.meter.create_counter(
            "api_requests_total",
            description="Total number of API requests"
        )
        
        self._api_response_time = self.meter.create_histogram(
            "api_response_time_seconds",
            description="API response time in seconds"
        )
        
        self._test_status_counter = self.meter.create_counter(
            "test_status_total",
            description="Test cases by status"
        )
    
    def record_test_execution(self, test_name: str, duration: float, status: str) -> None:
        """记录测试执行度量"""
        attributes = {"test_name": test_name, "status": status}
        
        self._test_counter.add(1, attributes)
        self._test_duration.record(duration, attributes)
        self._test_status_counter.add(1, {"status": status})
        
        # 同时记录到新的度量系统
        self.collector.record_test_end(test_name, status, duration)
    
    def record_api_request(self, method: str, url: str, status_code: int, 
                          response_time: float) -> None:
        """记录API请求度量"""
        attributes = {
            "method": method,
            "url": url,
            "status_code": str(status_code)
        }
        
        self._api_request_counter.add(1, attributes)
        self._api_response_time.record(response_time, attributes)
        
        # 同时记录到新的度量系统
        self.collector.record_api_request(method, url, response_time, status_code)
    
    def record_page_action(self, action: str, element: str = "", duration: float = 0) -> None:
        """记录页面操作度量"""
        page_action_counter = self.meter.create_counter(
            "page_actions_total",
            description="Total number of page actions"
        )
        
        attributes = {"action": action}
        if element:
            attributes["element"] = element
        
        page_action_counter.add(1, attributes)
        
        if duration > 0:
            page_action_duration = self.meter.create_histogram(
                "page_action_duration_seconds",
                description="Page action duration in seconds"
            )
            page_action_duration.record(duration, attributes)
            
            # 同时记录到新的度量系统
            self.collector.record_web_action(action, duration, "success", element)


class TestTimer:
    """测试计时器上下文管理器"""
    
    def __init__(self, metrics: PhoenixMetrics, test_name: str):
        self.metrics = metrics
        self.test_name = test_name
        self.start_time = None
        self.status = "unknown"
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            if exc_type is None:
                self.status = "passed"
            else:
                self.status = "failed"
            
            self.metrics.record_test_execution(self.test_name, duration, self.status)
    
    def set_status(self, status: str) -> None:
        """手动设置测试状态"""
        self.status = status


# 全局度量器实例（向后兼容）
_meters: Dict[str, PhoenixMetrics] = {}
_meter_provider: Optional[Any] = None


def get_meter(name: str) -> PhoenixMetrics:
    """获取度量器实例"""
    if name not in _meters:
        _meters[name] = PhoenixMetrics(name)
    return _meters[name]
"""度量收集系统补充部分"""

# PhoenixMetrics主类
class PhoenixMetrics:
    """PhoenixFrame度量系统"""
    
    def __init__(self, test_run_id: Optional[str] = None):
        self.test_run_id = test_run_id or str(uuid.uuid4())
        # 提供name属性以兼容集成测试对属性存在性的检查
        self.name = "phoenixframe.metrics"
        self.collector = MetricsCollector()
        self.opentelemetry_meter = None
        self.prometheus_registry = None
        self._setup_integrations()
    
    def _setup_integrations(self):
        """设置集成"""
        # OpenTelemetry集成
        if OPENTELEMETRY_METRICS_AVAILABLE:
            try:
                self.opentelemetry_meter = metrics.get_meter(
                    "phoenixframe.metrics",
                    version="3.2.0"
                )
            except Exception:
                pass
        
        # Prometheus集成
        if PROMETHEUS_AVAILABLE:
            try:
                self.prometheus_registry = CollectorRegistry()
            except Exception:
                pass
    
    def test_started(self, test_name: str, test_file: str = "", test_suite: str = ""):
        """记录测试开始"""
        self.collector.counter("test_start_count", 1.0, {
            "test_name": test_name,
            "test_file": test_file,
            "test_suite": test_suite
        })
    
    def test_completed(self, test_name: str, outcome: str, duration: float, 
                      error_type: str = "", test_suite: str = ""):
        """记录测试完成"""
        labels = {
            "test_name": test_name,
            "outcome": outcome,
            "test_suite": test_suite
        }
        if error_type:
            labels["error_type"] = error_type
        
        # 测试完成计数
        self.collector.counter("test_complete_count", 1.0, labels)
        
        # 测试持续时间
        self.collector.histogram("test_duration", duration, labels, MetricUnit.SECONDS)
        
        # 按结果分类计数
        if outcome == "passed":
            self.collector.counter("test_pass_count", 1.0, labels)
        elif outcome == "failed":
            self.collector.counter("test_fail_count", 1.0, labels)
        elif outcome == "skipped":
            self.collector.counter("test_skip_count", 1.0, labels)
    
    def api_request_completed(self, method: str, url: str, status_code: int, 
                            response_time: float, request_size: int = 0, 
                            response_size: int = 0):
        """记录API请求完成"""
        labels = {
            "method": method.upper(),
            "status_code": str(status_code),
            "status_class": f"{status_code // 100}xx"
        }
        
        # API请求计数
        self.collector.counter("api_request_count", 1.0, labels)
        
        # 响应时间
        self.collector.histogram("api_response_time", response_time, labels, MetricUnit.SECONDS)
        
        # 请求和响应大小
        if request_size > 0:
            self.collector.histogram("api_request_size", request_size, labels, MetricUnit.BYTES)
        if response_size > 0:
            self.collector.histogram("api_response_size", response_size, labels, MetricUnit.BYTES)
        
        # 错误率
        if status_code >= 400:
            self.collector.counter("api_error_count", 1.0, labels)
    
    def web_action_completed(self, action: str, element: str, duration: float,
                           success: bool = True, error_type: str = ""):
        """记录Web操作完成"""
        labels = {
            "action": action,
            "element_type": element,
            "success": str(success).lower()
        }
        if error_type:
            labels["error_type"] = error_type
        
        # Web操作计数
        self.collector.counter("web_action_count", 1.0, labels)
        
        # 操作持续时间
        self.collector.histogram("web_action_duration", duration, labels, MetricUnit.SECONDS)
        
        # 错误计数
        if not success:
            self.collector.counter("web_action_error_count", 1.0, labels)
    
    def record_custom_metric(self, name: str, value: float, metric_type: MetricType,
                           labels: Optional[Dict[str, str]] = None,
                           unit: MetricUnit = MetricUnit.NONE,
                           description: str = ""):
        """记录自定义度量"""
        metric = MetricPoint(
            name=name,
            value=value,
            metric_type=metric_type,
            unit=unit,
            labels=labels or {},
            description=description
        )
        self.collector.record_metric(metric)
    
    def get_test_summary(self) -> Dict[str, Any]:
        """获取测试汇总统计"""
        summaries = self.collector.get_all_summaries()
        test_stats = {}
        
        # 提取测试相关统计
        for name, summary in summaries.items():
            if name.startswith('test_'):
                test_stats[name] = {
                    'count': summary.count,
                    'mean': summary.mean,
                    'min': summary.min if summary.min != float('inf') else 0,
                    'max': summary.max if summary.max != float('-inf') else 0,
                    'p95': summary.p95,
                    'p99': summary.p99
                }
        
        return test_stats
    
    def get_api_summary(self) -> Dict[str, Any]:
        """获取API汇总统计"""
        summaries = self.collector.get_all_summaries()
        api_stats = {}
        
        for name, summary in summaries.items():
            if name.startswith('api_'):
                api_stats[name] = {
                    'count': summary.count,
                    'mean': summary.mean,
                    'min': summary.min if summary.min != float('inf') else 0,
                    'max': summary.max if summary.max != float('-inf') else 0,
                    'p95': summary.p95,
                    'p99': summary.p99
                }
        
        return api_stats
    
    def start_collection(self):
        """开始度量收集"""
        self.collector.start_collection()
    
    def stop_collection(self):
        """停止度量收集"""
        self.collector.stop_collection()
    
    def export_metrics(self, format_type: str = "json") -> str:
        """导出度量"""
        return self.collector.export_metrics(format_type)


# 全局度量实例
_metrics_collector: Optional[MetricsCollector] = None
_phoenix_metrics: Optional[PhoenixMetrics] = None
_metrics_enabled = False


def setup_metrics(collection_interval: float = 10.0,
                 console_export: bool = False,
                 prometheus_port: Optional[int] = None,
                 otlp_endpoint: Optional[str] = None,
                 test_run_id: Optional[str] = None) -> bool:
    """
    设置度量收集系统
    
    Args:
        collection_interval: 收集间隔（秒）
        console_export: 是否启用控制台导出
        prometheus_port: Prometheus端口
        otlp_endpoint: OTLP导出端点
        test_run_id: 测试运行ID
        
    Returns:
        bool: 是否成功设置
    """
    global _metrics_collector, _phoenix_metrics, _metrics_enabled
    
    try:
        # 创建度量收集器
        _metrics_collector = MetricsCollector(collection_interval)
        _phoenix_metrics = PhoenixMetrics(test_run_id)
        
        # 启用OpenTelemetry度量导出
        if OPENTELEMETRY_METRICS_AVAILABLE and (otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")):
            _setup_opentelemetry_metrics(otlp_endpoint, console_export)
        
        # 启用Prometheus导出
        if PROMETHEUS_AVAILABLE and prometheus_port:
            _setup_prometheus_metrics(prometheus_port)
        
        # 启动自动收集
        _metrics_collector.start_collection()
        _metrics_enabled = True
        
        print(f"Metrics collection initialized (interval: {collection_interval}s)")
        return True
        
    except Exception as e:
        print(f"Error setting up metrics: {e}")
        return False


def _setup_opentelemetry_metrics(otlp_endpoint: Optional[str], console_export: bool):
    """设置OpenTelemetry度量导出"""
    try:
        # 创建资源
        resource = Resource.create({
            "service.name": "phoenixframe",
            "service.version": "3.2.0",
            "service.instance.id": str(uuid.uuid4()),
        })
        
        # 创建导出器
        readers = []
        
        if otlp_endpoint:
            otlp_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
            readers.append(PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=10000))
        elif os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            otlp_exporter = OTLPMetricExporter()
            readers.append(PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=10000))
        
        if console_export:
            console_exporter = ConsoleMetricExporter()
            readers.append(PeriodicExportingMetricReader(console_exporter, export_interval_millis=15000))
        
        # 创建MeterProvider
        meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(meter_provider)
        
        print("OpenTelemetry metrics exporter configured")
        
    except Exception as e:
        print(f"Warning: Failed to setup OpenTelemetry metrics: {e}")


def _setup_prometheus_metrics(port: int):
    """设置Prometheus度量导出"""
    try:
        import prometheus_client
        from prometheus_client import start_http_server
        
        # 启动Prometheus HTTP服务器
        start_http_server(port)
        print(f"Prometheus metrics server started on port {port}")
        
    except Exception as e:
        print(f"Warning: Failed to setup Prometheus metrics: {e}")


def get_metrics_collector() -> Optional[MetricsCollector]:
    """获取度量收集器"""
    return _metrics_collector


def get_phoenix_metrics() -> Optional[PhoenixMetrics]:
    """获取Phoenix度量系统"""
    return _phoenix_metrics


def is_metrics_enabled() -> bool:
    """检查度量是否已启用"""
    return _metrics_enabled


def get_metrics_summary() -> Dict[str, Any]:
    """获取度量汇总"""
    if _phoenix_metrics:
        return {
            "test_metrics": _phoenix_metrics.get_test_summary(),
            "api_metrics": _phoenix_metrics.get_api_summary(),
            "system_metrics": _metrics_collector.get_current_values() if _metrics_collector else {}
        }
    return {}


def export_metrics(format_type: str = "json") -> str:
    """导出度量数据"""
    if _phoenix_metrics:
        return _phoenix_metrics.export_metrics(format_type)
    return "{}"


# 便捷函数
def record_test_start(test_name: str, **kwargs):
    """记录测试开始"""
    if _phoenix_metrics:
        _phoenix_metrics.test_started(test_name, **kwargs)


def record_test_end(test_name: str, outcome: str, duration: float, **kwargs):
    """记录测试结束"""
    if _phoenix_metrics:
        _phoenix_metrics.test_completed(test_name, outcome, duration, **kwargs)


def record_api_call(method: str, url: str, status_code: int, response_time: float, **kwargs):
    """记录API调用"""
    if _phoenix_metrics:
        _phoenix_metrics.api_request_completed(method, url, status_code, response_time, **kwargs)


def record_web_action(action: str, element: str, duration: float, success: bool = True, **kwargs):
    """记录Web操作"""
    if _phoenix_metrics:
        _phoenix_metrics.web_action_completed(action, element, duration, success, **kwargs)


def record_metric(name: str, value: float, metric_type: MetricType = MetricType.GAUGE, **kwargs):
    """记录自定义度量"""
    if _phoenix_metrics:
        _phoenix_metrics.record_custom_metric(name, value, metric_type, **kwargs)


# 装饰器支持
def metrics_timer(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """度量计时装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if _metrics_collector:
                with _metrics_collector.timer(metric_name, labels):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def metrics_counter(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """度量计数装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if _metrics_collector:
                _metrics_collector.counter(metric_name, 1.0, labels)
            return func(*args, **kwargs)
        return wrapper
    return decorator