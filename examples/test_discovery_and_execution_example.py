"""
测试发现和执行示例

展示如何使用PhoenixFrame的核心引擎优化功能，
包括智能测试发现和执行计划创建。
"""

import time
import tempfile
from pathlib import Path
from src.phoenixframe.core.runner import PhoenixRunner
from src.phoenixframe.core.test_executor import TestCase, TestSuite


def sample_test_function_1():
    """示例测试函数1"""
    print("执行测试函数1")
    assert 1 + 1 == 2


def sample_test_function_2():
    """示例测试函数2"""
    print("执行测试函数2")
    assert "hello".upper() == "HELLO"


def sample_test_function_3():
    """示例测试函数3"""
    print("执行测试函数3")
    time.sleep(0.1)  # 模拟耗时操作
    assert len([1, 2, 3]) == 3


def sample_failing_test():
    """示例失败测试函数"""
    print("执行失败测试函数")
    assert False, "这是故意的失败"


def example_test_discovery():
    """测试发现示例"""
    print("=== 测试发现示例 ===")
    
    # 创建PhoenixRunner实例
    runner = PhoenixRunner()
    
    # 创建临时测试文件
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "tests"
        test_dir.mkdir()
        
        # 创建示例测试文件
        test_file_content = '''
"""示例测试文件"""

def test_addition():
    """测试加法"""
    assert 2 + 2 == 4

def test_subtraction():
    """测试减法"""
    assert 5 - 3 == 2

def test_string_operations():
    """测试字符串操作"""
    assert "hello" + " world" == "hello world"
'''
        
        test_file = test_dir / "test_math.py"
        test_file.write_text(test_file_content, encoding='utf-8')
        
        # 发现测试
        test_suites = runner.discover_tests([str(test_dir)])
        
        print(f"发现 {len(test_suites)} 个测试套件:")
        for suite in test_suites:
            print(f"  - 套件: {suite.name} ({len(suite.test_cases)} 个测试用例)")
            for test_case in suite.test_cases:
                print(f"    - 测试: {test_case.name}")
        
        return test_suites


def example_execution_plan():
    """执行计划示例"""
    print("\n=== 执行计划示例 ===")
    
    # 创建测试套件
    test_cases = [
        TestCase(name="test_function_1", func=sample_test_function_1),
        TestCase(name="test_function_2", func=sample_test_function_2),
        TestCase(name="test_function_3", func=sample_test_function_3, timeout=5.0),
        TestCase(name="test_failing", func=sample_failing_test, retry_attempts=2)
    ]
    
    test_suite = TestSuite(
        name="sample_suite",
        test_cases=test_cases
    )
    
    # 创建PhoenixRunner实例
    runner = PhoenixRunner()
    
    # 创建执行计划
    execution_plan = runner.create_execution_plan([test_suite])
    
    print("执行计划:")
    print(f"  - 测试套件数量: {len(execution_plan['suites'])}")
    print(f"  - 总测试数量: {execution_plan['total_tests']}")
    print(f"  - 执行策略: {execution_plan['strategy']}")
    print(f"  - 最大工作线程数: {execution_plan['max_workers']}")
    print(f"  - 是否有依赖关系: {execution_plan['has_dependencies']}")


def example_test_execution():
    """测试执行示例"""
    print("\n=== 测试执行示例 ===")
    
    # 创建测试套件
    test_cases = [
        TestCase(name="test_function_1", func=sample_test_function_1),
        TestCase(name="test_function_2", func=sample_test_function_2),
        TestCase(name="test_function_3", func=sample_test_function_3),
        TestCase(name="test_failing", func=sample_failing_test)
    ]
    
    test_suite = TestSuite(
        name="sample_suite",
        test_cases=test_cases
    )
    
    # 创建PhoenixRunner实例
    runner = PhoenixRunner()
    
    # 执行测试
    result = runner.run_tests(test_paths=[])
    
    # 由于我们没有提供实际的测试路径，这里会使用默认的pytest模式
    # 但我们可以通过直接传递测试函数来演示新功能
    print("使用直接函数执行模式:")
    test_functions = [sample_test_function_1, sample_test_function_2, sample_test_function_3, sample_failing_test]
    result = runner.run_tests(test_functions=test_functions)
    
    print(f"执行结果:")
    print(f"  - 通过: {result['passed_count']}")
    print(f"  - 失败: {result['failed_count']}")
    if 'errors' in result:
        print(f"  - 错误数量: {len(result['errors'])}")


def main():
    """主函数"""
    print("PhoenixFrame 核心引擎优化示例")
    print("=" * 50)
    
    try:
        example_test_discovery()
        example_execution_plan()
        example_test_execution()
        
        print("\n所有示例执行完成!")
    except Exception as e:
        print(f"示例执行出错: {e}")


if __name__ == "__main__":
    main()