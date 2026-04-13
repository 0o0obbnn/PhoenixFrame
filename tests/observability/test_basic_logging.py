"""基础可观测性测试

测试PhoenixFrame中基础可观测性功能，
包括test_run_id注入日志、日志级别动态调整等。
"""

import json
import logging
import uuid
import pytest
from unittest.mock import patch, MagicMock

from src.phoenixframe.observability.logger import (
    setup_logging, 
    get_logger, 
    get_test_run_id,
    _loggers,
    StructuredFormatter
)


class TestBasicObservability:
    """基础可观测性测试"""
    
    def teardown_method(self):
        """每个测试方法结束后清理_loggers"""
        _loggers.clear()
    
    def test_test_run_id_generation_and_injection(self):
        """测试test_run_id生成和注入到日志中"""
        # 生成一个新的test_run_id
        test_run_id = str(uuid.uuid4())
        
        # 设置日志系统
        setup_logging(
            level="INFO",
            enable_console=False,  # 禁用控制台输出避免干扰
            json_format=True,
            test_run_id=test_run_id
        )
            
        # 获取日志器并记录消息
        logger = get_logger("test.logger")
        logger.info("测试消息")
        
        # 验证test_run_id是否正确设置
        assert get_test_run_id() == test_run_id
    
    def test_log_record_contains_test_run_id(self, caplog):
        """测试日志记录中包含test_run_id"""
        # 生成一个新的test_run_id
        test_run_id = str(uuid.uuid4())
        
        # 设置日志系统
        setup_logging(
            level="INFO",
            enable_console=False,  # 禁用控制台输出避免干扰
            json_format=False,
            test_run_id=test_run_id
        )
        
        # 捕获日志
        with caplog.at_level(logging.INFO):
            # 获取日志器并记录消息
            logger = get_logger("test.logger")
            logger.info("测试消息")
            
            # 验证日志记录中包含test_run_id
            assert len(caplog.records) > 0
            record = caplog.records[0]
            
            # 检查是否有test_run_id属性
            assert hasattr(record, 'test_run_id')
            assert record.test_run_id == test_run_id
    
    def test_multiple_loggers_share_same_test_run_id(self):
        """测试多个日志器共享相同的test_run_id"""
        # 生成一个新的test_run_id
        test_run_id = str(uuid.uuid4())
        
        # 设置日志系统
        setup_logging(
            level="INFO",
            enable_console=False,
            json_format=False,
            test_run_id=test_run_id
        )
        
        # 获取多个日志器
        logger1 = get_logger("test.logger1")
        logger2 = get_logger("test.logger2")
        
        # 验证它们都有相同的test_run_id
        assert logger1.test_run_id == test_run_id
        assert logger2.test_run_id == test_run_id
        assert logger1.test_run_id == logger2.test_run_id
    
    def test_structured_formatter_includes_test_run_id(self):
        """测试结构化格式化器包含test_run_id"""
        # 生成一个新的test_run_id
        test_run_id = str(uuid.uuid4())
        
        # 创建结构化格式化器
        formatter = StructuredFormatter(test_run_id=test_run_id)
        
        # 创建日志记录
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="测试消息",
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
        assert log_data["logger_name"] == "test.logger"
        assert log_data["message"] == "测试消息"
        assert log_data["test_run_id"] == test_run_id
        assert log_data["source"]["module"] == "test"
        assert log_data["source"]["function"] == "test_function"
        assert log_data["source"]["line"] == 10
        assert "@timestamp" in log_data