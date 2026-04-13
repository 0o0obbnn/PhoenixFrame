"""
手动测试配置热加载功能

这个脚本用于手动测试配置文件的热加载功能。
运行后修改 configs/phoenix.yaml 文件来观察热加载效果。
"""

import time
import signal
import sys
from src.phoenixframe.core.config import get_config_manager, get_config, get_active_environment_config


def config_change_handler(config):
    """配置变化处理函数"""
    print(f"\n[配置更新] 应用名称: {config.app_name}")
    print(f"[配置更新] 激活环境: {config.active_environment}")
    print(f"[配置更新] 当前环境URL: {get_active_environment_config().base_url}")
    print(f"[配置更新] 浏览器设置: {config.webdriver.browser}")
    print(f"[配置更新] 无头模式: {config.webdriver.headless}")


def signal_handler(sig, frame):
    """信号处理函数"""
    print('\n\n接收到退出信号，正在退出...')
    sys.exit(0)


def main():
    """主函数"""
    print("PhoenixFrame 配置热加载手动测试")
    print("=" * 50)
    print("这个脚本会监听配置文件的变化")
    print("请手动修改 configs/phoenix.yaml 文件来测试热加载功能")
    print("例如:")
    print("  1. 修改 webdriver.headless 的值")
    print("  2. 修改 environments.development.base_url 的值")
    print("  3. 修改 app_name 的值")
    print("\n按 Ctrl+C 退出")
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 获取配置管理器
    config_manager = get_config_manager()
    
    # 加载配置
    try:
        config = config_manager.load_config("configs/phoenix.yaml")
        print(f"\n初始配置加载完成:")
        print(f"  应用名称: {config.app_name}")
        print(f"  激活环境: {config.active_environment}")
        print(f"  当前环境URL: {get_active_environment_config().base_url}")
        print(f"  浏览器设置: {config.webdriver.browser}")
        print(f"  无头模式: {config.webdriver.headless}")
    except Exception as e:
        print(f"配置加载失败: {e}")
        return
    
    # 添加配置变化回调
    config_manager.add_change_callback(config_change_handler)
    
    print("\n开始监听配置文件变化...")
    print("请修改 configs/phoenix.yaml 文件来测试热加载功能")
    
    # 持续运行以监听配置变化
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n\n接收到退出信号，正在退出...')
        sys.exit(0)


if __name__ == "__main__":
    main()