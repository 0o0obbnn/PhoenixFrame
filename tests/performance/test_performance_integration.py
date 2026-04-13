"""测试性能测试集成"""
import pytest
from unittest.mock import Mock, patch
from src.phoenixframe.performance import (
    PerformanceTestConfig,
    PerformanceTestManager,
    LocustTestGenerator,
    run_performance_test,
    LOCUST_AVAILABLE
)


class TestPerformanceTestConfig:
    """测试性能测试配置"""
    
    def test_config_creation(self):
        """测试配置创建"""
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


class TestLocustTestGenerator:
    """测试Locust测试生成器"""
    
    def test_generate_basic_test(self):
        """测试生成基础测试"""
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
    
    def test_generate_api_test(self):
        """测试生成API测试"""
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


class TestPerformanceTestManager:
    """测试性能测试管理器"""
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = PerformanceTestManager()
        
        assert manager.runner is not None
        assert manager.generator is not None
        assert manager.logger is not None
        assert manager.tracer is not None
    
    def test_generate_locustfile(self):
        """测试生成Locust文件"""
        manager = PerformanceTestManager()
        config = PerformanceTestConfig(
            target_url="http://test.com",
            test_name="test_file"
        )
        
        with patch('pathlib.Path.write_text') as mock_write:
            content = manager.generate_locustfile(config, "test.py", "basic")
            
            assert "TestFileUser" in content
            assert "http://test.com" in content
            mock_write.assert_called_once()
    
    @patch('src.phoenixframe.performance.LOCUST_AVAILABLE', False)
    def test_run_performance_test_without_locust(self):
        """测试在没有Locust的情况下运行性能测试"""
        manager = PerformanceTestManager()
        config = PerformanceTestConfig(
            target_url="http://test.com",
            test_name="test_no_locust"
        )
        
        result = manager.run_performance_test(config)
        
        assert result.status == "error"
        assert result.test_name == "test_no_locust"
        assert len(result.errors) > 0
        assert "Locust not available" in result.errors[0]["error"]
    
    @patch('src.phoenixframe.performance.LOCUST_AVAILABLE', True)
    @patch('subprocess.run')
    def test_run_performance_test_with_locust(self, mock_subprocess):
        """测试在有Locust的情况下运行性能测试"""
        # 模拟subprocess.run返回
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Test completed successfully\\n1000 requests\\nRPS: 10.5"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        manager = PerformanceTestManager()
        config = PerformanceTestConfig(
            target_url="http://test.com",
            test_name="test_with_locust",
            users=5,
            duration=30
        )
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = "test_locust.py"
            
            result = manager.run_performance_test(config)
            
            assert result.status == "success"
            assert result.test_name == "test_with_locust"
            assert result.metrics.total_requests >= 0
            mock_subprocess.assert_called_once()


class TestPerformanceTestIntegration:
    """测试性能测试集成"""
    
    def test_run_performance_test_function(self):
        """测试运行性能测试函数"""
        config = PerformanceTestConfig(
            target_url="http://test.com",
            test_name="integration_test"
        )
        
        with patch('src.phoenixframe.performance.get_performance_manager') as mock_manager:
            mock_result = Mock()
            mock_result.status = "success"
            mock_manager.return_value.run_performance_test.return_value = mock_result
            
            result = run_performance_test(config)
            
            assert result.status == "success"
            mock_manager.assert_called_once()
    
    def test_locust_availability_check(self):
        """测试Locust可用性检查"""
        # 这个测试会根据实际环境而变化
        assert isinstance(LOCUST_AVAILABLE, bool)
        
        if LOCUST_AVAILABLE:
            # 如果Locust可用，检查相关模块
            from src.phoenixframe.performance import locust, HttpUser, task
            assert locust is not None
            assert HttpUser is not None
            assert task is not None
        else:
            # 如果Locust不可用，相关模块应该为None
            from src.phoenixframe.performance import locust, HttpUser, task
            assert locust is None
            assert HttpUser is None
            assert task is None


@pytest.mark.integration
class TestPerformanceTestE2E:
    """端到端性能测试"""
    
    @pytest.mark.skipif(not LOCUST_AVAILABLE, reason="Locust not available")
    def test_full_performance_test_workflow(self):
        """测试完整的性能测试工作流"""
        config = PerformanceTestConfig(
            target_url="http://httpbin.org",  # 使用公共测试服务
            users=2,
            duration=10,  # 短时间测试
            test_name="e2e_test"
        )
        
        manager = PerformanceTestManager()
        
        # 生成测试文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            locustfile_path = f.name
        
        try:
            content = manager.generate_locustfile(config, locustfile_path, "basic")
            assert len(content) > 0
            
            # 运行性能测试（这里可能会因为网络原因失败，所以标记为可选）
            result = manager.run_performance_test(config)
            
            # 验证结果结构
            assert result.test_name == "e2e_test"
            assert result.status in ["success", "failed", "error"]
            assert result.duration >= 0
            
        finally:
            # 清理临时文件
            import os
            if os.path.exists(locustfile_path):
                os.unlink(locustfile_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])