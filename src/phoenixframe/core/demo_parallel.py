"""并行执行系统使用示例

演示如何使用PhoenixFrame的并行执行功能：
- 并行测试执行
- 资源管理和隔离
- 性能监控和优化
- 自定义执行策略
"""

import time
import random
from datetime import datetime
from typing import Dict, Any

from ..core.parallel_executor import (
    ExecutionTask, ExecutionConfig, ExecutionStrategy, TaskPriority,
    ParallelExecutorFactory, create_task, execute_tasks_parallel
)
from ..core.test_executor import (
    TestCase, TestSuite, TestExecutor, TestDiscovery, create_test_executor,
    run_test_suite
)
from ..observability.logger import get_logger
from ..observability.report_collector import get_report_collector


logger = get_logger(__name__)


def demo_basic_parallel_execution():
    """基本并行执行演示"""
    print("=== 基本并行执行演示 ===")
    
    # 创建一些示例任务
    def sample_task(task_id: str, duration: float = 1.0, should_fail: bool = False):
        """示例任务函数"""
        logger.info(f"Task {task_id} started")
        time.sleep(duration)
        
        if should_fail:
            raise ValueError(f"Task {task_id} failed intentionally")
        
        result = f"Task {task_id} completed successfully"
        logger.info(result)
        return result
    
    # 创建任务列表
    tasks = [
        create_task("task_1", sample_task, "task_1", 0.5),
        create_task("task_2", sample_task, "task_2", 1.0),
        create_task("task_3", sample_task, "task_3", 0.8),
        create_task("task_4", sample_task, "task_4", 0.3, True),  # 故意失败
        create_task("task_5", sample_task, "task_5", 0.6),
    ]
    
    # 配置并行执行
    config = ExecutionConfig(
        strategy=ExecutionStrategy.THREAD_POOL,
        max_workers=3,
        retry_attempts=2,
        retry_delay=0.5
    )
    
    # 执行任务
    start_time = datetime.now()
    results = execute_tasks_parallel(tasks, config)
    end_time = datetime.now()
    
    # 输出结果
    duration = (end_time - start_time).total_seconds()
    print(f"执行完成，耗时: {duration:.2f}秒")
    
    for task_id, result in results.items():
        status = "✅" if result.status.value == "completed" else "❌"
        print(f"{status} {task_id}: {result.status.value} ({result.duration:.2f}s)")
        if result.error:
            print(f"   错误: {result.error}")
    
    return results


def demo_test_suite_execution():
    """测试套件并行执行演示"""
    print("\n=== 测试套件并行执行演示 ===")
    
    # 定义测试函数
    def test_login_success():
        """登录成功测试"""
        time.sleep(0.5)  # 模拟测试执行
        logger.info("Login test completed successfully")
        return {"status": "logged_in", "user": "testuser"}
    
    def test_login_failure():
        """登录失败测试"""
        time.sleep(0.3)
        logger.info("Login failure test completed")
        return {"status": "login_failed", "error": "invalid_credentials"}
    
    def test_logout():
        """登出测试"""
        time.sleep(0.2)
        logger.info("Logout test completed")
        return {"status": "logged_out"}
    
    def test_profile_update():
        """用户资料更新测试"""
        time.sleep(0.8)
        logger.info("Profile update test completed")
        return {"status": "profile_updated"}
    
    def test_password_change():
        """密码修改测试"""
        time.sleep(0.6)
        logger.info("Password change test completed")
        return {"status": "password_changed"}
    
    # 创建测试用例
    test_cases = [
        TestCase(
            name="test_login_success",
            func=test_login_success,
            priority=TaskPriority.HIGH,
            tags=["auth", "smoke"],
            metadata={"category": "authentication"}
        ),
        TestCase(
            name="test_login_failure",
            func=test_login_failure,
            priority=TaskPriority.HIGH,
            tags=["auth", "negative"],
            metadata={"category": "authentication"}
        ),
        TestCase(
            name="test_logout",
            func=test_logout,
            dependencies=["test_login_success"],  # 依赖登录成功
            tags=["auth"],
            metadata={"category": "authentication"}
        ),
        TestCase(
            name="test_profile_update",
            func=test_profile_update,
            dependencies=["test_login_success"],
            tags=["profile"],
            metadata={"category": "user_management"}
        ),
        TestCase(
            name="test_password_change",
            func=test_password_change,
            dependencies=["test_login_success"],
            tags=["security"],
            metadata={"category": "security"}
        )
    ]
    
    # 创建测试套件
    auth_suite = TestSuite(
        name="用户认证测试套件",
        test_cases=test_cases,
        parallel_execution=True,
        max_workers=3,
        metadata={"component": "authentication", "priority": "high"}
    )
    
    # 执行测试套件
    start_time = datetime.now()
    results = run_test_suite(auth_suite, max_workers=3)
    end_time = datetime.now()
    
    duration = (end_time - start_time).total_seconds()
    print(f"测试套件执行完成，耗时: {duration:.2f}秒")
    
    # 统计结果
    passed = sum(1 for r in results.values() if r.status.value == "completed")
    failed = sum(1 for r in results.values() if r.status.value == "failed")
    total = len(results)
    
    print(f"测试结果: {passed}/{total} 通过, {failed} 失败")
    
    for test_id, result in results.items():
        status = "✅" if result.status.value == "completed" else "❌"
        print(f"{status} {test_id}: {result.duration:.2f}s")
    
    return results


def demo_resource_management():
    """资源管理演示"""
    print("\n=== 资源管理演示 ===")
    
    # 模拟共享资源
    class DatabaseConnection:
        def __init__(self, name: str):
            self.name = name
            self.connected = True
            logger.info(f"Database connection created: {name}")
        
        def query(self, sql: str):
            time.sleep(0.1)  # 模拟查询
            return f"Query result from {self.name}: {sql}"
        
        def close(self):
            self.connected = False
            logger.info(f"Database connection closed: {self.name}")
    
    # 创建需要共享资源的测试
    def test_user_query(database):
        """用户查询测试"""
        result = database.query("SELECT * FROM users")
        logger.info(f"User query result: {result}")
        return result
    
    def test_product_query(database):
        """产品查询测试"""
        result = database.query("SELECT * FROM products")
        logger.info(f"Product query result: {result}")
        return result
    
    def test_order_query(database):
        """订单查询测试"""
        result = database.query("SELECT * FROM orders")
        logger.info(f"Order query result: {result}")
        return result
    
    # 创建测试用例
    test_cases = [
        TestCase(
            name="test_user_query",
            func=test_user_query,
            tags=["database", "users"]
        ),
        TestCase(
            name="test_product_query", 
            func=test_product_query,
            tags=["database", "products"]
        ),
        TestCase(
            name="test_order_query",
            func=test_order_query,
            tags=["database", "orders"]
        )
    ]
    
    # 创建带共享资源的测试套件
    db_suite = TestSuite(
        name="数据库查询测试套件",
        test_cases=test_cases,
        shared_resources={
            "database": DatabaseConnection("test_db")
        },
        parallel_execution=True,
        max_workers=2
    )
    
    # 执行测试
    results = run_test_suite(db_suite)
    
    print(f"数据库测试完成: {len(results)} 个测试")
    for test_id, result in results.items():
        status = "✅" if result.status.value == "completed" else "❌"
        print(f"{status} {test_id}")
    
    return results


def demo_adaptive_execution():
    """自适应执行演示"""
    print("\n=== 自适应执行演示 ===")
    
    # CPU密集型任务
    def cpu_intensive_task(task_id: str, iterations: int = 1000000):
        """CPU密集型任务"""
        logger.info(f"Starting CPU-intensive task: {task_id}")
        result = 0
        for i in range(iterations):
            result += i * i
        logger.info(f"CPU task {task_id} completed")
        return result
    
    # IO密集型任务
    def io_intensive_task(task_id: str, delay: float = 1.0):
        """IO密集型任务"""
        logger.info(f"Starting IO-intensive task: {task_id}")
        time.sleep(delay)  # 模拟IO等待
        logger.info(f"IO task {task_id} completed")
        return f"IO result for {task_id}"
    
    # 创建混合任务
    cpu_tasks = [
        ExecutionTask(
            task_id=f"cpu_task_{i}",
            func=cpu_intensive_task,
            args=(f"cpu_task_{i}", 500000),
            metadata={"task_type": "cpu_intensive"}
        )
        for i in range(3)
    ]
    
    io_tasks = [
        ExecutionTask(
            task_id=f"io_task_{i}",
            func=io_intensive_task,
            args=(f"io_task_{i}", 0.5),
            metadata={"task_type": "io_intensive"}
        )
        for i in range(4)
    ]
    
    all_tasks = cpu_tasks + io_tasks
    
    # 使用自适应执行策略
    config = ExecutionConfig(
        strategy=ExecutionStrategy.ADAPTIVE,
        max_workers=4
    )
    
    start_time = datetime.now()
    results = execute_tasks_parallel(all_tasks, config)
    end_time = datetime.now()
    
    duration = (end_time - start_time).total_seconds()
    print(f"自适应执行完成，耗时: {duration:.2f}秒")
    
    # 按任务类型统计
    cpu_results = [r for task_id, r in results.items() if "cpu_task" in task_id]
    io_results = [r for task_id, r in results.items() if "io_task" in task_id]
    
    cpu_avg_time = sum(r.duration for r in cpu_results) / len(cpu_results)
    io_avg_time = sum(r.duration for r in io_results) / len(io_results)
    
    print(f"CPU任务平均耗时: {cpu_avg_time:.2f}秒")
    print(f"IO任务平均耗时: {io_avg_time:.2f}秒")
    
    return results


def demo_performance_monitoring():
    """性能监控演示"""
    print("\n=== 性能监控演示 ===")
    
    # 创建测试执行器
    executor = create_test_executor(max_workers=3)
    
    # 创建一些测试任务
    def monitored_test(test_name: str, complexity: str = "simple"):
        """带监控的测试"""
        base_time = {"simple": 0.2, "medium": 0.5, "complex": 1.0}[complexity]
        variation = random.uniform(0.8, 1.2)
        time.sleep(base_time * variation)
        
        # 模拟偶尔失败
        if random.random() < 0.1:
            raise Exception(f"Random failure in {test_name}")
        
        return f"{test_name} completed ({complexity})"
    
    # 创建不同复杂度的测试
    test_cases = []
    for i in range(10):
        complexity = random.choice(["simple", "medium", "complex"])
        test_case = TestCase(
            name=f"test_performance_{i:02d}",
            func=monitored_test,
            args=(f"test_performance_{i:02d}", complexity),
            retry_attempts=1,
            metadata={"complexity": complexity}
        )
        test_cases.append(test_case)
    
    # 创建性能测试套件
    perf_suite = TestSuite(
        name="性能监控测试套件",
        test_cases=test_cases,
        parallel_execution=True,
        max_workers=3
    )
    
    executor.add_test_suite(perf_suite)
    
    # 执行并监控
    print("开始执行性能测试...")
    start_time = datetime.now()
    results = executor.execute()
    end_time = datetime.now()
    
    # 获取监控指标
    metrics = executor.monitor.get_metrics()
    duration = (end_time - start_time).total_seconds()
    
    print(f"性能测试完成:")
    print(f"  总耗时: {duration:.2f}秒")
    print(f"  任务总数: {metrics['tasks_total']}")
    print(f"  完成数: {metrics['tasks_completed']}")
    print(f"  失败数: {metrics['tasks_failed']}")
    print(f"  成功率: {metrics['success_rate']:.1f}%")
    print(f"  吞吐量: {metrics['throughput']:.2f} tests/sec")
    
    return results, metrics


def run_all_demos():
    """运行所有演示"""
    print("🚀 开始PhoenixFrame并行执行系统演示")
    print("="*60)
    
    try:
        # 基本并行执行
        demo_basic_parallel_execution()
        
        # 测试套件执行
        demo_test_suite_execution()
        
        # 资源管理
        demo_resource_management()
        
        # 自适应执行
        demo_adaptive_execution()
        
        # 性能监控
        demo_performance_monitoring()
        
        print("\n" + "="*60)
        print("✅ 所有并行执行演示完成！")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    run_all_demos()