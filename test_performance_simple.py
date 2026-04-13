"""
简单的性能测试验证脚本
不依赖pytest，直接验证功能
"""
import sys
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.phoenixframe.performance import (
    PerformanceTestConfig,
    PerformanceTestManager,
    LocustTestGenerator,
    LOCUST_AVAILABLE
)

def test_performance_test_config():
    """测试性能测试配置"""
    print("Testing PerformanceTestConfig...")
    
    config = PerformanceTestConfig(
        target_url="http://localhost:8000",
        users=5,
        duration=30,
        test_name="test_performance"
    )
    
    assert config.target_url == "http://localhost:8000"
    assert config.users == 5
    assert config.duration == 30
    assert config.test_name == "test_performance"
    assert config.spawn_rate == 1.0  # 默认值
    assert config.headless is True  # 默认值
    
    print("✅ PerformanceTestConfig test passed")


def test_locust_test_generator():
    """测试Locust测试生成器"""
    print("Testing LocustTestGenerator...")
    
    generator = LocustTestGenerator()
    config = PerformanceTestConfig(
        target_url="http://test.com",
        test_name="basic_test"
    )
    
    code = generator.generate_basic_test(config)
    
    assert "BasicTestUser" in code
    assert "http://test.com" in code
    assert "from locust import HttpUser, task, between" in code
    assert "get_home_page" in code
    assert "post_data" in code
    
    print("✅ LocustTestGenerator test passed")


def test_api_test_generation():
    """测试API测试生成"""
    print("Testing API test generation...")
    
    generator = LocustTestGenerator()
    config = PerformanceTestConfig(
        target_url="http://api.test.com",
        test_name="api_test"
    )
    
    endpoints = [
        {"method": "GET", "path": "/users", "weight": 3, "name": "get_users"},
        {"method": "POST", "path": "/users", "weight": 1, "name": "create_user"}
    ]
    
    code = generator.generate_api_test(config, endpoints)
    
    assert "ApiTestAPIUser" in code
    assert "http://api.test.com" in code
    assert "get_users" in code
    assert "create_user" in code
    assert "@task(3)" in code
    assert "@task(1)" in code
    
    print("✅ API test generation test passed")


def test_performance_test_manager():
    """测试性能测试管理器"""
    print("Testing PerformanceTestManager...")
    
    manager = PerformanceTestManager()
    
    assert manager.runner is not None
    assert manager.generator is not None
    assert manager.logger is not None
    assert manager.tracer is not None
    
    print("✅ PerformanceTestManager test passed")


def test_locust_availability():
    """测试Locust可用性检查"""
    print("Testing Locust availability...")
    
    assert isinstance(LOCUST_AVAILABLE, bool)
    print(f"Locust available: {LOCUST_AVAILABLE}")
    
    if LOCUST_AVAILABLE:
        from src.phoenixframe.performance import locust, HttpUser, task
        assert locust is not None
        assert HttpUser is not None
        assert task is not None
        print("✅ Locust components available")
    else:
        from src.phoenixframe.performance import locust, HttpUser, task
        assert locust is None
        assert HttpUser is None
        assert task is None
        print("ℹ️ Locust not available (expected)")
    
    print("✅ Locust availability test passed")


def test_generate_locustfile():
    """测试生成Locust文件"""
    print("Testing locustfile generation...")
    
    manager = PerformanceTestManager()
    config = PerformanceTestConfig(
        target_url="http://test.com",
        test_name="test_file"
    )
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        temp_file = f.name
    
    try:
        content = manager.generate_locustfile(config, temp_file, "basic")
        
        assert "TestFileUser" in content
        assert "http://test.com" in content
        
        # 检查文件是否被创建
        import os
        assert os.path.exists(temp_file)
        
        # 读取文件内容
        with open(temp_file, 'r') as f:
            file_content = f.read()
        
        assert "TestFileUser" in file_content
        
    finally:
        # 清理临时文件
        import os
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    print("✅ Locustfile generation test passed")


def test_performance_test_without_locust():
    """测试在没有Locust的情况下运行性能测试"""
    print("Testing performance test without Locust...")
    
    manager = PerformanceTestManager()
    config = PerformanceTestConfig(
        target_url="http://test.com",
        test_name="test_no_locust"
    )
    
    # 模拟Locust不可用的情况
    original_available = LOCUST_AVAILABLE
    
    try:
        # 暂时设置为不可用
        import src.phoenixframe.performance
        src.phoenixframe.performance.LOCUST_AVAILABLE = False
        
        result = manager.run_performance_test(config)
        
        assert result.status == "error"
        assert result.test_name == "test_no_locust"
        assert len(result.errors) > 0
        assert "Locust not available" in result.errors[0]["error"]
        
    finally:
        # 恢复原始状态
        src.phoenixframe.performance.LOCUST_AVAILABLE = original_available
    
    print("✅ Performance test without Locust test passed")


def main():
    """运行所有测试"""
    print("Running PhoenixFrame Performance Testing Integration Tests")
    print("=" * 60)
    
    tests = [
        test_performance_test_config,
        test_locust_test_generator,
        test_api_test_generation,
        test_performance_test_manager,
        test_locust_availability,
        test_generate_locustfile,
        test_performance_test_without_locust
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
        print()
    
    print("=" * 60)
    print(f"Test Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All performance tests passed!")
    else:
        print(f"⚠️ {failed} tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()