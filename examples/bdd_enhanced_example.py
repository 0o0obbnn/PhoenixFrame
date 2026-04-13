"""
BDD增强功能示例

这个示例展示了如何使用PhoenixFrame中增强的BDD功能，
包括pytest-bdd深度集成、HTML报告生成等。
"""

import tempfile
import os
from pathlib import Path
from src.phoenixframe.bdd import BDDIntegration
from src.phoenixframe.bdd.tools import BDDTools


def example_bdd_project_setup():
    """BDD项目设置示例"""
    print("=== BDD项目设置示例 ===")
    
    # 创建临时目录用于演示
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        print(f"在临时目录创建BDD项目: {project_root}")
        
        # 初始化BDD工具
        tools = BDDTools(str(project_root))
        
        # 初始化BDD项目结构
        tools.init_bdd_project()
        
        # 检查创建的目录和文件
        expected_dirs = [
            project_root / "features",
            project_root / "tests" / "bdd" / "steps"
        ]
        
        expected_files = [
            project_root / "features" / "sample.feature",
            project_root / "tests" / "bdd" / "steps" / "test_sample_steps.py",
            project_root / "pytest.ini"
        ]
        
        print("创建的目录:")
        for directory in expected_dirs:
            if directory.exists():
                print(f"  ✅ {directory}")
            else:
                print(f"  ❌ {directory}")
        
        print("创建的文件:")
        for file in expected_files:
            if file.exists():
                print(f"  ✅ {file}")
            else:
                print(f"  ❌ {file}")
        
        print("BDD项目设置完成!")


def example_feature_generation():
    """Feature文件生成示例"""
    print("\n=== Feature文件生成示例 ===")
    
    # 创建示例Feature内容
    feature_content = '''Feature: 用户登录功能
    作为系统用户
    我想要登录系统
    以便我可以访问我的账户

    Scenario: 成功登录
        Given 我在登录页面
        When 我输入用户名 "testuser" 和密码 "password123"
        Then 我应该被重定向到仪表板页面

    Scenario: 登录失败 - 无效凭据
        Given 我在登录页面
        When 我输入用户名 "invalid" 和密码 "wrong"
        Then 我应该看到错误消息 "用户名或密码无效"

    Scenario Outline: 登录失败 - 空字段
        Given 我在登录页面
        When 我输入用户名 "<username>" 和密码 "<password>"
        Then 我应该看到错误消息 "<error_message>"

        Examples:
            | username | password | error_message       |
            |          | pass123  | 用户名不能为空      |
            | user123  |          | 密码不能为空        |
'''

    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        features_dir = project_root / "features"
        features_dir.mkdir(parents=True)
        
        # 创建Feature文件
        feature_file = features_dir / "login.feature"
        feature_file.write_text(feature_content, encoding='utf-8')
        print(f"创建Feature文件: {feature_file}")
        
        # 初始化BDD工具
        tools = BDDTools(str(project_root))
        
        # 生成步骤定义
        generated_files = tools.generate_steps_from_features()
        print(f"生成的步骤定义文件: {generated_files}")
        
        # 显示生成的步骤定义内容
        if generated_files:
            generated_file = Path(generated_files[0])
            if generated_file.exists():
                content = generated_file.read_text(encoding='utf-8')
                print(f"\n生成的步骤定义内容 ({generated_file.name}):")
                print("=" * 50)
                print(content)
                print("=" * 50)


def example_html_report_generation():
    """HTML报告生成示例"""
    print("\n=== HTML报告生成示例 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        tools = BDDTools(str(project_root))
        
        # 生成HTML报告模板
        template_file = tools.generate_html_report_template()
        print(f"生成HTML报告模板: {template_file}")
        
        # 检查文件是否存在
        if Path(template_file).exists():
            print("✅ HTML报告模板生成成功")
        else:
            print("❌ HTML报告模板生成失败")


def example_bdd_integration():
    """BDD集成示例"""
    print("\n=== BDD集成示例 ===")
    
    # 创建BDD集成实例
    bdd_integration = BDDIntegration()
    
    # 设置BDD环境
    bdd_integration.setup_bdd_environment()
    print("✅ BDD环境设置完成")
    
    # 显示可用的步骤定义
    print("当前注册的步骤定义:")
    steps = bdd_integration.step_registry.get_steps()
    for step_type, step_list in steps.items():
        print(f"  {step_type.upper()} steps ({len(step_list)}):")
        for step in step_list:
            print(f"    - {step.pattern}")


def main():
    """主函数"""
    print("PhoenixFrame BDD增强功能示例")
    print("=" * 50)
    
    try:
        example_bdd_project_setup()
        example_feature_generation()
        example_html_report_generation()
        example_bdd_integration()
        
        print("\n所有示例执行完成!")
    except Exception as e:
        print(f"示例执行出错: {e}")


if __name__ == "__main__":
    main()