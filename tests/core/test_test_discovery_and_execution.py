"""
测试用例发现和执行测试

测试PhoenixFrame核心引擎优化功能，
包括智能测试发现和执行计划创建。
"""

import tempfile
import time
from pathlib import Path
import pytest

from src.phoenixframe.core.runner import PhoenixRunner
from src.phoenixframe.core.test_executor import TestCase, TestSuite, ExecutionConfig, ExecutionStrategy, TestExecutor


class TestTestDiscoveryAndExecution:
    """测试发现和执行测试"""
    
    def test_test_discovery_from_directory(self):
        """测试从目录发现测试用例"""
        runner = PhoenixRunner()
        
        # 创建临时测试目录和文件
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
'''
            
            test_file = test_dir / "test_math.py"
            test_file.write_text(test_file_content, encoding='utf-8')
            
            # 发现测试
            test_suites = runner.discover_tests([str(test_dir)])
            
            # 验证结果
            assert len(test_suites) == 1
            assert test_suites[0].name == "test_math"
            assert len(test_suites[0].test_cases) == 2
            
            test_case_names = [tc.name for tc in test_suites[0].test_cases]
            assert "test_addition" in test_case_names
            assert "test_subtraction" in test_case_names
    
    def test_test_discovery_from_file(self):
        """测试从文件发现测试用例"""
        runner = PhoenixRunner()
        
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write('''
def test_multiplication():
    """测试乘法"""
    assert 3 * 4 == 12

def test_division():
    """测试除法"""
    assert 10 / 2 == 5
''')
            temp_file_path = f.name
        
        try:
            # 发现测试
            test_suites = runner.discover_tests([temp_file_path])
            
            # 验证结果
            assert len(test_suites) == 1
            assert len(test_suites[0].test_cases) == 2
            
            test_case_names = [tc.name for tc in test_suites[0].test_cases]
            assert "test_multiplication" in test_case_names
            assert "test_division" in test_case_names
        finally:
            # 清理临时文件
            Path(temp_file_path).unlink()
    
    def test_execution_plan_creation(self):
        """测试执行计划创建"""
        runner = PhoenixRunner()
        
        # 创建测试套件
        test_cases = [
            TestCase(name="test_case_1", func=lambda: None),
            TestCase(name="test_case_2", func=lambda: None)
        ]
        
        test_suite = TestSuite(
            name="test_suite",
            test_cases=test_cases
        )
        
        # 创建执行计划
        execution_plan = runner.create_execution_plan([test_suite])
        
        # 验证结果
        assert len(execution_plan['suites']) == 1
        assert execution_plan['total_tests'] == 2
        assert execution_plan['strategy'] in ['adaptive', 'sequential', 'thread_pool', 'process_pool']
        assert isinstance(execution_plan['max_workers'], int)
        assert execution_plan['has_dependencies'] is False
    
    def test_execution_plan_with_dependencies(self):
        """测试带有依赖关系的执行计划"""
        runner = PhoenixRunner()
        
        # 创建带依赖的测试套件
        test_cases = [
            TestCase(name="test_case_1", func=lambda: None),
            TestCase(name="test_case_2", func=lambda: None, dependencies=["test_case_1"])
        ]
        
        test_suite = TestSuite(
            name="test_suite",
            test_cases=test_cases
        )
        
        # 创建执行计划
        execution_plan = runner.create_execution_plan([test_suite])
        
        # 验证结果 - 有依赖时应该使用顺序执行
        assert execution_plan['has_dependencies'] is True
    
    def test_direct_function_execution(self):
        """测试直接函数执行"""
        runner = PhoenixRunner()
        
        # 创建测试函数
        def passing_test():
            assert True
        
        def failing_test():
            assert False, "故意失败"
        
        # 执行测试
        test_functions = [passing_test, failing_test]
        result = runner.run_tests(test_functions=test_functions)
        
        # 验证结果
        assert result['passed_count'] == 1
        assert result['failed_count'] == 1
        assert len(result['errors']) == 1
    
    def test_test_executor_execution(self):
        """测试测试执行器执行"""
        # 创建执行配置
        config = ExecutionConfig(
            strategy=ExecutionStrategy.THREAD_POOL,
            max_workers=2
        )
        
        # 创建执行器
        executor = TestExecutor(config)
        
        # 创建测试套件
        def sample_test():
            time.sleep(0.1)  # 模拟耗时操作
            assert 1 + 1 == 2
        
        test_cases = [
            TestCase(name="test_1", func=sample_test),
            TestCase(name="test_2", func=sample_test)
        ]
        
        test_suite = TestSuite(
            name="sample_suite",
            test_cases=test_cases
        )
        
        # 添加测试套件
        executor.add_test_suite(test_suite)
        
        # 执行测试
        results = executor.execute()
        
        # 验证结果
        assert len(results) == 2
        assert all(r.status.name == 'COMPLETED' for r in results.values())


def test_backward_compatibility():
    """测试向后兼容性"""
    from src.phoenixframe.core.runner import PhoenixRunner
    
    runner = PhoenixRunner()
    
    # 测试旧的API仍然可用
    def sample_test():
        assert True
    
    result = runner.run_tests(test_functions=[sample_test])
    assert result['passed_count'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])