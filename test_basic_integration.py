#!/usr/bin/env python3
"""
PhoenixFrame 基础集成测试

测试框架的核心启动和基础功能是否正常工作
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

def test_cli_help():
    """测试CLI help命令"""
    print("🧪 测试CLI help命令...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "src.phoenixframe.cli", "--help"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ CLI help命令正常")
            return True
        else:
            print(f"❌ CLI help命令失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ CLI help命令异常: {e}")
        return False

def test_module_imports():
    """测试核心模块导入"""
    print("🧪 测试核心模块导入...")
    
    tests = [
        ("Logger模块", "from src.phoenixframe.observability.logger import get_logger"),
        ("Tracer模块", "from src.phoenixframe.observability.tracer import get_tracer"),
        ("Config模块", "from src.phoenixframe.core.config import PhoenixConfig"),
        ("Lifecycle模块", "from src.phoenixframe.core.lifecycle import LifecycleManager"),
    ]
    
    all_passed = True
    for test_name, import_statement in tests:
        try:
            result = subprocess.run([
                sys.executable, "-c", import_statement + "; print('Import successful')"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ {test_name}导入成功")
            else:
                print(f"❌ {test_name}导入失败: {result.stderr}")
                all_passed = False
        except Exception as e:
            print(f"❌ {test_name}导入异常: {e}")
            all_passed = False
    
    return all_passed

def test_project_init():
    """测试项目初始化功能"""
    print("🧪 测试项目初始化...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test_project"
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "src.phoenixframe.cli", 
                "init", str(project_path)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # 检查是否创建了必要的文件和目录
                expected_files = [
                    "configs/phoenix.yaml",
                    "pyproject.toml",
                ]
                expected_dirs = [
                    "src/phoenixframe",
                    "tests",
                    "configs",
                    "data",
                    "docs",
                    "templates"
                ]
                
                all_exists = True
                for file_path in expected_files:
                    if not (project_path / file_path).exists():
                        print(f"❌ 缺少文件: {file_path}")
                        all_exists = False
                
                for dir_path in expected_dirs:
                    if not (project_path / dir_path).exists():
                        print(f"❌ 缺少目录: {dir_path}")
                        all_exists = False
                
                if all_exists:
                    print("✅ 项目初始化成功")
                    return True
                else:
                    print("❌ 项目初始化不完整")
                    return False
            else:
                print(f"❌ 项目初始化失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 项目初始化异常: {e}")
            return False

def test_observability_basic():
    """测试基础可观测性功能"""
    print("🧪 测试基础可观测性功能...")
    
    test_code = """
import sys
sys.path.insert(0, 'src')

try:
    from phoenixframe.observability.logger import get_logger, setup_logging
    from phoenixframe.observability.tracer import get_tracer
    
    # 测试日志
    setup_logging(level='INFO', enable_console=True, json_format=False)
    logger = get_logger('test')
    logger.info('测试日志消息')
    
    # 测试追踪
    tracer = get_tracer('test')
    with tracer.start_as_current_span('test_span'):
        logger.info('在span中的日志')
    
    print('Observability test passed')
except Exception as e:
    print(f'Observability test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    
    try:
        result = subprocess.run([
            sys.executable, "-c", test_code
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and "Observability test passed" in result.stdout:
            print("✅ 可观测性功能正常")
            return True
        else:
            print(f"❌ 可观测性功能失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 可观测性功能异常: {e}")
        return False

def main():
    """运行所有基础集成测试"""
    print("🚀 开始PhoenixFrame基础集成测试")
    print("=" * 50)
    
    tests = [
        ("CLI功能测试", test_cli_help),
        ("模块导入测试", test_module_imports),
        ("项目初始化测试", test_project_init),
        ("可观测性测试", test_observability_basic),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("🎉 所有基础集成测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败，需要进一步修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())