"""测试结构化日志模块"""
import pytest
import json
import logging
from unittest.mock import patch, Mock
from src.phoenixframe.observability.logger import (
    StructuredFormatter, PhoenixLogger, get_logger, setup_logging
)


def test_structured_formatter():
    """测试结构化格式化器"""
    formatter = StructuredFormatter("test-run-123")
    
    # 创建日志记录
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.module = "test"
    record.funcName = "test_function"
    
    # 格式化日志
    formatted = formatter.format(record)
    log_data = json.loads(formatted)
    
    # 验证日志结构
    assert log_data["level"] == "INFO"
    assert log_data["logger"] == "test.logger"
    assert log_data["message"] == "Test message"
    assert log_data["test_run_id"] == "test-run-123"
    assert log_data["module"] == "test"
    assert log_data["function"] == "test_function"
    assert log_data["line"] == 10
    assert "timestamp" in log_data


def test_phoenix_logger():
    """测试PhoenixLogger"""
    logger = PhoenixLogger("test.logger", "test-run-456")
    
    assert logger.test_run_id == "test-run-456"
    assert logger.logger.name == "test.logger"


def test_phoenix_logger_methods():
    """测试PhoenixLogger的日志方法"""
    with patch('src.phoenixframe.observability.logger.logging.getLogger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        logger = PhoenixLogger("test.logger")
        
        # 测试各种日志级别
        logger.debug("Debug message", extra_field="value")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        # 验证调用
        assert mock_logger.log.call_count == 5
        
        # 测试特殊方法
        logger.step("Test step", step_data="data")
        logger.api_request("GET", "https://api.example.com")
        logger.api_response(200, 0.5, response_size=1024)
        
        assert mock_logger.log.call_count == 8


def test_get_logger():
    """测试获取日志器"""
    logger1 = get_logger("test.module1")
    logger2 = get_logger("test.module1")
    logger3 = get_logger("test.module2")
    
    # 同名日志器应该是同一个实例
    assert logger1 is logger2
    assert logger1 is not logger3


def test_setup_logging():
    """测试日志设置"""
    with patch('src.phoenixframe.observability.logger.logging') as mock_logging:
        mock_root_logger = Mock()
        mock_root_logger.handlers = []  # 模拟handlers列表
        mock_logging.getLogger.return_value = mock_root_logger
        mock_logging.INFO = logging.INFO
        mock_logging.StreamHandler = Mock()

        setup_logging(level="INFO", test_run_id="setup-test-123")

        # 验证设置调用
        mock_root_logger.setLevel.assert_called_with(logging.INFO)
        mock_root_logger.addHandler.assert_called()


def test_setup_logging_with_file():
    """测试带文件输出的日志设置"""
    with patch('src.phoenixframe.observability.logger.logging') as mock_logging:
        with patch('src.phoenixframe.observability.logger.logging.FileHandler') as mock_file_handler:
            mock_root_logger = Mock()
            mock_root_logger.handlers = []  # 模拟handlers列表
            mock_logging.getLogger.return_value = mock_root_logger
            mock_logging.INFO = logging.INFO
            mock_logging.StreamHandler = Mock()

            setup_logging(level="INFO", log_file="test.log")

            # 验证文件处理器被创建
            mock_file_handler.assert_called_with("test.log")
            mock_root_logger.addHandler.assert_called()


def test_structured_formatter_with_exception():
    """测试带异常信息的格式化"""
    formatter = StructuredFormatter()
    
    try:
        raise ValueError("Test exception")
    except ValueError:
        import sys
        exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        record.module = "test"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]


def test_structured_formatter_with_extra_fields():
    """测试带额外字段的格式化"""
    formatter = StructuredFormatter()
    
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.module = "test"
    record.funcName = "test_function"
    record.extra_fields = {"custom_field": "custom_value", "request_id": "req-123"}
    
    formatted = formatter.format(record)
    log_data = json.loads(formatted)
    
    assert log_data["custom_field"] == "custom_value"
    assert log_data["request_id"] == "req-123"
