"""API 响应断言库

提供链式断言功能，支持状态码、响应头、JSON 路径、响应时间等断言。
"""

from typing import Any, Union

import requests


class APIResponse:
    """API 响应包装器，支持链式断言"""

    def __init__(self, response: requests.Response):
        """初始化 API 响应包装器

        Args:
            response: Requests 响应对象
        """
        self.response = response
        self._assertions = []

    def status_code(self, expected: int) -> "APIResponse":
        """断言状态码

        Args:
            expected: 期望的状态码

        Returns:
            APIResponse: 支持链式调用
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
            APIResponse: 支持链式调用
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
            value: 期望值或值列表

        Returns:
            APIResponse: 支持链式调用
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
            expected: 期望值

        Returns:
            APIResponse: 支持链式调用
        """
        data = self.response.json()
        actual = self._get_json_path(data, path)
        assert actual == expected, f"Expected {path} = {expected}, got {actual}"
        self._assertions.append(f"json_path {path} == {expected}")
        return self

    def json_schema(self, schema: dict[str, Any]) -> "APIResponse":
        """断言 JSON 模式

        Args:
            schema: JSON Schema 定义

        Returns:
            APIResponse: 支持链式调用
        """
        try:
            from jsonschema import validate

            validate(self.response.json(), schema)
        except ImportError as e:
            raise ImportError("jsonschema is required for schema validation") from e

        self._assertions.append("json_schema validation passed")
        return self

    def response_time(self, max_seconds: float) -> "APIResponse":
        """断言响应时间

        Args:
            max_seconds: 最大响应时间（秒）

        Returns:
            APIResponse: 支持链式调用
        """
        assert (
            self.response.elapsed.total_seconds() <= max_seconds
        ), f"Expected response time <= {max_seconds}s, got {self.response.elapsed.total_seconds()}s"
        self._assertions.append(f"response_time <= {max_seconds}s")
        return self

    def content_type(self, expected: str) -> "APIResponse":
        """断言内容类型

        Args:
            expected: 期望的内容类型

        Returns:
            APIResponse: 支持链式调用
        """
        actual = self.response.headers.get("Content-Type", "")
        assert expected in actual, f"Expected Content-Type to contain '{expected}', got '{actual}'"
        self._assertions.append(f"content_type contains {expected}")
        return self

    def json(self) -> dict[str, Any]:
        """获取 JSON 响应数据

        Returns:
            Dict[str, Any]: JSON 数据
        """
        return self.response.json()

    def text(self) -> str:
        """获取文本响应数据

        Returns:
            str: 文本数据
        """
        return self.response.text

    def content(self) -> bytes:
        """获取二进制响应数据

        Returns:
            bytes: 二进制数据
        """
        return self.response.content

    def _get_json_path(self, data: Any, path: str) -> Any:
        """获取 JSON 路径值

        Args:
            data: JSON 数据
            path: 路径，如 "data.user.name"

        Returns:
            Any: 路径对应的值
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
            List[str]: 断言列表
        """
        return self._assertions.copy()

    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"APIResponse(status={self.response.status_code}, assertions={len(self._assertions)})"
        )

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"APIResponse(status={self.response.status_code}, url={self.response.url}, assertions={self._assertions})"
