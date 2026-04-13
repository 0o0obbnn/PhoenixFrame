"""性能监控系统使用示例

演示如何使用PhoenixFrame的性能监控功能：
- 系统性能监控
- 测试性能分析
- Web自动化性能监控
- 实时性能仪表板
- 性能回归检测
"""

import time
import random
import threading
import statistics
from datetime import datetime
from typing import List

from ..observability.performance_monitor import (
    get_performance_analyzer, get_performance_profiler, 
    start_performance_monitoring, get_performance_summary,
    profile_function
)
from ..observability.performance_dashboard import (
    PerformanceDashboard, generate_performance_dashboard
)
from ..observability.performance_integration import (
    get_test_performance_monitor, get_web_performance_monitor,
    monitor_test_performance, monitor_page_load, monitor_element_operation,
    performance_monitor
)
from ..observability.logger import get_logger


logger = get_logger(__name__)


def demo_basic_performance_monitoring():
    """基本性能监控演示"""
    print("=== 基本性能监控演示 ===")
    
    # 启动性能监控
    start_performance_monitoring(
        sample_interval=0.5,  # 0.5秒采样间隔
        cpu_percent=80,       # CPU告警阈值
        memory_percent=85,    # 内存告警阈值
        memory_growth_rate=30 # 内存增长率告警阈值(MB/min)
    )
    
    print("性能监控已启动，运行5秒钟收集数据...")
    time.sleep(5)
    
    # 获取性能摘要
    summary = get_performance_summary()
    
    print(f"当前系统状态:")
    print(f"  CPU使用率: {summary['current_status']['cpu_percent']:.1f}%")
    print(f"  内存使用率: {summary['current_status']['memory_percent']:.1f}%")
    print(f"  内存使用量: {summary['current_status']['memory_used_mb']:.1f} MB")
    print(f"  磁盘使用率: {summary['current_status']['disk_usage_percent']:.1f}%")
    print(f"  活跃线程数: {summary['current_status']['thread_count']}")
    
    print(f"\n内存分析:")
    memory_profile = summary['memory_profile']
    print(f"  当前使用: {memory_profile['current_usage_mb']:.1f} MB")
    print(f"  峰值使用: {memory_profile['peak_usage_mb']:.1f} MB")
    print(f"  增长率: {memory_profile['growth_rate_mb_per_min']:.2f} MB/min")
    if memory_profile['potential_leaks']:
        print(f"  潜在泄漏: {', '.join(memory_profile['potential_leaks'])}")
    
    print(f"\nCPU分析:")
    cpu_profile = summary['cpu_profile']
    print(f"  平均使用率: {cpu_profile['avg_usage_percent']:.1f}%")
    print(f"  峰值使用率: {cpu_profile['peak_usage_percent']:.1f}%")
    if cpu_profile['bottleneck_indicators']:
        print(f"  瓶颈指标: {', '.join(cpu_profile['bottleneck_indicators'])}")
    
    # 检查活跃告警
    if summary['active_alerts']:
        print(f"\n活跃告警 ({len(summary['active_alerts'])} 个):")
        for alert in summary['active_alerts'][-3:]:  # 显示最近3个
            print(f"  [{alert['severity'].upper()}] {alert['message']}")


def demo_function_performance_profiling():
    """函数性能分析演示"""
    print("\n=== 函数性能分析演示 ===")
    
    @profile_function("fast_operation")
    def fast_operation():
        """快速操作"""
        time.sleep(0.1)
        return "fast_result"
    
    @profile_function("slow_operation")
    def slow_operation():
        """慢速操作"""
        time.sleep(0.5)
        return "slow_result"
    
    @performance_monitor("cpu_intensive", track_memory=True)
    def cpu_intensive_task():
        """CPU密集型任务"""
        result = 0
        for i in range(1000000):
            result += i * i
        return result
    
    # 执行多次操作收集性能数据
    print("执行函数性能测试...")
    
    for i in range(5):
        fast_operation()
        if i % 2 == 0:  # 偶数次执行慢操作
            slow_operation()
        if i < 2:  # 只执行2次CPU密集型任务
            cpu_intensive_task()
    
    # 获取性能分析报告
    profiler = get_performance_profiler()
    profile_summary = profiler.get_profile_summary()
    
    print("\n函数性能分析结果:")
    for func_name, stats in profile_summary.items():
        print(f"\n{func_name}:")
        print(f"  调用次数: {stats['count']}")
        print(f"  总耗时: {stats['total_time']:.3f}s")
        print(f"  平均耗时: {stats['avg_time']:.3f}s")
        print(f"  最小耗时: {stats['min_time']:.3f}s")
        print(f"  最大耗时: {stats['max_time']:.3f}s")
        print(f"  P95耗时: {stats['p95_time']:.3f}s")


def demo_test_performance_monitoring():
    """测试性能监控演示"""
    print("\n=== 测试性能监控演示 ===")
    
    def simulate_test_case(test_name: str, complexity: str):
        """模拟测试用例执行"""
        base_times = {
            "simple": (0.1, 0.5, 0.1),    # setup, execution, teardown
            "medium": (0.3, 1.0, 0.2),
            "complex": (0.5, 2.0, 0.3)
        }
        
        setup_time, exec_time, teardown_time = base_times[complexity]
        
        # 模拟setup阶段
        time.sleep(setup_time * random.uniform(0.8, 1.2))
        
        # 模拟execution阶段
        time.sleep(exec_time * random.uniform(0.8, 1.2))
        
        # 模拟teardown阶段
        time.sleep(teardown_time * random.uniform(0.8, 1.2))
        
        # 10%概率失败
        if random.random() < 0.1:
            raise Exception(f"Simulated failure in {test_name}")
    
    # 模拟多个测试用例
    test_cases = [
        ("test_login_simple", "simple"),
        ("test_search_medium", "medium"),
        ("test_checkout_complex", "complex"),
        ("test_profile_simple", "simple"),
        ("test_payment_complex", "complex")
    ]
    
    test_monitor = get_test_performance_monitor()
    
    for test_name, complexity in test_cases:
        print(f"执行测试: {test_name} ({complexity})")
        
        try:
            with monitor_test_performance(test_name) as monitor:
                # 标记setup完成
                simulate_test_case(test_name, complexity)
                
            print(f"  ✅ {test_name} 通过")
            
        except Exception as e:
            print(f"  ❌ {test_name} 失败: {e}")
    
    # 显示测试性能统计
    profiler = get_performance_profiler()
    test_profiles = {k: v for k, v in profiler.get_profile_summary().items() 
                    if k.startswith("test.")}
    
    if test_profiles:
        print(f"\n测试性能统计:")
        for test_name, stats in test_profiles.items():
            test_name = test_name.replace("test.", "")
            print(f"  {test_name}: {stats['avg_time']:.2f}s 平均 "
                  f"(最小: {stats['min_time']:.2f}s, 最大: {stats['max_time']:.2f}s)")


def demo_web_performance_monitoring():
    """Web性能监控演示"""
    print("\n=== Web性能监控演示 ===")
    
    def simulate_page_load(url: str, load_time: float):
        """模拟页面加载"""
        time.sleep(load_time * random.uniform(0.8, 1.2))
    
    def simulate_element_operation(operation: str, element: str, duration: float):
        """模拟元素操作"""
        time.sleep(duration * random.uniform(0.8, 1.2))
    
    # 模拟页面加载和操作
    pages = [
        ("https://example.com/login", 1.5),
        ("https://example.com/dashboard", 2.0),
        ("https://example.com/profile", 1.2),
        ("https://example.com/slow-page", 4.0)  # 慢页面
    ]
    
    for url, load_time in pages:
        print(f"加载页面: {url}")
        
        try:
            with monitor_page_load(url):
                simulate_page_load(url, load_time)
            
            # 模拟页面操作
            operations = [
                ("click", "#login-button", 0.2),
                ("input", "#username", 0.1),
                ("scroll", "page", 0.3),
                ("wait", ".loading", 1.0)  # 慢操作
            ]
            
            for operation, element, duration in operations[:2]:  # 只执行前2个操作
                print(f"  执行操作: {operation} on {element}")
                with monitor_element_operation(operation, element):
                    simulate_element_operation(operation, element, duration)
                    
        except Exception as e:
            print(f"  页面操作失败: {e}")
    
    # 分析Web性能
    web_monitor = get_web_performance_monitor()
    web_analysis = web_monitor.analyze_web_performance()
    
    print(f"\nWeb性能分析:")
    print(f"页面加载:")
    print(f"  总加载次数: {web_analysis['page_loads']['total_count']}")
    print(f"  平均加载时间: {web_analysis['page_loads']['avg_duration']:.2f}s")
    
    if web_analysis['page_loads']['slowest_pages']:
        print(f"  最慢页面:")
        for page, duration in web_analysis['page_loads']['slowest_pages'][:3]:
            print(f"    {page}: {duration:.2f}s")
    
    print(f"\n元素操作:")
    print(f"  总操作次数: {web_analysis['element_operations']['total_count']}")
    print(f"  平均操作时间: {web_analysis['element_operations']['avg_duration']:.2f}s")
    
    if web_analysis['element_operations']['slowest_operations']:
        print(f"  最慢操作:")
        for operation, duration in web_analysis['element_operations']['slowest_operations'][:3]:
            print(f"    {operation}: {duration:.2f}s")


def demo_performance_dashboard():
    """性能仪表板演示"""
    print("\n=== 性能仪表板演示 ===")
    
    # 生成静态仪表板
    dashboard_path = generate_performance_dashboard("demo_dashboard")
    print(f"性能仪表板已生成: {dashboard_path}")
    
    # 创建仪表板实例进行详细配置
    dashboard = PerformanceDashboard("demo_dashboard")
    
    print("仪表板功能:")
    print("  - 实时系统性能监控")
    print("  - 测试执行性能分析")
    print("  - 内存使用和泄漏检测")
    print("  - CPU性能瓶颈分析")
    print("  - 性能告警和异常检测")
    print("  - 交互式图表和可视化")
    
    # 提示用户如何启动实时仪表板
    print(f"\n要启动实时仪表板服务器，请运行:")
    print(f"  from phoenixframe.observability.performance_dashboard import start_live_dashboard")
    print(f"  start_live_dashboard(port=8080)")


def demo_performance_regression_detection():
    """性能回归检测演示"""
    print("\n=== 性能回归检测演示 ===")
    
    analyzer = get_performance_analyzer()
    
    # 建立性能基线
    print("建立性能基线（模拟2分钟数据收集）...")
    analyzer.establish_baseline(duration_minutes=0.1)  # 快速演示用6秒
    
    print(f"基线已建立: {analyzer.baseline}")
    
    # 模拟性能变化
    print("\n模拟性能变化...")
    
    # 模拟CPU和内存压力
    def create_cpu_load():
        """创建CPU负载"""
        end_time = time.time() + 2
        while time.time() < end_time:
            _ = sum(i * i for i in range(10000))
    
    def create_memory_load():
        """创建内存负载"""
        data = []
        for i in range(1000):
            data.append([random.random() for _ in range(1000)])
        time.sleep(1)
        return data
    
    # 创建负载
    cpu_thread = threading.Thread(target=create_cpu_load)
    cpu_thread.start()
    
    memory_data = create_memory_load()
    
    cpu_thread.join()
    
    # 等待收集新的性能数据
    time.sleep(2)
    
    # 检测性能回归
    regressions = analyzer.detect_performance_regression()
    
    if regressions:
        print(f"\n检测到性能回归:")
        for regression in regressions:
            print(f"  ⚠️  {regression}")
    else:
        print(f"\n✅ 未检测到显著性能回归")
    
    # 清理内存
    del memory_data


def demo_concurrent_performance_monitoring():
    """并发性能监控演示"""
    print("\n=== 并发性能监控演示 ===")
    
    def worker_task(worker_id: int):
        """工作线程任务"""
        for i in range(3):
            task_name = f"worker_{worker_id}_task_{i}"
            
            with monitor_test_performance(task_name) as monitor:
                # 模拟不同复杂度的任务
                complexity = random.choice([0.1, 0.3, 0.5])
                time.sleep(complexity)
                
                # 模拟一些操作
                with monitor_element_operation("operation", f"element_{i}"):
                    time.sleep(0.1)
            
            print(f"  Worker {worker_id} 完成任务 {i}")
    
    # 启动多个工作线程
    print("启动并发性能监控（3个工作线程）...")
    
    threads = []
    for worker_id in range(3):
        thread = threading.Thread(target=worker_task, args=(worker_id,))
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    print("并发任务完成")
    
    # 分析并发性能
    profiler = get_performance_profiler()
    profile_summary = profiler.get_profile_summary()
    
    worker_profiles = {k: v for k, v in profile_summary.items() 
                      if k.startswith("test.worker_")}
    
    if worker_profiles:
        print(f"\n并发性能统计:")
        total_tasks = sum(stats['count'] for stats in worker_profiles.values())
        avg_duration = sum(stats['avg_time'] * stats['count'] for stats in worker_profiles.values()) / total_tasks
        
        print(f"  总任务数: {total_tasks}")
        print(f"  平均任务时间: {avg_duration:.3f}s")
        print(f"  最快任务: {min(stats['min_time'] for stats in worker_profiles.values()):.3f}s")
        print(f"  最慢任务: {max(stats['max_time'] for stats in worker_profiles.values()):.3f}s")


def run_all_performance_demos():
    """运行所有性能监控演示"""
    print("🚀 开始PhoenixFrame性能监控系统演示")
    print("="*60)
    
    try:
        # 基本性能监控
        demo_basic_performance_monitoring()
        
        # 函数性能分析
        demo_function_performance_profiling()
        
        # 测试性能监控
        demo_test_performance_monitoring()
        
        # Web性能监控
        demo_web_performance_monitoring()
        
        # 性能仪表板
        demo_performance_dashboard()
        
        # 性能回归检测
        demo_performance_regression_detection()
        
        # 并发性能监控
        demo_concurrent_performance_monitoring()
        
        print("\n" + "="*60)
        print("✅ 所有性能监控演示完成！")
        
        # 最终性能摘要
        final_summary = get_performance_summary()
        print(f"\n📊 最终性能摘要:")
        print(f"  监控时长: {final_summary['monitoring_stats']['monitoring_duration_minutes']:.1f} 分钟")
        print(f"  数据点总数: {final_summary['monitoring_stats']['total_snapshots']}")
        print(f"  当前CPU: {final_summary['current_status']['cpu_percent']:.1f}%")
        print(f"  当前内存: {final_summary['current_status']['memory_percent']:.1f}%")
        
        if final_summary['active_alerts']:
            print(f"  活跃告警: {len(final_summary['active_alerts'])} 个")
        else:
            print(f"  活跃告警: 无")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    run_all_performance_demos()