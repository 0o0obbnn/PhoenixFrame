#!/usr/bin/env python3
"""简单的功能测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """测试导入"""
    try:
        from phoenixframe.web.base_driver import BaseWebDriver, WaitStrategy, LocatorStrategy
        print("✅ BaseWebDriver 导入成功")
        
        from phoenixframe.api.enhanced_client import EnhancedAPIClient, APIResponse
        print("✅ EnhancedAPIClient 导入成功")
        
        from phoenixframe.cli.doctor import DoctorChecker
        print("✅ DoctorChecker 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_doctor_checker():
    """测试诊断检查器"""
    try:
        from phoenixframe.cli.doctor import DoctorChecker
        
        checker = DoctorChecker()
        results = checker.run_all_checks()
        
        print(f"✅ 诊断检查完成: {len(results['passed'])} 通过, {len(results['failed'])} 失败")
        return True
    except Exception as e:
        print(f"❌ 诊断检查失败: {e}")
        return False

def test_api_client():
    """测试 API 客户端"""
    try:
        from phoenixframe.api.enhanced_client import EnhancedAPIClient
        
        client = EnhancedAPIClient("https://api.example.com")
        stats = client.get_stats()
        
        print(f"✅ API 客户端创建成功: {stats}")
        return True
    except Exception as e:
        print(f"❌ API 客户端测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 开始简单功能测试...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_doctor_checker,
        test_api_client
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 测试结果: {passed}/{len(tests)} 通过")
    
    if passed == len(tests):
        print("🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        sys.exit(1)
