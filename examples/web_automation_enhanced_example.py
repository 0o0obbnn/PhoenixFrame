"""
Playwright增强功能示例

这个示例展示了如何使用PhoenixFrame中增强的Playwright功能，
包括设备模拟、网络拦截和视觉对比测试。
"""

from src.phoenixframe.web.playwright_driver import PlaywrightDriver


def example_device_simulation():
    """设备模拟示例"""
    print("=== 设备模拟示例 ===")
    
    # 创建Playwright驱动
    driver = PlaywrightDriver(headless=True)
    page = driver.start()
    
    # 获取可用设备列表
    devices = driver.get_available_devices()
    print(f"可用设备数量: {len(devices)}")
    print(f"部分设备: {devices[:5]}")
    
    # 设置为iPhone设备
    if "iPhone 11" in devices:
        driver.set_device("iPhone 11")
        print("已设置为iPhone 11设备")
    
    # 导航到页面
    page.goto("https://example.com")
    print("已导航到示例页面")
    
    # 设置自定义视口大小
    driver.set_viewport(1920, 1080)
    print("已设置视口大小为1920x1080")
    
    # 关闭驱动
    driver.quit()
    print("驱动已关闭")


def example_network_interception():
    """网络拦截示例"""
    print("\n=== 网络拦截示例 ===")
    
    # 创建Playwright驱动
    driver = PlaywrightDriver(headless=True)
    page = driver.start()
    
    # 定义拦截处理函数
    def block_images(route):
        if route.request.resource_type == "image":
            print(f"拦截图片请求: {route.request.url}")
            route.abort()
        else:
            route.continue_()
    
    # 拦截图片请求
    driver.intercept_requests("**/*.{png,jpg,jpeg,gif,webp}", block_images)
    print("已开始拦截图片请求")
    
    # 导航到页面
    page.goto("https://example.com")
    print("已导航到示例页面（图片被拦截）")
    
    # 停止拦截
    driver.stop_intercepting_requests("**/*.{png,jpg,jpeg,gif,webp}")
    print("已停止拦截图片请求")
    
    # 关闭驱动
    driver.quit()
    print("驱动已关闭")


def example_visual_testing():
    """视觉测试示例"""
    print("\n=== 视觉测试示例 ===")
    
    # 创建Playwright驱动
    driver = PlaywrightDriver(headless=True)
    page = driver.start()
    
    # 导航到页面
    page.goto("https://example.com")
    
    # 截图
    screenshot_data = page.screenshot(path="example_screenshot.png")
    print(f"截图完成，大小: {len(screenshot_data)} 字节")
    
    # 视觉对比（需要安装opencv-python）
    try:
        result = page.compare_visual("example_screenshot.png")  # 假设扩展了Page类或使用工具函数
        print(f"视觉对比结果: {'通过' if result else '失败'}")
    except AttributeError:
        print("Page对象没有compare_visual方法，请确认是否扩展了功能")
    except Exception as e:
        print(f"视觉对比测试失败: {e}")
    
    # 关闭驱动
    driver.quit()
    print("驱动已关闭")


def main():
    """主函数"""
    print("PhoenixFrame Playwright增强功能示例")
    print("=" * 50)
    
    try:
        example_device_simulation()
        example_network_interception()
        example_visual_testing()
        
        print("\n所有示例执行完成!")
    except Exception as e:
        print(f"示例执行出错: {e}")


if __name__ == "__main__":
    main()