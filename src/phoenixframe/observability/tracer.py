"""分布式追踪模块"""
import os
import uuid
import time
from typing import Optional, Dict, Any, Callable, List
from contextlib import contextmanager
from functools import wraps
from datetime import datetime

try:
    from opentelemetry import trace, baggage, context
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import Status, StatusCode, SpanKind
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.propagate import inject, extract
    from opentelemetry.semconv.trace import SpanAttributes
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = baggage = context = None


class MockTracer:
    """模拟追踪器，当OpenTelemetry不可用时使用"""
    
    def start_span(self, name: str, **kwargs):
        return MockSpan(name)
    
    @contextmanager
    def start_as_current_span(self, name: str, **kwargs):
        yield MockSpan(name)


class MockSpan:
    """模拟Span"""
    
    def __init__(self, name: str):
        self.name = name
    
    def set_attribute(self, key: str, value: Any) -> None:
        pass
    
    def set_status(self, status: Any) -> None:
        pass
    
    def end(self) -> None:
        pass
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        pass
    
    def record_exception(self, exception: Exception) -> None:
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class PhoenixTracer:
    """PhoenixFrame增强追踪器"""
    
    def __init__(self, name: str):
        self.name = name
        self.test_run_id = str(uuid.uuid4())
        self._current_test_span = None
        self._correlation_id = None
        
        if OPENTELEMETRY_AVAILABLE:
            self.tracer = trace.get_tracer(name)
        else:
            self.tracer = MockTracer()
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """设置关联ID，用于跨服务追踪"""
        self._correlation_id = correlation_id
        if OPENTELEMETRY_AVAILABLE and baggage:
            baggage.set_baggage("correlation_id", correlation_id)
    
    def get_correlation_id(self) -> Optional[str]:
        """获取当前关联ID"""
        if OPENTELEMETRY_AVAILABLE and baggage:
            return baggage.get_baggage("correlation_id") or self._correlation_id
        return self._correlation_id
    
    def start_span(self, name: str, **kwargs):
        """开始一个新的span"""
        return self.tracer.start_span(name, **kwargs)
    
    @contextmanager
    def start_as_current_span(self, name: str, attributes: Optional[Dict[str, Any]] = None, 
                             kind: Optional[Any] = None, **kwargs):
        """作为当前span开始追踪"""
        span_kwargs = kwargs.copy()
        if kind and OPENTELEMETRY_AVAILABLE:
            span_kwargs['kind'] = kind
        
        with self.tracer.start_as_current_span(name, **span_kwargs) as span:
            # 添加通用属性
            if hasattr(span, 'set_attribute'):
                span.set_attribute("test.run.id", self.test_run_id)
                span.set_attribute("service.name", "phoenixframe")
                span.set_attribute("service.version", "3.2.0")
                
                # 添加关联ID
                correlation_id = self.get_correlation_id()
                if correlation_id:
                    span.set_attribute("correlation.id", correlation_id)
                
                # 添加自定义属性
                if attributes:
                    for key, value in attributes.items():
                        if value is not None:  # 跳过None值
                            span.set_attribute(key, str(value) if not isinstance(value, (int, float, bool)) else value)
            
            try:
                yield span
            except Exception as e:
                if hasattr(span, 'record_exception'):
                    span.record_exception(e)
                if hasattr(span, 'set_status') and OPENTELEMETRY_AVAILABLE:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    def trace_test_case(self, test_name: str, test_file: str = "", outcome: str = "", 
                       test_id: str = "", test_suite: str = ""):
        """追踪测试用例"""
        attributes = {
            "test.name": test_name,
            "test.type": "unit",
            "test.framework": "pytest"
        }
        if test_file:
            attributes["test.file"] = test_file
        if outcome:
            attributes["test.outcome"] = outcome
        if test_id:
            attributes["test.id"] = test_id
        if test_suite:
            attributes["test.suite"] = test_suite
            
        return self.start_as_current_span(f"test_case:{test_name}", attributes, 
                                        kind=SpanKind.INTERNAL if OPENTELEMETRY_AVAILABLE else None)
    
    def trace_api_request(self, method: str, url: str, status_code: Optional[int] = None, 
                         response_time: Optional[float] = None, request_size: Optional[int] = None,
                         response_size: Optional[int] = None, user_agent: str = ""):
        """追踪API请求"""
        attributes = {
            SpanAttributes.HTTP_METHOD if OPENTELEMETRY_AVAILABLE else "http.method": method.upper(),
            SpanAttributes.HTTP_URL if OPENTELEMETRY_AVAILABLE else "http.url": url,
            SpanAttributes.HTTP_SCHEME if OPENTELEMETRY_AVAILABLE else "http.scheme": "https" if url.startswith("https") else "http"
        }
        
        if status_code:
            attributes[SpanAttributes.HTTP_STATUS_CODE if OPENTELEMETRY_AVAILABLE else "http.status_code"] = status_code
        if response_time:
            attributes["http.response_time_ms"] = response_time * 1000
        if request_size:
            attributes[SpanAttributes.HTTP_REQUEST_CONTENT_LENGTH if OPENTELEMETRY_AVAILABLE else "http.request_content_length"] = request_size
        if response_size:
            attributes[SpanAttributes.HTTP_RESPONSE_CONTENT_LENGTH if OPENTELEMETRY_AVAILABLE else "http.response_content_length"] = response_size
        if user_agent:
            attributes[SpanAttributes.HTTP_USER_AGENT if OPENTELEMETRY_AVAILABLE else "http.user_agent"] = user_agent
            
        return self.start_as_current_span(f"HTTP {method.upper()}", attributes, 
                                        kind=SpanKind.CLIENT if OPENTELEMETRY_AVAILABLE else None)
    
    def trace_page_action(self, action: str, element: str = "", page_url: str = "", 
                         duration: Optional[float] = None, element_type: str = "",
                         screenshot_path: str = ""):
        """追踪页面操作"""
        attributes = {
            "web.action": action,
            "web.type": "ui_interaction",
            "web.driver": "selenium"  # 可以根据实际驱动类型调整
        }
        
        if element:
            attributes["web.element"] = element
        if element_type:
            attributes["web.element_type"] = element_type
        if page_url:
            attributes["web.page_url"] = page_url
        if duration:
            attributes["web.duration_ms"] = duration * 1000
        if screenshot_path:
            attributes["web.screenshot"] = screenshot_path
            
        span_name = f"Web {action}"
        if element:
            span_name += f" {element}"
            
        return self.start_as_current_span(span_name, attributes, 
                                        kind=SpanKind.INTERNAL if OPENTELEMETRY_AVAILABLE else None)
    
    def trace_database_query(self, operation: str, table: str = "", query: str = "", 
                           database: str = "", connection_string: str = "",
                           rows_affected: Optional[int] = None, execution_time: Optional[float] = None):
        """追踪数据库查询"""
        attributes = {
            SpanAttributes.DB_OPERATION if OPENTELEMETRY_AVAILABLE else "db.operation": operation,
            SpanAttributes.DB_SYSTEM if OPENTELEMETRY_AVAILABLE else "db.system": "sql"
        }
        
        if table:
            attributes[SpanAttributes.DB_SQL_TABLE if OPENTELEMETRY_AVAILABLE else "db.sql.table"] = table
        if query:
            # 截断长查询以避免span过大
            truncated_query = query[:500] + "..." if len(query) > 500 else query
            attributes[SpanAttributes.DB_STATEMENT if OPENTELEMETRY_AVAILABLE else "db.statement"] = truncated_query
        if database:
            attributes[SpanAttributes.DB_NAME if OPENTELEMETRY_AVAILABLE else "db.name"] = database
        if connection_string:
            # 移除敏感信息
            safe_connection = connection_string.split('@')[-1] if '@' in connection_string else connection_string
            attributes[SpanAttributes.DB_CONNECTION_STRING if OPENTELEMETRY_AVAILABLE else "db.connection_string"] = safe_connection
        if rows_affected is not None:
            attributes["db.rows_affected"] = rows_affected
        if execution_time is not None:
            attributes["db.execution_time_ms"] = execution_time * 1000
            
        return self.start_as_current_span(f"DB {operation}", attributes, 
                                        kind=SpanKind.CLIENT if OPENTELEMETRY_AVAILABLE else None)
    
    def trace_file_operation(self, operation: str, file_path: str = "", file_size: Optional[int] = None,
                           encoding: str = "", mime_type: str = ""):
        """追踪文件操作"""
        attributes = {
            "file.operation": operation
        }
        
        if file_path:
            attributes["file.path"] = file_path
        if file_size is not None:
            attributes["file.size"] = file_size
        if encoding:
            attributes["file.encoding"] = encoding
        if mime_type:
            attributes["file.mime_type"] = mime_type
            
        return self.start_as_current_span(f"File {operation}", attributes, 
                                        kind=SpanKind.INTERNAL if OPENTELEMETRY_AVAILABLE else None)
    
    def trace_lifecycle_operation(self, operation: str):
        """追踪生命周期操作"""
        attributes = {
            "lifecycle.operation": operation,
            "lifecycle.type": "management"
        }
        return self.start_as_current_span(f"Lifecycle {operation}", attributes,
                                        kind=SpanKind.INTERNAL if OPENTELEMETRY_AVAILABLE else None)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """向当前span添加事件"""
        if OPENTELEMETRY_AVAILABLE:
            current_span = trace.get_current_span()
            if current_span and hasattr(current_span, 'add_event'):
                current_span.add_event(name, attributes or {})
    
    def set_attribute(self, key: str, value: Any):
        """向当前span设置属性"""
        if OPENTELEMETRY_AVAILABLE:
            current_span = trace.get_current_span()
            if current_span and hasattr(current_span, 'set_attribute'):
                current_span.set_attribute(key, value)
    
    def get_trace_context(self) -> Dict[str, str]:
        """获取当前追踪上下文，用于传播"""
        if not OPENTELEMETRY_AVAILABLE:
            return {}
        
        headers = {}
        inject(headers)
        return headers
    
    def set_trace_context(self, headers: Dict[str, str]):
        """从headers中恢复追踪上下文"""
        if OPENTELEMETRY_AVAILABLE and headers:
            ctx = extract(headers)
            if ctx:
                context.attach(ctx)
    
    def get_test_run_id(self) -> str:
        """获取当前测试运行ID"""
        return self.test_run_id


# 全局追踪器实例
_tracers: Dict[str, PhoenixTracer] = {}
_tracer_provider: Optional[Any] = None
_tracing_enabled = False


def setup_tracing(service_name: str = "phoenixframe", 
                 service_version: str = "3.2.0",
                 otlp_endpoint: Optional[str] = None,
                 console_export: bool = False,
                 auto_instrument: bool = True,
                 sample_rate: float = 1.0,
                 resource_attributes: Optional[Dict[str, str]] = None) -> bool:
    """
    设置分布式追踪
    
    Args:
        service_name: 服务名称
        service_version: 服务版本
        otlp_endpoint: OTLP导出端点
        console_export: 是否启用控制台导出
        auto_instrument: 是否自动启用HTTP请求instrumentation
        sample_rate: 采样率 (0.0-1.0)
        resource_attributes: 额外的资源属性
        
    Returns:
        bool: 是否成功设置追踪
    """
    global _tracer_provider, _tracing_enabled
    
    if not OPENTELEMETRY_AVAILABLE:
        print("Warning: OpenTelemetry is not available. Install with: pip install 'phoenixframe[observability]'")
        return False
    
    try:
        # 创建资源属性
        attributes = {
            "service.name": service_name,
            "service.version": service_version,
            "service.instance.id": str(uuid.uuid4()),
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
            "telemetry.sdk.version": "1.21.0"
        }
        
        # 添加自定义资源属性
        if resource_attributes:
            attributes.update(resource_attributes)
        
        # 添加环境信息
        if os.getenv("PHOENIX_ENVIRONMENT"):
            attributes["deployment.environment"] = os.getenv("PHOENIX_ENVIRONMENT")
        
        # 创建资源
        resource = Resource.create(attributes)
        
        # 创建TracerProvider
        _tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(_tracer_provider)
        
        # 配置采样
        if sample_rate < 1.0:
            from opentelemetry.sdk.trace.sampling import TraceIdRatioBasedSampler
            _tracer_provider._sampler = TraceIdRatioBasedSampler(sample_rate)
        
        # 添加导出器
        exporters_added = 0
        
        # OTLP导出器
        if otlp_endpoint:
            try:
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                exporters_added += 1
                print(f"OTLP exporter configured for endpoint: {otlp_endpoint}")
            except Exception as e:
                print(f"Warning: Failed to configure OTLP exporter: {e}")
        elif os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            try:
                otlp_exporter = OTLPSpanExporter()
                _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                exporters_added += 1
                print(f"OTLP exporter configured from environment")
            except Exception as e:
                print(f"Warning: Failed to configure OTLP exporter from environment: {e}")
        
        # 控制台导出器
        if console_export or os.getenv("PHOENIX_TRACE_CONSOLE", "false").lower() == "true":
            try:
                console_exporter = ConsoleSpanExporter()
                _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
                exporters_added += 1
                print("Console trace exporter configured")
            except Exception as e:
                print(f"Warning: Failed to configure console exporter: {e}")
        
        # 如果没有配置任何导出器，默认使用控制台
        if exporters_added == 0:
            console_exporter = ConsoleSpanExporter()
            _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
            print("Default console trace exporter configured")
        
        # 自动instrumentation
        if auto_instrument:
            _setup_auto_instrumentation()
        
        _tracing_enabled = True
        print(f"OpenTelemetry tracing initialized for service: {service_name}")
        return True
        
    except Exception as e:
        print(f"Error setting up tracing: {e}")
        return False


def _setup_auto_instrumentation():
    """设置自动instrumentation"""
    instrumentation_count = 0
    
    # HTTP requests instrumentation
    try:
        RequestsInstrumentor().instrument()
        instrumentation_count += 1
    except Exception as e:
        print(f"Warning: Failed to auto-instrument requests: {e}")
    
    # urllib3 instrumentation
    try:
        URLLib3Instrumentor().instrument()
        instrumentation_count += 1
    except Exception as e:
        print(f"Warning: Failed to auto-instrument urllib3: {e}")
    
    # httpx instrumentation (如果可用)
    try:
        HTTPXClientInstrumentor().instrument()
        instrumentation_count += 1
    except Exception as e:
        # httpx可能不可用，这是正常的
        pass
    
    if instrumentation_count > 0:
        print(f"Auto-instrumentation enabled for {instrumentation_count} libraries")


def configure_sampling(sample_rate: float = 1.0, parent_based: bool = True):
    """配置追踪采样策略"""
    if not OPENTELEMETRY_AVAILABLE or not _tracer_provider:
        return False
    
    try:
        if parent_based:
            from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBasedSampler
            sampler = ParentBased(root=TraceIdRatioBasedSampler(sample_rate))
        else:
            from opentelemetry.sdk.trace.sampling import TraceIdRatioBasedSampler
            sampler = TraceIdRatioBasedSampler(sample_rate)
        
        _tracer_provider._sampler = sampler
        print(f"Sampling configured: rate={sample_rate}, parent_based={parent_based}")
        return True
    except Exception as e:
        print(f"Error configuring sampling: {e}")
        return False


def add_span_processor(processor):
    """添加自定义span处理器"""
    if OPENTELEMETRY_AVAILABLE and _tracer_provider:
        _tracer_provider.add_span_processor(processor)


def create_trace_context_headers() -> Dict[str, str]:
    """创建用于传播的追踪上下文headers"""
    if not OPENTELEMETRY_AVAILABLE:
        return {}
    
    headers = {}
    inject(headers)
    return headers


def restore_trace_context(headers: Dict[str, str]):
    """从headers恢复追踪上下文"""
    if OPENTELEMETRY_AVAILABLE and headers:
        ctx = extract(headers)
        if ctx:
            context.attach(ctx)


def get_tracer(name: str) -> PhoenixTracer:
    """
    获取追踪器实例
    
    Args:
        name: 追踪器名称
        
    Returns:
        PhoenixTracer: 追踪器实例
    """
    if name not in _tracers:
        _tracers[name] = PhoenixTracer(name)
    return _tracers[name]


def trace_decorator(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """追踪装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            span_attributes = attributes or {}
            span_attributes.update({
                "function.name": func.__name__,
                "function.module": func.__module__,
            })
            
            with tracer.start_as_current_span(f"{operation_name}:{func.__name__}", span_attributes):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def is_tracing_enabled() -> bool:
    """检查追踪是否已启用"""
    return _tracing_enabled and OPENTELEMETRY_AVAILABLE


def shutdown_tracing():
    """关闭追踪系统"""
    global _tracer_provider, _tracing_enabled
    
    if _tracer_provider and hasattr(_tracer_provider, 'shutdown'):
        _tracer_provider.shutdown()
    
    _tracing_enabled = False


# 便捷函数
def trace_test(test_name: str, test_file: str = ""):
    """便捷的测试追踪函数"""
    tracer = get_tracer("phoenixframe.test")
    return tracer.trace_test_case(test_name, test_file)


def trace_api(method: str, url: str, status_code: Optional[int] = None, 
             response_time: Optional[float] = None):
    """便捷的API追踪函数"""
    tracer = get_tracer("phoenixframe.api")
    return tracer.trace_api_request(method, url, status_code, response_time)


def trace_web(action: str, element: str = "", page_url: str = ""):
    """便捷的Web追踪函数"""
    tracer = get_tracer("phoenixframe.web")
    return tracer.trace_page_action(action, element, page_url)


def trace_db(operation: str, table: str = "", query: str = ""):
    """便捷的数据库追踪函数"""
    tracer = get_tracer("phoenixframe.database")
    return tracer.trace_database_query(operation, table, query)


def trace_custom(span_name: str, attributes: Optional[Dict[str, Any]] = None, kind=None):
    """便捷的自定义追踪函数"""
    tracer = get_tracer("phoenixframe.custom")
    return tracer.start_as_current_span(span_name, attributes, kind)


class TraceContext:
    """追踪上下文管理器，用于跨进程/线程传播追踪信息"""
    
    def __init__(self, headers: Optional[Dict[str, str]] = None):
        self.headers = headers or create_trace_context_headers()
        self._token = None
    
    def __enter__(self):
        if self.headers and OPENTELEMETRY_AVAILABLE:
            ctx = extract(self.headers)
            if ctx:
                self._token = context.attach(ctx)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token and OPENTELEMETRY_AVAILABLE:
            context.detach(self._token)
    
    def get_headers(self) -> Dict[str, str]:
        """获取当前上下文的传播headers"""
        if not OPENTELEMETRY_AVAILABLE:
            return {}
        headers = {}
        inject(headers)
        return headers


def auto_trace(operation_type: str = "function", include_args: bool = False, 
               include_result: bool = False, span_name: Optional[str] = None):
    """自动追踪装饰器，增强版"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            name = span_name or f"{operation_type}:{func.__name__}"
            
            span_attributes = {
                "function.name": func.__name__,
                "function.module": func.__module__,
                "operation.type": operation_type
            }
            
            # 包含参数信息
            if include_args and args:
                span_attributes["function.args.count"] = len(args)
                # 只记录前3个参数的字符串表示（避免敏感信息）
                for i, arg in enumerate(args[:3]):
                    if not callable(arg):
                        span_attributes[f"function.args.{i}"] = str(arg)[:100]
            
            if include_args and kwargs:
                span_attributes["function.kwargs.count"] = len(kwargs)
                # 只记录非敏感键名
                safe_keys = [k for k in kwargs.keys() if not any(
                    sensitive in k.lower() for sensitive in 
                    ['password', 'token', 'secret', 'key', 'auth']
                )]
                span_attributes["function.kwargs.keys"] = ",".join(safe_keys[:5])
            
            start_time = time.time()
            
            with tracer.start_as_current_span(name, span_attributes):
                try:
                    result = func(*args, **kwargs)
                    
                    # 记录执行时间
                    execution_time = time.time() - start_time
                    tracer.set_attribute("function.execution_time_ms", execution_time * 1000)
                    
                    # 包含结果信息
                    if include_result and result is not None:
                        if hasattr(result, '__len__') and not isinstance(result, str):
                            tracer.set_attribute("function.result.length", len(result))
                        tracer.set_attribute("function.result.type", type(result).__name__)
                    
                    tracer.set_attribute("function.success", True)
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    tracer.set_attribute("function.execution_time_ms", execution_time * 1000)
                    tracer.set_attribute("function.success", False)
                    tracer.set_attribute("function.error", str(e))
                    raise
        return wrapper
    return decorator


# 专用的测试追踪装饰器
def trace_test_method(test_suite: str = "", test_id: str = ""):
    """测试方法追踪装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer("phoenixframe.test")
            test_name = func.__name__
            
            # 从文件路径获取测试文件信息
            test_file = func.__code__.co_filename
            
            with tracer.trace_test_case(test_name, test_file, test_suite=test_suite, test_id=test_id):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    tracer.set_attribute("test.duration_ms", execution_time * 1000)
                    tracer.set_attribute("test.outcome", "passed")
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    tracer.set_attribute("test.duration_ms", execution_time * 1000)
                    tracer.set_attribute("test.outcome", "failed")
                    tracer.set_attribute("test.error", str(e))
                    raise
        return wrapper
    return decorator
