#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础可观测性功能示例

展示如何使用PhoenixFrame的基础可观测性功能，
包括日志、追踪和度量收集。
"""

import time
import uuid
from src.phoenixframe.observability.logger import setup_logging, get_logger
from src.phoenixframe.observability.tracer import setup_tracing, get_tracer
from src.phoenixframe.observability.metrics import setup_metrics, get_phoenix_metrics


def demo_basic_observability():
    """演示基础可观测性功能"""
    print("=== 基础可观测性功能演示 ===\n")
    
    # 1. 设置日志系统
    print("1. 设置日志系统...")
    test_run_id = str(uuid.uuid4())
    setup_logging(
        level="INFO",
        enable_console=True,
        json_format=False,
        test_run_id=test_run_id
    )
    print(f"   日志系统已设置，test_run_id: {test_run_id}")
    
    # 获取日志器
    logger = get_logger("observability.demo")
    logger.info("日志系统初始化完成")
    
    # 2. 设置追踪系统
    print("\n2. 设置追踪系统...")
    if setup_tracing(
        service_name="phoenixframe-demo",
        console_export=True
    ):
        print("   追踪系统已设置")
        tracer = get_tracer("observability.demo")
        logger.info("追踪系统初始化完成")
    else:
        print("   追踪系统不可用（缺少依赖）")
        tracer = None
    
    # 3. 设置度量系统
    print("\n3. 设置度量系统...")
    if setup_metrics(
        collection_interval=5.0,
        console_export=True
    ):
        print("   度量系统已设置")
        metrics = get_phoenix_metrics()
        logger.info("度量系统初始化完成")
    else:
        print("   度量系统初始化失败")
        metrics = None
    
    # 4. 演示日志功能
    print("\n4. 演示日志功能...")
    logger.info("开始执行示例任务")
    logger.warning("这是一条警告消息")
    logger.error("这是一条错误消息")
    
    # 5. 演示追踪功能
    print("\n5. 演示追踪功能...")
    if tracer:
        with tracer.start_as_current_span("example-operation"):
            logger.info("在追踪span中执行操作")
            time.sleep(0.1)  # 模拟工作
            
        with tracer.start_as_current_span("another-operation"):
            logger.info("在另一个追踪span中执行操作")
            time.sleep(0.05)  # 模拟工作
    else:
        logger.info("跳过追踪功能演示（追踪系统不可用）")
    
    # 6. 演示度量功能
    print("\n6. 演示度量功能...")
    if metrics:
        # 记录一些度量
        metrics.test_started("example_test")
        time.sleep(0.02)  # 模拟测试执行
        metrics.test_completed("example_test", "passed", 0.02)
        
        metrics.api_request_completed("GET", "/api/users", 200, 0.05)
        metrics.web_action_completed("click", "button", 0.01, True)
        
        logger.info("度量数据已记录")
    else:
        logger.info("跳过度量功能演示（度量系统不可用）")
    
    # 7. 总结
    print("\n7. 演示完成")
    logger.info("基础可观测性功能演示完成")


if __name__ == "__main__":
    demo_basic_observability()
