"""
示例性能测试脚本
演示如何使用PhoenixFrame进行性能测试
"""
import time
from src.phoenixframe.performance import (
    PerformanceTestConfig,
    run_performance_test,
    generate_locustfile,
    LOCUST_AVAILABLE
)
from src.phoenixframe.observability.logger import get_logger

# 设置日志
logger = get_logger("example_performance_test")

def main():
    """主函数"""
    logger.info("Starting performance test example")
    
    # 检查Locust是否可用
    if not LOCUST_AVAILABLE:
        logger.error("Locust is not available. Please install it with: pip install locust")
        return
    
    # 配置性能测试
    config = PerformanceTestConfig(
        target_url="http://httpbin.org",  # 公共测试API
        users=5,  # 5个并发用户
        spawn_rate=1.0,  # 每秒启动1个用户
        duration=30,  # 测试30秒
        test_name="httpbin_performance_test",
        html_report="performance_report.html",
        csv_prefix="performance_results"
    )
    
    logger.info(f"Performance test configuration:")
    logger.info(f"  Target URL: {config.target_url}")
    logger.info(f"  Users: {config.users}")
    logger.info(f"  Duration: {config.duration}s")
    logger.info(f"  Test Name: {config.test_name}")
    
    # 生成Locust测试文件
    logger.info("Generating Locust test file...")
    try:
        locustfile_content = generate_locustfile(
            config, 
            "example_performance_test.py", 
            "basic"
        )
        logger.info("Locust test file generated successfully")
        logger.info(f"Generated file: example_performance_test.py")
        
        # 显示部分生成的代码
        lines = locustfile_content.split('\n')
        logger.info("Generated code preview:")
        for i, line in enumerate(lines[:20]):  # 显示前20行
            logger.info(f"  {i+1:2d}: {line}")
        if len(lines) > 20:
            logger.info(f"  ... and {len(lines) - 20} more lines")
            
    except Exception as e:
        logger.error(f"Failed to generate Locust file: {e}")
        return
    
    # 运行性能测试
    logger.info("Running performance test...")
    try:
        result = run_performance_test(config)
        
        # 显示测试结果
        logger.info("Performance test completed!")
        logger.info(f"Test Results:")
        logger.info(f"  Status: {result.status}")
        logger.info(f"  Duration: {result.duration:.2f}s")
        logger.info(f"  Test Name: {result.test_name}")
        
        # 显示性能度量
        metrics = result.metrics
        logger.info(f"Performance Metrics:")
        logger.info(f"  Total Requests: {metrics.total_requests}")
        logger.info(f"  Failed Requests: {metrics.failed_requests}")
        logger.info(f"  Success Rate: {metrics.success_rate:.1f}%")
        logger.info(f"  Error Rate: {metrics.error_rate:.1f}%")
        logger.info(f"  Average Response Time: {metrics.average_response_time:.2f}ms")
        logger.info(f"  Requests per Second: {metrics.requests_per_second:.2f}")
        
        # 显示错误信息（如果有）
        if result.errors:
            logger.warning(f"Errors encountered ({len(result.errors)}):")
            for error in result.errors[:5]:  # 显示前5个错误
                logger.warning(f"  - {error.get('message', 'Unknown error')}")
        
        # 显示报告文件
        if result.reports:
            logger.info("Generated reports:")
            for report_type, report_path in result.reports.items():
                logger.info(f"  {report_type}: {report_path}")
        
        # 性能测试成功/失败判断
        if result.status == "success":
            logger.info("✅ Performance test completed successfully!")
            
            # 检查性能阈值
            if metrics.success_rate >= 95:
                logger.info("✅ Success rate meets threshold (>=95%)")
            else:
                logger.warning(f"⚠️  Success rate below threshold: {metrics.success_rate:.1f}% < 95%")
                
            if metrics.average_response_time <= 2000:
                logger.info("✅ Response time meets threshold (<=2000ms)")
            else:
                logger.warning(f"⚠️  Response time above threshold: {metrics.average_response_time:.2f}ms > 2000ms")
                
        else:
            logger.error("❌ Performance test failed!")
            logger.error(f"Status: {result.status}")
            
            # 显示原始输出以便调试
            if result.raw_output:
                logger.debug("Raw output:")
                for line in result.raw_output.split('\n')[:10]:
                    logger.debug(f"  {line}")
                
    except Exception as e:
        logger.error(f"Performance test failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("Performance test example completed")


def demonstrate_test_generation():
    """演示测试生成功能"""
    logger.info("Demonstrating test generation...")
    
    # 生成基础性能测试
    config = PerformanceTestConfig(
        target_url="http://api.example.com",
        test_name="api_load_test",
        users=10,
        duration=60
    )
    
    try:
        # 生成不同类型的测试
        basic_test = generate_locustfile(config, "demo_basic_test.py", "basic")
        logger.info("Generated basic performance test")
        
        # 显示生成的测试特点
        logger.info("Basic test includes:")
        logger.info("  - Home page loading")
        logger.info("  - API health checks")
        logger.info("  - POST data submission")
        logger.info("  - User workflow simulation")
        
    except Exception as e:
        logger.error(f"Failed to generate demo tests: {e}")


if __name__ == "__main__":
    print("PhoenixFrame Performance Testing Example")
    print("=" * 50)
    
    # 检查依赖
    if not LOCUST_AVAILABLE:
        print("❌ Locust is not available!")
        print("Please install it with: pip install locust")
        print("Then run this example again.")
        exit(1)
    
    print("✅ Locust is available")
    print("Starting performance test demonstration...")
    print()
    
    # 运行示例
    try:
        demonstrate_test_generation()
        print()
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Performance test interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nPerformance test example finished.")