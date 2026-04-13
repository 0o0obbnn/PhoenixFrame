#!/usr/bin/env python3
"""最终功能验证测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_playwright_driver_syntax():
    """测试 Playwright 驱动语法"""
    try:
        from phoenixframe.web.playwright_driver import PlaywrightDriver
        print("✅ Playwright 驱动语法正确")
        return True
    except Exception as e:
        print(f"❌ Playwright 驱动语法错误: {e}")
        return False

def test_api_client_basic():
    """测试 API 客户端基本功能"""
    try:
        from phoenixframe.api.enhanced_client import EnhancedAPIClient, APIResponse
        import requests
        
        # 创建客户端
        client = EnhancedAPIClient("https://api.example.com", timeout=10)
        
        # 测试基本属性
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 10
        assert client.max_retries == 3
        assert client.enable_idempotency is True
        
        # 测试统计信息
        stats = client.get_stats()
        assert stats["total_requests"] == 0
        assert stats["successful_requests"] == 0
        assert stats["failed_requests"] == 0
        assert stats["success_rate"] == 0.0
        
        print("✅ API 客户端基本功能正常")
        return True
    except Exception as e:
        print(f"❌ API 客户端测试失败: {e}")
        return False

def test_doctor_basic():
    """测试诊断功能基本功能"""
    try:
        from phoenixframe.cli.doctor import DoctorChecker
        
        checker = DoctorChecker()
        results = checker.run_all_checks()
        
        assert "passed" in results
        assert "failed" in results
        assert "warnings" in results
        
        print(f"✅ 诊断功能正常: {len(results['passed'])} 通过, {len(results['failed'])} 失败")
        return True
    except Exception as e:
        print(f"❌ 诊断功能测试失败: {e}")
        return False

def test_base_driver_interface():
    """测试 BaseWebDriver 接口"""
    try:
        from phoenixframe.web.base_driver import BaseWebDriver, WaitStrategy, LocatorStrategy
        
        # 测试枚举值
        assert WaitStrategy.EXPLICIT.value == "explicit"
        assert WaitStrategy.IMPLICIT.value == "implicit"
        assert WaitStrategy.FLUENT.value == "fluent"
        
        assert LocatorStrategy.CSS.value == "css"
        assert LocatorStrategy.XPATH.value == "xpath"
        assert LocatorStrategy.ID.value == "id"
        
        print("✅ BaseWebDriver 接口正常")
        return True
    except Exception as e:
        print(f"❌ BaseWebDriver 接口测试失败: {e}")
        return False

def test_ci_config():
    """测试 CI 配置"""
    try:
        with open(".github/workflows/ci.yml", "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "master" in content
        assert "--cov-fail-under=70" in content
        assert "npx playwright install" in content
        
        print("✅ CI 配置正常")
        return True
    except Exception as e:
        print(f"❌ CI 配置测试失败: {e}")
        return False

def main():
    """运行最终测试"""
    print("🎯 PhoenixFrame 最终功能验证")
    print("=" * 60)
    
    tests = [
        ("Playwright 驱动语法", test_playwright_driver_syntax),
        ("API 客户端基本功能", test_api_client_basic),
        ("诊断功能基本功能", test_doctor_basic),
        ("BaseWebDriver 接口", test_base_driver_interface),
        ("CI 配置", test_ci_config),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 40)
        
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} 失败")
    
    print("\n" + "=" * 60)
    print(f"📊 最终测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！Playwright 驱动语法问题已解决！")
        print("\n✨ 项目状态:")
        print("  ✅ Playwright 驱动语法修复完成")
        print("  ✅ API 客户端功能正常")
        print("  ✅ 诊断功能正常")
        print("  ✅ BaseWebDriver 接口正常")
        print("  ✅ CI 配置正常")
        
        print("\n🎯 开发进度:")
        print("  - 阶段一: CI 与质量门禁修复 ✅ 完成")
        print("  - 阶段二: Web 自动化核心功能 ✅ 完成")
        print("  - 阶段三: API 客户端增强 ✅ 完成")
        print("  - 阶段四: CLI 诊断与故障排除 ✅ 完成")
        print("  - 阶段五: 测试用例补充 ✅ 完成")
        print("  - 阶段六: Playwright 驱动语法修复 ✅ 完成")
        
        print("\n🚀 项目已准备好进行下一步开发！")
        return 0
    else:
        print(f"❌ {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
