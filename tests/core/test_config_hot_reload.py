"""
配置热加载测试
测试配置管理器的热加载和环境切换功能
"""

import tempfile
import time
import threading
import yaml
from pathlib import Path
import pytest

from src.phoenixframe.core.config import (
    ConfigManager,
    ConfigModel,
    EnvironmentConfig
)


class TestConfigHotReload:
    """配置热加载测试"""
    
    def test_config_loading(self):
        """测试配置加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试配置文件
            config_path = Path(temp_dir) / "test_config.yaml"
            config_data = {
                "app_name": "TestApp",
                "version": "1.0.0",
                "environments": {
                    "default": {
                        "base_url": "http://localhost:8000",
                        "description": "测试环境"
                    },
                    "test": {
                        "base_url": "http://test.example.com",
                        "description": "测试专用环境"
                    }
                },
                "active_environment": "default"
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            # 加载配置
            manager = ConfigManager()
            config = manager.load_config(config_path)
            
            # 验证配置
            assert config.app_name == "TestApp"
            assert config.version == "1.0.0"
            assert "default" in config.environments
            assert "test" in config.environments
            assert config.active_environment == "default"
    
    def test_environment_switching(self):
        """测试环境切换"""
        # 创建测试配置
        config = ConfigModel(
            app_name="TestApp",
            environments={
                "default": EnvironmentConfig(
                    base_url="http://localhost:8000",
                    description="默认环境"
                ),
                "test": EnvironmentConfig(
                    base_url="http://test.example.com",
                    description="测试环境"
                )
            }
        )
        
        manager = ConfigManager()
        manager.set_config(config)
        
        # 切换环境
        manager.switch_environment("test")
        active_env = manager.get_active_environment_config()
        assert active_env.base_url == "http://test.example.com"
        
        # 切换回默认环境
        manager.switch_environment("default")
        active_env = manager.get_active_environment_config()
        assert active_env.base_url == "http://localhost:8000"
    
    def test_invalid_environment_switching(self):
        """测试无效环境切换"""
        config = ConfigModel(
            app_name="TestApp"
        )
        
        manager = ConfigManager()
        manager.set_config(config)
        
        # 尝试切换到不存在的环境
        with pytest.raises(ValueError, match="Environment 'nonexistent' not found"):
            manager.switch_environment("nonexistent")
    
    def test_config_value_access(self):
        """测试配置值访问"""
        config = ConfigModel(
            app_name="TestApp",
            webdriver={"browser": "chrome", "headless": True}
        )
        
        manager = ConfigManager()
        manager.set_config(config)
        
        # 获取配置值
        browser = manager.get_config_value("webdriver.browser")
        headless = manager.get_config_value("webdriver.headless")
        
        assert browser == "chrome"
        assert headless is True
        
        # 设置配置值
        manager.set_config_value("webdriver.headless", False)
        new_headless = manager.get_config_value("webdriver.headless")
        assert new_headless is False
    
    def test_config_change_callbacks(self):
        """测试配置变化回调"""
        config = ConfigModel(app_name="TestApp")
        manager = ConfigManager()
        
        # 记录回调调用次数
        callback_count = 0
        callback_config = None
        
        def test_callback(new_config):
            nonlocal callback_count, callback_config
            callback_count += 1
            callback_config = new_config
        
        # 添加回调
        manager.add_change_callback(test_callback)
        
        # 触发配置变化
        manager.set_config(config)
        
        # 验证回调被调用
        assert callback_count == 1
        assert callback_config == config
        
        # 移除回调
        manager.remove_change_callback(test_callback)
        
        # 再次触发配置变化
        manager.set_config(config)
        
        # 验证回调未被再次调用
        assert callback_count == 1  # 仍然为1，说明回调已被移除


def test_backward_compatibility():
    """测试向后兼容性"""
    from src.phoenixframe.core.config import (
        load_config,
        get_config,
        set_config,
        switch_environment,
        get_active_environment_config,
        get_config_value,
        set_config_value
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试配置文件
        config_path = Path(temp_dir) / "test_config.yaml"
        config_data = {
            "app_name": "CompatTest",
            "environments": {
                "default": {
                    "base_url": "http://localhost:8000"
                }
            },
            "webdriver": {
                "browser": "firefox"
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        
        # 使用旧API加载配置
        config = load_config(config_path)
        assert config.app_name == "CompatTest"
        
        # 使用旧API获取配置
        current_config = get_config()
        assert current_config.app_name == "CompatTest"
        
        # 使用旧API访问配置值
        browser = get_config_value("webdriver.browser")
        assert browser == "firefox"
        
        # 使用旧API设置配置值
        set_config_value("webdriver.browser", "chrome")
        new_browser = get_config_value("webdriver.browser")
        assert new_browser == "chrome"