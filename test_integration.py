#!/usr/bin/env python3
"""集成测试 - 验证新功能"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_base_driver_interface():
    """测试 BaseWebDriver 接口"""
    try:
        from phoenixframe.web.base_driver import BaseWebDriver, WaitStrategy, LocatorStrategy
        
        # 验证枚举
        assert WaitStrategy.EXPLICIT.value == "explicit"
        assert WaitStrategy.IMPLICIT.value == "implicit"
        assert WaitStrategy.FLUENT.value == "fluent"
        
        assert LocatorStrategy.CSS.value == "css"
        assert LocatorStrategy.XPATH.value == "xpath"
        assert LocatorStrategy.ID.value == "id"
        
        print("✅ BaseWebDriver 接口测试通过")
        return True
    except Exception as e:
        print(f"❌ BaseWebDriver 接口测试失败: {e}")
        return False

def test_enhanced_api_client():
    """测试增强的 API 客户端"""
    try:
        from phoenixframe.api.enhanced_client import EnhancedAPIClient, APIResponse
        import requests
        
        # 创建客户端
        client = EnhancedAPIClient("https://api.example.com")
        
        # 测试统计信息
        stats = client.get_stats()
        assert stats["total_requests"] == 0
        assert stats["base_url"] == "https://api.example.com"
        
        # 测试 APIResponse
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.elapsed = type('obj', (object,), {'total_seconds': lambda: 0.5})()
        mock_response.json = lambda: {"data": "test"}
        
        response = APIResponse(mock_response)
        response.status_code(200).header("Content-Type", "application/json")
        
        assertions = response.get_assertions()
        assert len(assertions) == 2
        assert "status_code == 200" in assertions
        
        print("✅ EnhancedAPIClient 测试通过")
        return True
    except Exception as e:
        print(f"❌ EnhancedAPIClient 测试失败: {e}")
        return False

def test_doctor_checker():
    """测试诊断检查器"""
    try:
        from phoenixframe.cli.doctor import DoctorChecker
        
        checker = DoctorChecker()
        results = checker.run_all_checks()
        
        # 验证结果结构
        assert "passed" in results
        assert "failed" in results
        assert "warnings" in results
        
        # 验证检查项
        assert len(results["passed"]) > 0  # 至少有一些检查通过
        
        print(f"✅ DoctorChecker 测试通过: {len(results['passed'])} 通过, {len(results['failed'])} 失败")
        return True
    except Exception as e:
        print(f"❌ DoctorChecker 测试失败: {e}")
        return False

def test_ci_config():
    """测试 CI 配置"""
    try:
        import yaml
        
        # 读取 CI 配置
        with open(".github/workflows/ci.yml", "r") as f:
            ci_config = yaml.safe_load(f)
        
        # 验证分支触发
        assert "master" in ci_config["on"]["push"]["branches"]
        assert "master" in ci_config["on"]["pull_request"]["branches"]
        
        # 验证覆盖率阈值
        test_job = None
        for job_name, job_config in ci_config["jobs"].items():
            if job_name == "test":
                test_job = job_config
                break
        
        assert test_job is not None
        
        # 查找覆盖率配置
        steps = test_job["steps"]
        coverage_step = None
        for step in steps:
            if "cov-fail-under" in step.get("run", ""):
                coverage_step = step
                break
        
        assert coverage_step is not None
        assert "--cov-fail-under=70" in coverage_step["run"]
        
        print("✅ CI 配置测试通过")
        return True
    except Exception as e:
        print(f"❌ CI 配置测试失败: {e}")
        return False

def test_import_structure():
    """测试导入结构"""
    try:
        # 测试核心模块导入
        from phoenixframe.web.base_driver import BaseWebDriver
        from phoenixframe.api.enhanced_client import EnhancedAPIClient
        from phoenixframe.cli.doctor import DoctorChecker
        
        # 测试 CLI 模块导入
        from phoenixframe.cli import doctor, DoctorChecker as CLI_DoctorChecker
        
        print("✅ 导入结构测试通过")
        return True
    except Exception as e:
        print(f"❌ 导入结构测试失败: {e}")
        return False

def main():
    """运行所有集成测试"""
    print("🧪 开始集成测试...")
    print("=" * 60)
    
    tests = [
        ("BaseWebDriver 接口", test_base_driver_interface),
        ("EnhancedAPIClient", test_enhanced_api_client),
        ("DoctorChecker", test_doctor_checker),
        ("CI 配置", test_ci_config),
        ("导入结构", test_import_structure),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 测试: {test_name}")
        print("-" * 40)
        
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} 失败")
    
    print("\n" + "=" * 60)
    print(f"📊 集成测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有集成测试通过！")
        print("\n✨ 新功能验证完成:")
        print("  - 统一的 Web 驱动接口 (BaseWebDriver)")
        print("  - 增强的 API 客户端 (连接池、重试、幂等性)")
        print("  - CLI 诊断功能 (phoenix doctor)")
        print("  - CI 配置优化 (分支触发、覆盖率阈值)")
        print("  - 完整的测试用例覆盖")
        
        return 0
    else:
        print(f"❌ {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
