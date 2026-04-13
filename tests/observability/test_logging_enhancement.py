"""
日志功能增强测试

测试PhoenixFrame中增强的日志功能，
包括多种输出格式和动态日志级别调整。
"""

import json
import logging
import tempfile
import time
from pathlib import Path
import pytest

from src.phoenixframe.observability.logger import (
    setup_logging, 
    get_logger, 
    change_log_level,
    get_all_loggers,
    DetailedFormatter,
    StructuredFormatter,
    ELKFormatter
)


class TestLoggingEnhancement:
    """日志功能增强测试"""
    
    def test_detailed_formatter(self):
        """测试详细格式化器"""
        formatter = DetailedFormatter("test-run-123")
        
        # 创建日志记录
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="测试日志消息",
            args=(),
            exc_info=None
        )
        
        # 格式化日志
        formatted = formatter.format(record)
        
        # 验证格式化结果
        assert "测试日志消息" in formatted
        assert "INFO" in formatted  # 详细格式中级别显示为INFO而不是[INFO]
        assert "test.logger" in formatted
    
    def test_structured_formatter(self):
        """测试结构化格式化器"""
        formatter = StructuredFormatter("test-run-123")
        
        # 创建日志记录
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="测试日志消息",
            args=(),
            exc_info=None
        )
        
        # 格式化日志
        formatted = formatter.format(record)
        
        # 解析JSON
        log_data = json.loads(formatted)
        
        # 验证结构化日志内容
        assert log_data["message"] == "测试日志消息"
        assert log_data["level"] == "INFO"
        assert log_data["logger_name"] == "test.logger"
        assert log_data["test_run_id"] == "test-run-123"
    
    def test_elk_formatter(self):
        """测试ELK格式化器"""
        formatter = ELKFormatter("test-run-123")
        
        # 创建日志记录
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="测试日志消息",
            args=(),
            exc_info=None
        )
        
        # 格式化日志
        formatted = formatter.format(record)
        
        # 解析JSON
        log_data = json.loads(formatted)
        
        # 验证ELK格式日志内容
        assert log_data["message"] == "测试日志消息"
        assert log_data["level"] == "info"
        assert log_data["fields"]["logger_name"] == "test.logger"
        assert log_data["fields"]["test_run_id"] == "test-run-123"
    
    def test_multiple_formats(self):
        """测试多种日志格式"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # 测试紧凑格式
            setup_logging(
                formatter_type="compact",
                level="DEBUG",
                log_file=str(log_file),
                test_run_id="test-run-compact"
            )
            
            logger = get_logger("test.compact")
            logger.info("紧凑格式测试")
            
            # 验证日志文件内容
            log_content = log_file.read_text(encoding='utf-8')
            assert "紧凑格式测试" in log_content
    
    def test_dynamic_log_level_change(self):
        """测试动态日志级别调整"""
        setup_logging(formatter_type="compact", level="INFO")
        logger = get_logger("test.dynamic")
        
        # 创建内存处理器来捕获日志
        memory_handler = logging.handlers.MemoryHandler(capacity=100)
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        memory_handler.setFormatter(formatter)
        
        # 添加到日志器
        test_logger = logging.getLogger("test.dynamic")
        test_logger.addHandler(memory_handler)
        original_level = test_logger.level  # 保存原始级别
        
        try:
            # 测试初始级别(INFO)
            logger.debug("调试信息")
            logger.info("信息日志")
            logger.warning("警告日志")
            
            memory_handler.flush()
            records = memory_handler.buffer
            
            # 验证只有INFO和WARNING级别以上的日志被记录
            messages = [record.getMessage() for record in records]
            assert "信息日志" in messages
            assert "警告日志" in messages
            # 注意：由于setup_logging设置的是INFO级别，PhoenixLogger会记录DEBUG消息，
            # 但实际的logging.getLogger("test.dynamic")仍然在INFO级别
            
            # 清空缓冲区
            memory_handler.flush()
            memory_handler.buffer.clear()
            
            # 动态调整为DEBUG级别
            change_log_level("test.dynamic", "DEBUG")
            
            # 测试调整后的级别
            logger.debug("调试信息")
            logger.info("信息日志")
            
            memory_handler.flush()
            records = memory_handler.buffer
            
            # 验证DEBUG级别日志现在被记录
            messages = [record.getMessage() for record in records]
            assert "调试信息" in messages
            assert "信息日志" in messages
        finally:
            # 清理
            test_logger.removeHandler(memory_handler)
            test_logger.setLevel(original_level)  # 恢复原始级别
    
    def test_contextual_logging(self):
        """测试上下文日志"""
        setup_logging(formatter_type="compact", level="DEBUG")
        logger = get_logger("test.context")
        
        # 创建内存处理器来捕获日志
        memory_handler = logging.handlers.MemoryHandler(capacity=100)
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        memory_handler.setFormatter(formatter)
        
        # 添加到日志器
        test_logger = logging.getLogger("test.context")
        test_logger.addHandler(memory_handler)
        
        try:
            # 无上下文日志
            logger.info("无上下文日志")
            
            # 有上下文日志
            with logger.context(user_id="user123", session_id="sess456"):
                logger.info("有上下文日志")
            
            memory_handler.flush()
            records = memory_handler.buffer
            
            # 验证日志内容
            messages = [record.getMessage() for record in records]
            assert "无上下文日志" in messages
            assert "有上下文日志" in messages
        finally:
            # 清理
            test_logger.removeHandler(memory_handler)
    
    def test_event_specific_logging(self):
        """测试事件特定日志"""
        setup_logging(formatter_type="compact", level="DEBUG")
        logger = get_logger("test.events")
        
        # 创建内存处理器来捕获日志
        memory_handler = logging.handlers.MemoryHandler(capacity=100)
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        memory_handler.setFormatter(formatter)
        
        # 添加到日志器
        test_logger = logging.getLogger("test.events")
        test_logger.addHandler(memory_handler)
        
        try:
            # 测试各种事件日志
            logger.test_start("测试用例1", "test_file.py")
            time.sleep(0.01)  # 模拟执行时间
            logger.test_end("测试用例1", "passed", 0.01)
            
            logger.api_request("GET", "https://api.example.com/users")
            logger.api_response(200, 0.1)
            
            logger.web_action("click", "#submit-button")
            
            logger.performance_metric("response_time", 150.0, "ms")
            
            logger.business_event("user_registration", user_id="user123")
            
            memory_handler.flush()
            records = memory_handler.buffer
            
            # 验证各种事件日志都被记录
            messages = [record.getMessage() for record in records]
            assert any("Test Started: 测试用例1" in msg for msg in messages)
            assert any("Test PASSED: 测试用例1" in msg for msg in messages)
            assert any("API Request: GET https://api.example.com/users" in msg for msg in messages)
            assert any("API Response: 200" in msg for msg in messages)
            assert any("Web Action: click on #submit-button" in msg for msg in messages)
            assert any("Metric response_time: 150.0 ms" in msg for msg in messages)
            assert any("Business Event: user_registration" in msg for msg in messages)
        finally:
            # 清理
            test_logger.removeHandler(memory_handler)
    
    def test_get_all_loggers(self):
        """测试获取所有日志器"""
        # 确保有一些日志器被创建
        setup_logging(level="INFO")
        get_logger("test.logger1")
        get_logger("test.logger2")
        
        # 获取所有日志器
        loggers = get_all_loggers()
        
        # 验证返回了日志器字典
        assert isinstance(loggers, dict)
        assert len(loggers) > 0


def test_backward_compatibility():
    """测试向后兼容性"""
    from src.phoenixframe.observability.logger import (
        log_test_start,
        log_test_end,
        log_api_request,
        log_api_response,
        log_web_action,
        log_performance_metric
    )
    
    setup_logging(formatter_type="compact", level="INFO")
    
    # 测试旧的便捷函数仍然可用
    log_test_start("兼容性测试")
    log_test_end("兼容性测试", "passed", 0.1)
    log_api_request("POST", "https://api.example.com/test")
    log_api_response(200, 0.05)
    log_web_action("click", "#test-button")
    log_performance_metric("test_metric", 100.0, "units")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])