# 企业级可观测性模块
from .logger import get_logger, setup_logging
from .tracer import get_tracer, setup_tracing
from .metrics import get_meter, setup_metrics, get_metrics_collector, get_prometheus_collector
from .report_generator import (
    TestResult, TestSuite, ReportSummary, TestReport,
    ReportGenerator, JSONReportGenerator, XMLReportGenerator, HTMLReportGenerator,
    ReportManager, generate_html_report, generate_json_report, generate_xml_report
)
from .report_collector import (
    ReportCollector, get_report_collector, set_report_collector,
    start_test_suite, end_test_suite, start_test, end_test,
    test_context, suite_context
)
from .performance_monitor import (
    PerformanceSnapshot, MemoryProfile, CPUProfile, PerformanceAlert,
    PerformanceAnalyzer, PerformanceProfiler,
    get_performance_analyzer, get_performance_profiler,
    start_performance_monitoring, stop_performance_monitoring,
    get_performance_summary, export_performance_report, profile_function
)
from .performance_dashboard import (
    PerformanceDashboard, generate_performance_dashboard, start_live_dashboard
)
from .performance_integration import (
    PerformanceMonitoringMixin, TestPerformanceMonitor, WebPerformanceMonitor,
    get_test_performance_monitor, get_web_performance_monitor,
    monitor_test_performance, monitor_page_load, monitor_element_operation,
    performance_monitor, monitor_web_method
)

__all__ = [
    # 日志系统
    "get_logger", "setup_logging",
    
    # 链路追踪
    "get_tracer", "setup_tracing", 
    
    # 指标监控
    "get_meter", "setup_metrics", "get_metrics_collector", "get_prometheus_collector",
    
    # 报告生成
    "TestResult", "TestSuite", "ReportSummary", "TestReport",
    "ReportGenerator", "JSONReportGenerator", "XMLReportGenerator", "HTMLReportGenerator",
    "ReportManager", "generate_html_report", "generate_json_report", "generate_xml_report",
    
    # 报告收集
    "ReportCollector", "get_report_collector", "set_report_collector",
    "start_test_suite", "end_test_suite", "start_test", "end_test",
    "test_context", "suite_context",
    
    # 性能监控
    "PerformanceSnapshot", "MemoryProfile", "CPUProfile", "PerformanceAlert",
    "PerformanceAnalyzer", "PerformanceProfiler",
    "get_performance_analyzer", "get_performance_profiler",
    "start_performance_monitoring", "stop_performance_monitoring",
    "get_performance_summary", "export_performance_report", "profile_function",
    
    # 性能仪表板
    "PerformanceDashboard", "generate_performance_dashboard", "start_live_dashboard",
    
    # 性能集成
    "PerformanceMonitoringMixin", "TestPerformanceMonitor", "WebPerformanceMonitor",
    "get_test_performance_monitor", "get_web_performance_monitor",
    "monitor_test_performance", "monitor_page_load", "monitor_element_operation",
    "performance_monitor", "monitor_web_method"
]
