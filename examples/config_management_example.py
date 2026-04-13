"""
配置管理示例

展示如何使用PhoenixFrame的配置管理系统，
包括多环境切换和配置热加载功能。
"""

import time
import threading
from pathlib import Path
from src.phoenixframe.core.config import (
    get_config_manager, 
    load_config, 
    switch_environment,
    get_active_environment_config,
    get_config_value,
    set_config_value
)


def example_config_loading():
    """配置加载示例"""
    print("=== 配置加载示例 ===")
    
    # 加载配置
    config_manager = get_config_manager()
    config = config_manager.load_config("configs/phoenix.yaml")
    
    print(f"应用名称: {config.app_name}")
    print(f"版本: {config.version}")
    print(f"激活环境: {config.active_environment}")
    
    # 显示所有环境
    print("可用环境:")
    for env_name, env_config in config.environments.items():
        print(f"  - {env_name}: {env_config.base_url} ({env_config.description})")


def example_environment_switching():
    """环境切换示例"""
    print("\n=== 环境切换示例 ===")
    
    # 获取当前环境配置
    current_env = get_active_environment_config()
    print(f"当前环境URL: {current_env.base_url}")
    
    # 切换到开发环境
    try:
        switch_environment("development")
        dev_env = get_active_environment_config()
        print(f"切换到开发环境，URL: {dev_env.base_url}")
    except ValueError as e:
        print(f"切换环境失败: {e}")
    
    # 切换到预发布环境
    try:
        switch_environment("staging")
        staging_env = get_active_environment_config()
        print(f"切换到预发布环境，URL: {staging_env.base_url}")
    except ValueError as e:
        print(f"切换环境失败: {e}")
    
    # 切换回默认环境
    try:
        switch_environment("default")
        default_env = get_active_environment_config()
        print(f"切换回默认环境，URL: {default_env.base_url}")
    except ValueError as e:
        print(f"切换环境失败: {e}")


def example_config_access():
    """配置访问示例"""
    print("\n=== 配置访问示例 ===")
    
    # 通过键路径访问配置值
    browser = get_config_value("webdriver.browser")
    headless = get_config_value("webdriver.headless")
    log_level = get_config_value("logging.level")
    
    print(f"浏览器: {browser}")
    print(f"无头模式: {headless}")
    print(f"日志级别: {log_level}")
    
    # 设置配置值
    set_config_value("webdriver.headless", False)
    new_headless = get_config_value("webdriver.headless")
    print(f"更新后的无头模式: {new_headless}")


def config_change_callback(config):
    """配置变化回调函数"""
    print(f"\n[回调] 配置已更新，激活环境: {config.active_environment}")


def example_config_hot_reload():
    """配置热加载示例"""
    print("\n=== 配置热加载示例 ===")
    print("请手动修改 configs/phoenix.yaml 文件来测试热加载功能")
    print("例如，可以修改 webdriver.headless 的值")
    print("按 Ctrl+C 停止监听")
    
    # 添加配置变化回调
    config_manager = get_config_manager()
    config_manager.add_change_callback(config_change_callback)
    
    try:
        # 持续运行以监听配置变化
        for i in range(30):  # 运行30秒
            time.sleep(1)
            if i % 10 == 0:
                print(f"监听中... ({i}/30秒)")
    except KeyboardInterrupt:
        print("\n停止监听")


def main():
    """主函数"""
    print("PhoenixFrame 配置管理示例")
    print("=" * 50)
    
    try:
        example_config_loading()
        example_environment_switching()
        example_config_access()
        
        # 热加载示例需要手动修改配置文件来观察效果
        # example_config_hot_reload()
        
        print("\n所有示例执行完成!")
    except Exception as e:
        print(f"示例执行出错: {e}")


if __name__ == "__main__":
    main()