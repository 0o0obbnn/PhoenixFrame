"""增强的 API 客户端

提供连接池管理、重试机制、幂等性保护等企业级功能。
"""

import time
import uuid
from typing import Any, Callable, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..observability.logger import get_logger
from ..observability.tracer import get_tracer


class EnhancedAPIClient:
    """增强的 API 客户端

    提供企业级的 API 调用功能，包括连接池管理、重试机制、
    幂等性保护、请求日志记录等。
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        enable_idempotency: bool = True,
    ):
        """初始化增强的 API 客户端

        Args:
            base_url: API 基础 URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            backoff_factor: 重试退避因子
            pool_connections: 连接池大小
            pool_maxsize: 连接池最大连接数
            enable_idempotency: 是否启用幂等性保护
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.enable_idempotency = enable_idempotency

        # 创建会话并配置连接池
        self.session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
            raise_on_status=False,
        )

        # 配置适配器
        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=pool_connections, pool_maxsize=pool_maxsize
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 设置默认超时
        self.session.timeout = timeout

        # 初始化观测性组件
        self.tracer = get_tracer("phoenixframe.api.enhanced_client")
        self.logger = get_logger("phoenixframe.api.enhanced_client")

        # 请求计数器
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送请求

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: 其他请求参数

        Returns:
            requests.Response: 响应对象
        """
        self._request_count += 1
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # 添加幂等性保护
        if self.enable_idempotency and method.upper() in ["POST", "PUT", "PATCH"]:
            kwargs.setdefault("headers", {})
            if "Idempotency-Key" not in kwargs["headers"]:
                kwargs["headers"]["Idempotency-Key"] = self._generate_idempotency_key()

        # 添加请求 ID 用于追踪
        request_id = str(uuid.uuid4())
        kwargs.setdefault("headers", {})
        kwargs["headers"]["X-Request-ID"] = request_id

        # 记录请求开始
        start_time = time.time()

        with self.tracer.trace_operation(
            "api_request", method=method, url=url, request_id=request_id
        ):
            try:
                response = self.session.request(method, url, **kwargs)
                duration = time.time() - start_time

                # 记录请求结果
                self._log_request(method, url, response, duration, request_id)

                if response.status_code < 400:
                    self._success_count += 1
                else:
                    self._error_count += 1

                return response

            except Exception as e:
                duration = time.time() - start_time
                self._error_count += 1
                self.logger.error(
                    "API request failed",
                    method=method,
                    url=url,
                    error=str(e),
                    duration=duration,
                    request_id=request_id,
                )
                raise

    def _generate_idempotency_key(self) -> str:
        """生成幂等性键"""
        return str(uuid.uuid4())

    def _log_request(
        self, method: str, url: str, response: requests.Response, duration: float, request_id: str
    ) -> None:
        """记录请求日志"""
        self.logger.info(
            "API request completed",
            method=method,
            url=url,
            status_code=response.status_code,
            duration=duration,
            request_id=request_id,
            response_size=len(response.content),
        )

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET 请求"""
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """POST 请求"""
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """PUT 请求"""
        return self.request("PUT", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> requests.Response:
        """PATCH 请求"""
        return self.request("PATCH", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """DELETE 请求"""
        return self.request("DELETE", endpoint, **kwargs)

    def head(self, endpoint: str, **kwargs) -> requests.Response:
        """HEAD 请求"""
        return self.request("HEAD", endpoint, **kwargs)

    def options(self, endpoint: str, **kwargs) -> requests.Response:
        """OPTIONS 请求"""
        return self.request("OPTIONS", endpoint, **kwargs)

    def set_auth(self, auth: Union[tuple, Callable]) -> None:
        """设置认证信息

        Args:
            auth: 认证信息，可以是 (username, password) 元组或认证函数
        """
        self.session.auth = auth

    def set_headers(self, headers: dict[str, str]) -> None:
        """设置默认请求头

        Args:
            headers: 请求头字典
        """
        self.session.headers.update(headers)

    def set_cookies(self, cookies: dict[str, str]) -> None:
        """设置默认 Cookie

        Args:
            cookies: Cookie 字典
        """
        self.session.cookies.update(cookies)

    def set_proxies(self, proxies: dict[str, str]) -> None:
        """设置代理

        Args:
            proxies: 代理配置字典
        """
        self.session.proxies.update(proxies)

    def set_verify(self, verify: Union[bool, str]) -> None:
        """设置 SSL 验证

        Args:
            verify: SSL 验证设置，True/False 或证书路径
        """
        self.session.verify = verify

    def set_cert(self, cert: Union[str, tuple]) -> None:
        """设置客户端证书

        Args:
            cert: 客户端证书路径或 (cert, key) 元组
        """
        self.session.cert = cert

    def get_stats(self) -> dict[str, Any]:
        """获取客户端统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_requests": self._request_count,
            "successful_requests": self._success_count,
            "failed_requests": self._error_count,
            "success_rate": self._success_count / max(self._request_count, 1),
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0

    def close(self) -> None:
        """关闭客户端，释放资源"""
        self.session.close()
        self.logger.info("API client closed")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


class APIResponse:
    """API 响应包装器，支持链式断言"""

    def __init__(self, response: requests.Response):
        """初始化响应包装器

        Args:
            response: requests.Response 对象
        """
        self.response = response
        self._assertions = []
        self._json_data = None

    def status_code(self, expected: int) -> "APIResponse":
        """断言状态码

        Args:
            expected: 期望的状态码

        Returns:
            self: 支持链式调用
        """
        assert (
            self.response.status_code == expected
        ), f"Expected status {expected}, got {self.response.status_code}"
        self._assertions.append(f"status_code == {expected}")
        return self

    def status_code_in(self, expected_codes: list[int]) -> "APIResponse":
        """断言状态码在范围内

        Args:
            expected_codes: 期望的状态码列表

        Returns:
            self: 支持链式调用
        """
        assert (
            self.response.status_code in expected_codes
        ), f"Expected status in {expected_codes}, got {self.response.status_code}"
        self._assertions.append(f"status_code in {expected_codes}")
        return self

    def header(self, name: str, value: Union[str, list[str]]) -> "APIResponse":
        """断言响应头

        Args:
            name: 响应头名称
            value: 期望的值或值列表

        Returns:
            self: 支持链式调用
        """
        actual = self.response.headers.get(name)
        if isinstance(value, list):
            assert actual in value, f"Expected header {name} in {value}, got {actual}"
        else:
            assert actual == value, f"Expected header {name} = {value}, got {actual}"
        self._assertions.append(f"header {name} == {value}")
        return self

    def json_path(self, path: str, expected: Any) -> "APIResponse":
        """断言 JSON 路径值

        Args:
            path: JSON 路径，如 "data.user.name"
            expected: 期望的值

        Returns:
            self: 支持链式调用
        """
        data = self.json()
        actual = self._get_json_path(data, path)
        assert actual == expected, f"Expected {path} = {expected}, got {actual}"
        self._assertions.append(f"json_path {path} == {expected}")
        return self

    def json_schema(self, schema: dict[str, Any]) -> "APIResponse":
        """断言 JSON 模式

        Args:
            schema: JSON Schema 字典

        Returns:
            self: 支持链式调用
        """
        try:
            from jsonschema import validate

            validate(self.json(), schema)
        except ImportError as e:
            raise ImportError(
                "jsonschema is required for schema validation. Install with: pip install jsonschema"
            ) from e

        self._assertions.append("json_schema validation passed")
        return self

    def response_time(self, max_seconds: float) -> "APIResponse":
        """断言响应时间

        Args:
            max_seconds: 最大响应时间（秒）

        Returns:
            self: 支持链式调用
        """
        actual_time = self.response.elapsed.total_seconds()
        assert (
            actual_time <= max_seconds
        ), f"Expected response time <= {max_seconds}s, got {actual_time}s"
        self._assertions.append(f"response_time <= {max_seconds}s")
        return self

    def content_type(self, expected: str) -> "APIResponse":
        """断言内容类型

        Args:
            expected: 期望的内容类型

        Returns:
            self: 支持链式调用
        """
        actual = self.response.headers.get("content-type", "")
        assert expected in actual, f"Expected content-type containing '{expected}', got '{actual}'"
        self._assertions.append(f"content_type contains '{expected}'")
        return self

    def json(self) -> Any:
        """获取 JSON 响应数据

        Returns:
            JSON 数据
        """
        if self._json_data is None:
            self._json_data = self.response.json()
        return self._json_data

    def text(self) -> str:
        """获取文本响应数据

        Returns:
            文本数据
        """
        return self.response.text

    def content(self) -> bytes:
        """获取二进制响应数据

        Returns:
            二进制数据
        """
        return self.response.content

    def _get_json_path(self, data: Any, path: str) -> Any:
        """获取 JSON 路径值

        Args:
            data: JSON 数据
            path: 路径，如 "data.user.name"

        Returns:
            路径对应的值
        """
        keys = path.split(".")
        current = data

        for key in keys:
            if key.isdigit():
                current = current[int(key)]
            else:
                current = current[key]

        return current

    def get_assertions(self) -> list[str]:
        """获取所有断言

        Returns:
            断言列表
        """
        return self._assertions.copy()

    def __str__(self) -> str:
        """字符串表示"""
        return f"APIResponse(status={self.response.status_code}, url={self.response.url})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"APIResponse(status={self.response.status_code}, url={self.response.url}, assertions={len(self._assertions)})"
