"""报告系统使用示例

演示如何使用PhoenixFrame的报告系统：
- 自动数据收集
- 手动报告生成
- 自定义报告格式
- 集成测试框架
"""

import time
import random
from datetime import datetime, timedelta
from pathlib import Path

from ..observability import (
    get_report_collector, ReportManager, TestResult, TestSuite, 
    ReportSummary, TestReport, test_context, suite_context
)
from ..core.lifecycle import global_lifecycle_manager
from ..observability.logger import get_logger


logger = get_logger(__name__)


def demo_basic_reporting():
    """基本报告功能演示"""
    print("=== 基本报告功能演示 ===")
    
    # 获取报告收集器
    collector = get_report_collector()
    
    # 配置收集器
    collector.configure(
        auto_screenshot=True,
        collect_logs=True,
        collect_metrics=True,
        max_log_entries=100
    )
    
    # 使用上下文管理器自动管理测试套件
    with suite_context("登录功能测试", {"component": "authentication", "priority": "high"}):
        
        # 测试用例1：成功登录
        with test_context("用户名密码登录成功", {"username": "testuser", "password": "****"}):
            time.sleep(0.1)  # 模拟测试执行
            collector.add_log("开始登录测试")
            collector.add_log("输入用户名和密码")
            collector.add_log("点击登录按钮")
            collector.add_test_data("login_time", 1.5)
            collector.add_metadata("browser", "Chrome")
            collector.add_log("登录成功")
        
        # 测试用例2：密码错误
        with test_context("错误密码登录失败", {"username": "testuser", "password": "wrong"}):
            time.sleep(0.05)
            collector.add_log("开始错误密码测试")
            collector.add_log("输入错误密码")
            collector.fail_test("密码验证失败", "Expected error: Invalid credentials")
        
        # 测试用例3：跳过的测试
        with test_context("社交媒体登录", {"provider": "google"}):
            collector.skip_test("社交媒体登录功能未实现")
    
    # 生成报告
    report = collector.generate_report(
        environment_info={
            "os": "Windows 10",
            "browser": "Chrome 91.0",
            "resolution": "1920x1080"
        },
        config_info={
            "timeout": 30,
            "retry_attempts": 3
        }
    )
    
    # 输出报告摘要
    print(f"测试总数: {report.summary.total_tests}")
    print(f"通过: {report.summary.passed_tests}")
    print(f"失败: {report.summary.failed_tests}")
    print(f"跳过: {report.summary.skipped_tests}")
    print(f"成功率: {report.summary.success_rate:.1f}%")
    
    return report


def demo_manual_reporting():
    """手动创建报告演示"""
    print("\n=== 手动创建报告演示 ===")
    
    # 手动创建测试数据
    test_data = []
    
    for i in range(5):
        start_time = datetime.now() - timedelta(minutes=5-i)
        end_time = start_time + timedelta(seconds=random.uniform(0.5, 3.0))
        
        status = random.choice(["passed", "passed", "passed", "failed", "skipped"])
        
        test = TestResult(
            name=f"测试用例_{i+1}",
            status=status,
            start_time=start_time,
            end_time=end_time,
            error_message="模拟错误信息" if status == "failed" else None,
            test_data={"iteration": i+1, "data_size": random.randint(100, 1000)},
            screenshots=["screenshot1.png"] if status == "failed" else [],
            logs=[f"日志条目 {j}" for j in range(random.randint(3, 8))],
            metadata={"priority": random.choice(["high", "medium", "low"])}
        )
        test_data.append(test)
    
    # 创建测试套件
    suite = TestSuite(
        name="API接口测试",
        tests=test_data,
        start_time=min(t.start_time for t in test_data),
        end_time=max(t.end_time for t in test_data),
        metadata={"api_version": "v2.1", "environment": "staging"}
    )
    
    # 计算套件统计
    suite.duration = (suite.end_time - suite.start_time).total_seconds()
    
    # 创建报告摘要
    summary = ReportSummary(
        total_suites=1,
        total_tests=suite.total_tests,
        passed_tests=suite.passed_tests,
        failed_tests=suite.failed_tests,
        skipped_tests=suite.skipped_tests,
        error_tests=suite.error_tests,
        total_duration=suite.duration,
        start_time=suite.start_time,
        end_time=suite.end_time,
        environment={"server": "staging.example.com", "version": "1.2.3"},
        config={"timeout": 60, "retries": 2}
    )
    
    # 创建完整报告
    report = TestReport(
        summary=summary,
        suites=[suite],
        metadata={"created_by": "manual_demo", "report_type": "api_test"}
    )
    
    print(f"手动创建的报告 - 测试数: {report.summary.total_tests}, "
          f"成功率: {report.summary.success_rate:.1f}%")
    
    return report


def demo_report_generation(report: TestReport):
    """报告生成演示"""
    print("\n=== 报告生成演示 ===")
    
    # 创建报告管理器
    manager = ReportManager("demo_reports")
    
    # 生成多种格式的报告
    try:
        report_files = manager.generate_report(
            report,
            formats=['html', 'json', 'xml'],
            filename_base='demo_test_report'
        )
        
        print("生成的报告文件:")
        for format_name, file_path in report_files.items():
            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
            print(f"  {format_name.upper()}: {file_path} ({file_size} bytes)")
            
    except Exception as e:
        logger.error(f"报告生成失败: {e}")


def demo_lifecycle_integration():
    """生命周期集成演示"""
    print("\n=== 生命周期集成演示 ===")
    
    # 获取全局生命周期管理器
    lifecycle = global_lifecycle_manager
    
    # 注册报告收集器作为生命周期监听器
    collector = get_report_collector()
    lifecycle.add_listener(collector)
    
    # 模拟会话开始
    session = lifecycle.create_session("集成测试会话")
    
    try:
        # 添加一些资源
        session.add_resource("test_resource_1", {"type": "test", "name": "集成测试1"})
        time.sleep(0.1)
        
        # 模拟错误
        try:
            raise ValueError("模拟的测试错误")
        except Exception as e:
            session.handle_error(e, {"test_name": "集成测试1"})
        
        # 移除资源（触发测试结束）
        session.remove_resource("test_resource_1", {"status": "error"})
        
    finally:
        # 清理会话
        session.dispose()
    
    # 生成集成测试报告
    integration_report = collector.generate_report()
    print(f"集成测试报告 - 测试数: {integration_report.summary.total_tests}")
    
    return integration_report


def demo_custom_report_callbacks():
    """自定义报告回调演示"""
    print("\n=== 自定义报告回调演示 ===")
    
    collector = get_report_collector()
    
    # 定义回调函数
    def on_test_started(test: TestResult):
        print(f"📝 测试开始: {test.name}")
    
    def on_test_completed(test: TestResult):
        status_emoji = {"passed": "✅", "failed": "❌", "skipped": "⏭️", "error": "💥"}
        emoji = status_emoji.get(test.status, "❓")
        print(f"{emoji} 测试完成: {test.name} ({test.status})")
    
    def on_suite_completed(suite: TestSuite):
        print(f"📊 套件完成: {suite.name} - "
              f"{suite.passed_tests}通过/{suite.total_tests}总计 "
              f"({suite.success_rate:.1f}%)")
    
    def on_report_generated(report: TestReport):
        print(f"📄 报告生成完成 - {report.summary.total_tests}个测试")
    
    # 注册回调
    collector.add_callback('test_started', on_test_started)
    collector.add_callback('test_completed', on_test_completed)
    collector.add_callback('suite_completed', on_suite_completed)
    collector.add_callback('report_generated', on_report_generated)
    
    # 执行一些测试来触发回调
    with suite_context("回调演示测试"):
        with test_context("回调测试1"):
            time.sleep(0.05)
        
        with test_context("回调测试2"):
            collector.fail_test("故意失败的测试")
            time.sleep(0.03)
    
    # 生成报告（触发回调）
    report = collector.generate_report()
    return report


def run_all_demos():
    """运行所有演示"""
    print("🚀 开始PhoenixFrame报告系统演示")
    print("="*50)
    
    try:
        # 基本报告功能
        report1 = demo_basic_reporting()
        
        # 手动创建报告
        report2 = demo_manual_reporting()
        
        # 报告生成
        demo_report_generation(report1)
        
        # 生命周期集成
        report3 = demo_lifecycle_integration()
        
        # 自定义回调
        report4 = demo_custom_report_callbacks()
        
        print("\n" + "="*50)
        print("✅ 所有演示完成！")
        
        # 生成综合报告
        all_reports = [report1, report2, report3, report4]
        return all_reports
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    run_all_demos()