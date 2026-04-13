"""API客户端，支持自动认证和链式断言"""
import requests
import os
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin
import uuid
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..core.config import get_config
from .response import APIResponse
from ..observability.tracer import get_tracer, is_tracing_enabled
from ..observability.logger import get_logger, log_api_request, log_api_response


class APIClient:
    """API客户端，提供统一的HTTP请求接口"""
    
    def __init__(self, base_url: Optional[str] = None, auth_strategy=None, 
                 max_retries: int = 3, retry_delay: float = 1.0,
                 pool_connections: int = 10, pool_maxsize: int = 10):
        """
        初始化API客户端
        
        Args:
            base_url: 基础URL，如果不提供则从配置中获取
            auth_strategy: 认证策略，用于自动处理认证
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            pool_connections: 连接池连接数
            pool_maxsize: 连接池最大连接数
        """
        self.config = get_config()
        # 获取当前环境或默认环境的base_url
        current_env_name = os.environ.get('PHOENIX_CURRENT_ENV', 'default')
        current_env = self.config.environments.get(current_env_name)
        if not current_env:
            current_env = self.config.environments.get('default')
        default_base_url = current_env.base_url if current_env else "http://localhost:8000"
        self.base_url = base_url or default_base_url
        self.auth_strategy = auth_strategy
        
        # 重试配置
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 创建会话并配置连接池
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=Retry(
                total=max_retries,
                backoff_factor=retry_delay,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"]
            )
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 初始化观测性组件
        self.tracer = get_tracer("phoenixframe.api")
        self.logger = get_logger("phoenixframe.api")
        
        # 设置默认请求头
        self.session.headers.update({
            'User-Agent': f'PhoenixFrame/{self.config.version}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def _prepare_url(self, endpoint: str) -> str:
        """准备完整URL"""
        if endpoint.startswith(('http://', 'https://')):
            return endpoint
        return urljoin(self.base_url, endpoint.lstrip('/'))
    
    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """准备请求头，包括认证和追踪信息"""
        request_headers = self.session.headers.copy()
        
        if headers:
            request_headers.update(headers)
        
        # 添加追踪ID
        trace_id = str(uuid.uuid4())
        request_headers['X-Trace-ID'] = trace_id
        
        # 如果有认证策略，应用认证
        if self.auth_strategy:
            auth_headers = self.auth_strategy.get_auth_headers()
            request_headers.update(auth_headers)
        
        return request_headers
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> APIResponse:
        """发送HTTP请求"""
        url = self._prepare_url(endpoint)
        headers = self._prepare_headers(kwargs.pop('headers', None))
        
        # 记录请求开始
        start_time = time.time()
        self.logger.api_request(method, url, **kwargs)
        
        # 使用分布式追踪
        with self.tracer.trace_api_request(method, url) as span:
            try:
                # 发送请求
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                
                # 计算响应时间
                response_time = time.time() - start_time
                
                # 记录响应
                self.logger.api_response(response.status_code, response_time, 
                                       response_size=len(response.content),
                                       url=url)
                
                # 添加追踪属性
                if is_tracing_enabled() and hasattr(span, 'set_attribute'):
                    span.set_attribute("http.status_code", response.status_code)
                    span.set_attribute("http.response_time_ms", response_time * 1000)
                    span.set_attribute("http.response_size", len(response.content))
                    
                    # 如果是错误响应，设置错误状态
                    if response.status_code >= 400:
                        span.set_status({"status_code": 2, "description": f"HTTP {response.status_code}"})
                
                return APIResponse(response)
                
            except Exception as e:
                # 记录错误
                response_time = time.time() - start_time
                self.logger.error(f"API request failed: {str(e)}", 
                                extra={
                                    "method": method, 
                                    "url": url, 
                                    "error": str(e),
                                    "response_time": response_time
                                })
                
                # 记录异常到追踪
                if is_tracing_enabled() and hasattr(span, 'record_exception'):
                    span.record_exception(e)
                
                raise
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None, **kwargs) -> APIResponse:
        """发送GET请求"""
        return self._make_request('GET', endpoint, params=params, headers=headers, **kwargs)
    
    def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None,
             data: Optional[Union[str, Dict[str, Any]]] = None,
             files: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None, **kwargs) -> APIResponse:
        """发送POST请求"""
        return self._make_request('POST', endpoint, json=json, data=data, 
                                files=files, headers=headers, **kwargs)
    
    def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None,
            data: Optional[Union[str, Dict[str, Any]]] = None,
            headers: Optional[Dict[str, str]] = None, **kwargs) -> APIResponse:
        """发送PUT请求"""
        return self._make_request('PUT', endpoint, json=json, data=data, 
                                headers=headers, **kwargs)
    
    def patch(self, endpoint: str, json: Optional[Dict[str, Any]] = None,
              data: Optional[Union[str, Dict[str, Any]]] = None,
              headers: Optional[Dict[str, str]] = None, **kwargs) -> APIResponse:
        """发送PATCH请求"""
        return self._make_request('PATCH', endpoint, json=json, data=data, 
                                headers=headers, **kwargs)
    
    def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None, 
               **kwargs) -> APIResponse:
        """发送DELETE请求"""
        return self._make_request('DELETE', endpoint, headers=headers, **kwargs)
    
    def set_auth_strategy(self, auth_strategy):
        """设置认证策略"""
        self.auth_strategy = auth_strategy
    
    def close(self):
        """关闭会话"""
        self.session.close()