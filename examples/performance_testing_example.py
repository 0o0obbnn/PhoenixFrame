"""
性能测试综合示例
演示PhoenixFrame的性能测试功能
"""
import sys
from pathlib import Path
import tempfile
import time

# 添加src路径以便导入模块
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.phoenixframe.performance import (
    PerformanceTestConfig,
    PerformanceTestManager,
    run_performance_test,
    generate_locustfile,
    LOCUST_AVAILABLE
)
from src.phoenixframe.observability.logger import get_logger

# 设置日志
logger = get_logger("performance_testing_example")


def demo_performance_test_availability():
    """演示性能测试可用性检查"""
    logger.info("=== Performance Testing Availability Demo ===")
    
    if LOCUST_AVAILABLE:
        logger.info("✅ Locust is available for performance testing")
        try:
            from locust import HttpUser, task, between
            logger.info("✅ Locust components imported successfully")
        except ImportError as e:
            logger.warning(f"⚠️ Locust import issue: {e}")
    else:
        logger.warning("❌ Locust is not available")
        logger.info("   Install with: pip install locust")
        logger.info("   Or: pip install 'phoenixframe[performance]'")
    
    return LOCUST_AVAILABLE


def demo_locustfile_generation():
    """演示Locust测试文件生成"""
    logger.info("=== Locustfile Generation Demo ===")
    
    config = PerformanceTestConfig(
        target_url="http://localhost:8000",
        users=10,
        spawn_rate=2.0,
        duration=60,
        test_name="demo_test"
    )
    
    manager = PerformanceTestManager()
    
    # 生成基础测试文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        locustfile_path = f.name
    
    try:
        content = manager.generate_locustfile(config, locustfile_path, "basic")
        logger.info(f"Generated locustfile: {locustfile_path}")
        logger.info(f"File size: {len(content)} characters")
        
        # 显示生成内容的摘要
        lines = content.split('\n')
        logger.info(f"Total lines: {len(lines)}")
        
        # 检查关键内容
        if "HttpUser" in content:
            logger.info("✅ Contains HttpUser class")
        if "@task" in content:
            logger.info("✅ Contains task decorators")
        if config.target_url in content:
            logger.info("✅ Contains target URL")
        
        # 显示部分内容
        logger.info("Sample content (first 10 lines):")
        for i, line in enumerate(lines[:10]):
            logger.info(f"  {i+1:2}: {line}")
        
        return locustfile_path
        
    except Exception as e:
        logger.error(f"Failed to generate locustfile: {e}")
        return None


def demo_performance_test_config():
    """演示性能测试配置"""
    logger.info("=== Performance Test Configuration Demo ===")
    
    # 基础配置
    basic_config = PerformanceTestConfig(
        target_url="http://httpbin.org",
        users=5,
        duration=30,
        test_name="basic_test"
    )
    
    logger.info(f"Basic config: {basic_config.test_name}")
    logger.info(f"  Target URL: {basic_config.target_url}")
    logger.info(f"  Users: {basic_config.users}")
    logger.info(f"  Duration: {basic_config.duration}s")
    logger.info(f"  Spawn rate: {basic_config.spawn_rate}")
    
    # 高级配置
    advanced_config = PerformanceTestConfig(
        target_url="http://httpbin.org",
        users=20,
        spawn_rate=5.0,
        duration=120,
        test_name="advanced_test",
        html_report="performance_report.html",
        csv_prefix="test_results",
        tags=["smoke", "api"],
        exclude_tags=["slow"],
        custom_options={
            "stop-timeout": 10,
            "expect-workers": 1
        }
    )
    
    logger.info(f"\nAdvanced config: {advanced_config.test_name}")
    logger.info(f"  Target URL: {advanced_config.target_url}")
    logger.info(f"  Users: {advanced_config.users}")
    logger.info(f"  Spawn rate: {advanced_config.spawn_rate}")
    logger.info(f"  Duration: {advanced_config.duration}s")
    logger.info(f"  HTML report: {advanced_config.html_report}")
    logger.info(f"  CSV prefix: {advanced_config.csv_prefix}")
    logger.info(f"  Tags: {advanced_config.tags}")
    logger.info(f"  Exclude tags: {advanced_config.exclude_tags}")
    logger.info(f"  Custom options: {advanced_config.custom_options}")
    
    return basic_config, advanced_config


def demo_performance_test_execution():
    """演示性能测试执行"""
    logger.info("=== Performance Test Execution Demo ===")
    
    if not LOCUST_AVAILABLE:
        logger.warning("Skipping execution demo - Locust not available")
        return None
    
    # 使用httpbin.org作为测试目标（公共HTTP测试服务）
    config = PerformanceTestConfig(
        target_url="http://httpbin.org",
        users=2,  # 少量用户避免对公共服务造成压力
        spawn_rate=1.0,
        duration=10,  # 短时间测试
        test_name="demo_execution"
    )
    
    logger.info(f"Starting performance test: {config.test_name}")
    logger.info(f"Target: {config.target_url}")
    logger.info(f"Configuration: {config.users} users, {config.duration}s duration")
    
    start_time = time.time()
    
    try:
        # 运行性能测试
        result = run_performance_test(config)
        
        execution_time = time.time() - start_time
        
        logger.info(f"Test completed in {execution_time:.2f}s")
        logger.info(f"Status: {result.status}")
        logger.info(f"Duration: {result.duration:.2f}s")
        
        # 显示度量信息
        metrics = result.metrics
        logger.info(f"\n📊 Performance Metrics:")
        logger.info(f"  Total requests: {metrics.total_requests}")
        logger.info(f"  Failed requests: {metrics.failed_requests}")
        logger.info(f"  Success rate: {metrics.success_rate:.1f}%")
        logger.info(f"  Average response time: {metrics.average_response_time:.2f}ms")
        logger.info(f"  Requests per second: {metrics.requests_per_second:.2f}")
        
        # 显示错误信息（如果有）
        if result.errors:
            logger.warning(f"\n⚠️ Errors found ({len(result.errors)}):")
            for error in result.errors[:3]:  # 只显示前3个错误
                logger.warning(f"  - {error.get('message', 'Unknown error')}")
        
        # 显示原始输出的摘要
        if result.raw_output:
            lines = result.raw_output.split('\n')
            logger.info(f"\nRaw output: {len(lines)} lines")
            # 查找关键输出行
            for line in lines:
                if any(keyword in line.lower() for keyword in ['requests', 'rps', 'response time', 'error']):
                    logger.info(f"  {line.strip()}")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Performance test failed after {execution_time:.2f}s: {e}")
        return None


def demo_performance_report_generation():
    """演示性能测试报告生成"""
    logger.info("=== Performance Report Generation Demo ===")
    
    # 创建模拟测试结果
    from src.phoenixframe.performance import (
        PerformanceTestResult, PerformanceMetrics
    )
    from datetime import datetime
    
    # 模拟结果1
    config1 = PerformanceTestConfig(
        target_url="http://api.example.com",
        users=10,
        duration=60,
        test_name="api_load_test"
    )
    
    metrics1 = PerformanceMetrics(
        total_requests=1000,
        failed_requests=5,
        average_response_time=150.5,
        min_response_time=50.0,
        max_response_time=500.0,
        median_response_time=120.0,
        p95_response_time=300.0,
        p99_response_time=450.0,
        requests_per_second=16.7,
        failures_per_second=0.08,
        test_duration=60.0,
        success_rate=99.5,
        error_rate=0.5
    )
    
    result1 = PerformanceTestResult(
        test_name="api_load_test",
        status="success",
        start_time=datetime.now(),
        end_time=datetime.now(),
        duration=60.0,
        config=config1,
        metrics=metrics1,
        errors=[],
        raw_output="Test completed successfully"
    )
    
    # 模拟结果2
    config2 = PerformanceTestConfig(
        target_url="http://web.example.com",
        users=50,
        duration=120,
        test_name="web_stress_test"
    )
    
    metrics2 = PerformanceMetrics(
        total_requests=5000,
        failed_requests=50,
        average_response_time=200.0,
        min_response_time=80.0,
        max_response_time=1000.0,
        median_response_time=180.0,
        p95_response_time=400.0,
        p99_response_time=800.0,
        requests_per_second=41.7,
        failures_per_second=0.42,
        test_duration=120.0,
        success_rate=99.0,
        error_rate=1.0
    )
    
    result2 = PerformanceTestResult(
        test_name="web_stress_test",
        status="success",
        start_time=datetime.now(),
        end_time=datetime.now(),
        duration=120.0,
        config=config2,
        metrics=metrics2,
        errors=[
            {"type": "timeout", "message": "Request timeout", "count": 10},
            {"type": "connection", "message": "Connection failed", "count": 5}
        ],
        raw_output="Test completed with some errors"
    )
    
    # 生成报告
    from src.phoenixframe.performance import generate_performance_report
    
    results = [result1, result2]
    
    # 生成JSON报告
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        report_path = f.name
    
    try:
        report_json = generate_performance_report(results, report_path)
        
        logger.info(f"Generated performance report: {report_path}")
        
        # 解析并显示报告摘要
        import json
        report_data = json.loads(report_json)
        
        summary = report_data['summary']
        logger.info(f"\n📋 Report Summary:")
        logger.info(f"  Total tests: {summary['total_tests']}")
        logger.info(f"  Passed tests: {summary['passed_tests']}")
        logger.info(f"  Failed tests: {summary['failed_tests']}")
        logger.info(f"  Success rate: {summary['success_rate']:.1f}%")
        logger.info(f"  Total requests: {summary['total_requests']}")
        logger.info(f"  Overall success rate: {summary['overall_success_rate']:.1f}%")
        logger.info(f"  Average response time: {summary['average_response_time']:.1f}ms")
        logger.info(f"  Average RPS: {summary['average_rps']:.1f}")
        
        # 显示各个测试的详情
        logger.info(f"\n📊 Test Details:")
        for test in report_data['tests']:
            logger.info(f"  {test['test_name']}:")
            logger.info(f"    Status: {test['status']}")
            logger.info(f"    Duration: {test['duration']:.1f}s")
            logger.info(f"    Requests: {test['metrics']['total_requests']}")
            logger.info(f"    Success rate: {test['metrics']['success_rate']:.1f}%")
            logger.info(f"    Avg response time: {test['metrics']['average_response_time']:.1f}ms")
        
        return report_path
        
    except Exception as e:
        logger.error(f"Failed to generate performance report: {e}")
        return None


def main():
    """主演示函数"""
    logger.info("PhoenixFrame Performance Testing Demo")
    logger.info("=" * 50)
    
    try:
        # 检查可用性
        available = demo_performance_test_availability()
        print()
        
        # 配置演示
        basic_config, advanced_config = demo_performance_test_config()
        print()
        
        # 文件生成演示
        locustfile_path = demo_locustfile_generation()
        print()
        
        # 执行演示（仅在Locust可用时）
        if available:
            result = demo_performance_test_execution()
            print()
        else:
            logger.info("Skipping execution demo - Locust not available")
            print()
        
        # 报告生成演示
        report_path = demo_performance_report_generation()
        print()
        
        logger.info("=== Demo Summary ===")
        logger.info("✅ Performance test availability check")
        logger.info("✅ Performance test configuration")
        logger.info("✅ Locustfile generation")
        
        if available:
            logger.info("✅ Performance test execution")
        else:
            logger.info("⚠️ Performance test execution (Locust not available)")
        
        logger.info("✅ Performance report generation")
        
        logger.info("\n🎉 All performance testing features demonstrated successfully!")
        
        # CLI使用示例
        logger.info("\n📋 CLI Usage Examples:")
        logger.info("# Generate a Locust performance test file")
        logger.info("phoenix scaffold locustfile my_test --target-url http://localhost:8000 --users 10")
        logger.info("\n# Run a performance test")
        logger.info("phoenix performance run --target-url http://localhost:8000 --users 10 --duration 60")
        logger.info("\n# Generate performance test from template")
        logger.info("phoenix performance generate --target-url http://api.example.com --test-type api")
        logger.info("\n# Generate performance report")
        logger.info("phoenix performance report ./test_results --output performance_report.json")
        
        # 清理临时文件
        if locustfile_path:
            try:
                import os
                os.unlink(locustfile_path)
                logger.info(f"\nCleaned up temporary file: {locustfile_path}")
            except:
                pass
        
        if report_path:
            logger.info(f"Performance report saved at: {report_path}")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()