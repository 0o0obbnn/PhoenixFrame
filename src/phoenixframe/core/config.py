"""配置管理系统

提供统一的配置管理功能，包括：
- 多种配置源支持（文件、环境变量、命令行）
- 配置继承和覆盖
- 配置验证和类型转换
- 动态配置更新
- 配置加密和安全
- 多环境配置切换
- 配置热加载
"""

import os
import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Type, TypeVar, get_type_hints, Callable
import yaml
from pydantic import BaseModel, Field, ValidationError, ConfigDict

from ..observability.logger import get_logger

T = TypeVar('T')


class ConfigFormat(Enum):
    """配置文件格式"""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    INI = "ini"
    ENV = "env"


class ConfigSource(Enum):
    """配置源类型"""
    FILE = "file"
    ENVIRONMENT = "environment"
    COMMAND_LINE = "command_line"
    DATABASE = "database"
    REMOTE = "remote"
    MEMORY = "memory"


@dataclass
class ConfigMetadata:
    """配置元数据"""
    source: ConfigSource
    format: Optional[ConfigFormat] = None
    path: Optional[str] = None
    priority: int = 100
    encrypted: bool = False
    readonly: bool = False
    last_modified: Optional[float] = None


# === 原有的Pydantic配置模型 ===

class EnvironmentConfig(BaseModel):
    model_config = ConfigDict(extra="allow")  # Allow additional environment-specific configurations
    
    base_url: str = Field(default="http://localhost:8000")
    description: Optional[str] = None


class ReportingConfig(BaseModel):
    # Allure报告配置（保持向后兼容）
    allure: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "report_dir": "allure-report",
        "results_dir": "allure-results"
    })
    
    # PhoenixFrame原生报告配置
    native: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "output_dir": "reports",
        "formats": ["html", "json"],
        "auto_open": False,
        "template_dir": None
    })
    
    # 报告收集器配置
    collector: Dict[str, Any] = Field(default_factory=lambda: {
        "auto_screenshot": True,
        "collect_logs": True,
        "collect_metrics": True,
        "max_log_entries": 1000,
        "screenshot_on_failure": True
    })
    
    # 报告内容配置
    content: Dict[str, Any] = Field(default_factory=lambda: {
        "include_environment": True,
        "include_config": True,
        "include_screenshots": True,
        "include_logs": True,
        "include_metrics": True,
        "include_timeline": True
    })
    
    # 报告分发配置
    distribution: Dict[str, Any] = Field(default_factory=lambda: {
        "email": {
            "enabled": False,
            "recipients": [],
            "smtp_server": "",
            "smtp_port": 587,
            "username": "",
            "password": ""
        },
        "slack": {
            "enabled": False,
            "webhook_url": "",
            "channel": "#testing"
        },
        "webhook": {
            "enabled": False,
            "url": "",
            "headers": {}
        }
    })


class WebDriverConfig(BaseModel):
    """WebDriver配置"""
    browser: str = Field(default="chrome", description="Default browser")
    headless: bool = Field(default=True, description="Run in headless mode")
    window_size: str = Field(default="1920x1080", description="Browser window size")
    timeout: int = Field(default=30, description="Default timeout in seconds")
    implicit_wait: int = Field(default=10, description="Implicit wait in seconds")
    page_load_timeout: int = Field(default=30, description="Page load timeout in seconds")
    
    # Selenium特定配置
    selenium: Dict[str, Any] = Field(default_factory=lambda: {
        "chrome_options": ["--no-sandbox", "--disable-dev-shm-usage"],
        "firefox_options": [],
        "driver_path": None,
        "binary_path": None
    })
    
    # Playwright特定配置
    playwright: Dict[str, Any] = Field(default_factory=lambda: {
        "slow_mo": 0,
        "user_agent": None,
        "extra_http_headers": {},
        "ignore_https_errors": False
    })


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "filename": "phoenixframe.log",
        "max_bytes": 10485760,  # 10MB
        "backup_count": 5
    })
    console_handler: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "stream": "stdout"
    })


class DatabaseConfig(BaseModel):
    """数据库配置"""
    default: Dict[str, Any] = Field(default_factory=lambda: {
        "driver": "sqlite",
        "host": "localhost",
        "port": 5432,
        "database": "phoenixframe.db",
        "username": "",
        "password": "",
        "pool_size": 5,
        "ssl": False
    })


class TestingConfig(BaseModel):
    """测试配置"""
    # 并行执行配置
    parallel_workers: int = Field(default=4, description="Number of parallel workers")
    execution_strategy: str = Field(default="adaptive", description="Execution strategy (sequential, thread_pool, process_pool, adaptive)")
    worker_timeout: float = Field(default=300.0, description="Worker timeout in seconds")
    task_timeout: float = Field(default=60.0, description="Task timeout in seconds")
    
    # 重试配置
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    
    # 测试数据和输出
    test_data_dir: str = Field(default="tests/data", description="Test data directory")
    output_dir: str = Field(default="output", description="Test output directory")
    temp_dir: str = Field(default="temp", description="Temporary files directory")
    
    # 截图和视频
    screenshot_on_failure: bool = Field(default=True, description="Take screenshot on test failure")
    video_recording: bool = Field(default=False, description="Enable video recording")
    screenshot_dir: str = Field(default="screenshots", description="Screenshot directory")
    
    # 资源管理
    resource_cleanup: bool = Field(default=True, description="Auto cleanup test resources")
    memory_limit_mb: Optional[int] = Field(default=None, description="Memory limit per worker in MB")
    cpu_limit_percent: Optional[float] = Field(default=None, description="CPU limit per worker in percent")
    
    # 监控和日志
    enable_progress_tracking: bool = Field(default=True, description="Enable progress tracking")
    enable_resource_monitoring: bool = Field(default=True, description="Enable resource monitoring")
    log_level: str = Field(default="INFO", description="Test execution log level")
    
    # 测试发现
    test_discovery: Dict[str, Any] = Field(default_factory=lambda: {
        "auto_discover": True,
        "test_patterns": ["test_*.py", "*_test.py"],
        "exclude_patterns": ["__pycache__", "*.pyc"],
        "max_depth": 5
    })
    
    # 测试分类和标签
    test_categories: Dict[str, Any] = Field(default_factory=lambda: {
        "unit": {"timeout": 30, "parallel": True},
        "integration": {"timeout": 120, "parallel": True},
        "ui": {"timeout": 300, "parallel": False},
        "api": {"timeout": 60, "parallel": True},
        "performance": {"timeout": 600, "parallel": False}
    })


class SecurityConfig(BaseModel):
    """安全配置"""
    encryption_key: Optional[str] = Field(default=None, description="Encryption key for sensitive data")
    mask_sensitive_data: bool = Field(default=True, description="Mask sensitive data in logs")
    sensitive_fields: List[str] = Field(default_factory=lambda: ["password", "token", "key", "secret"])


class PerformanceConfig(BaseModel):
    """性能配置"""
    locust: Dict[str, Any] = Field(default_factory=lambda: {
        "host": "http://localhost",
        "users": 10,
        "spawn_rate": 2,
        "run_time": "1m"
    })
    monitoring: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "metrics_interval": 5,
        "memory_threshold": 80,
        "cpu_threshold": 80
    })


class ObservabilityConfig(BaseModel):
    """可观测性配置"""
    tracing: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "service_name": "phoenixframe",
        "jaeger_endpoint": "http://localhost:14268/api/traces",
        "sample_rate": 1.0
    })
    metrics: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "prometheus_port": 8090,
        "collection_interval": 10
    })


class ConfigModel(BaseModel):
    """完整的配置模型"""
    model_config = ConfigDict(extra="allow")
    
    app_name: str = "PhoenixFrame"
    version: str = "3.2.0"
    
    # 环境配置
    environments: Dict[str, EnvironmentConfig] = Field(default_factory=lambda: {
        "default": EnvironmentConfig()
    })
    
    # 各模块配置
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    webdriver: WebDriverConfig = Field(default_factory=WebDriverConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    testing: TestingConfig = Field(default_factory=TestingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    
    # 当前激活的环境
    active_environment: str = Field(default="default")


# === 新的配置管理系统 ===

class ConfigProvider(ABC):
    """配置提供者接口"""
    
    @abstractmethod
    def load(self, path: str) -> Dict[str, Any]:
        """加载配置"""
        pass
    
    @abstractmethod
    def save(self, path: str, config: Dict[str, Any]) -> None:
        """保存配置"""
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """检查配置是否存在"""
        pass
    
    @abstractmethod
    def watch(self, path: str, callback: Callable) -> None:
        """监控配置变化"""
        pass


class FileConfigProvider(ConfigProvider):
    """文件配置提供者"""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._watchers: Dict[str, List[Callable]] = {}
        self._file_watchers: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
    
    def load(self, path: str) -> Dict[str, Any]:
        """加载文件配置"""
        file_path = Path(path)
        
        if not file_path.exists():
            return {}
        
        try:
            format = self._detect_format(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if format == ConfigFormat.JSON:
                    return json.load(f)
                elif format == ConfigFormat.YAML:
                    return yaml.safe_load(f) or {}
                elif format == ConfigFormat.TOML:
                    import toml
                    return toml.load(f)
                elif format == ConfigFormat.INI:
                    import configparser
                    config = configparser.ConfigParser()
                    config.read(file_path)
                    return {section: dict(config[section]) for section in config.sections()}
                else:
                    raise ValueError(f"Unsupported format: {format}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load config from {path}: {e}")
            return {}
    
    def save(self, path: str, config: Dict[str, Any]) -> None:
        """保存文件配置"""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            format = self._detect_format(file_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if format == ConfigFormat.JSON:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                elif format == ConfigFormat.YAML:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                elif format == ConfigFormat.TOML:
                    import toml
                    toml.dump(config, f)
                elif format == ConfigFormat.INI:
                    import configparser
                    config_parser = configparser.ConfigParser()
                    for section, values in config.items():
                        config_parser[section] = values
                    config_parser.write(f)
                else:
                    raise ValueError(f"Unsupported format: {format}")
                    
            self.logger.debug(f"Saved config to {path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save config to {path}: {e}")
            raise
    
    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return Path(path).exists()
    
    def watch(self, path: str, callback: Callable) -> None:
        """监控文件变化"""
        if path not in self._watchers:
            self._watchers[path] = []
        self._watchers[path].append(callback)
        
        # 如果还没有启动监控线程，则启动它
        if path not in self._file_watchers:
            self._start_file_watcher(path)
    
    def _start_file_watcher(self, path: str) -> None:
        """启动文件监控线程"""
        stop_event = threading.Event()
        self._stop_events[path] = stop_event
        
        def watch_thread():
            last_modified = None
            while not stop_event.is_set():
                try:
                    if os.path.exists(path):
                        current_modified = os.path.getmtime(path)
                        if last_modified is not None and current_modified != last_modified:
                            self.logger.info(f"Configuration file {path} changed, reloading...")
                            # 通知所有观察者
                            for callback in self._watchers.get(path, []):
                                try:
                                    callback(path)
                                except Exception as e:
                                    self.logger.error(f"Error in config change callback: {e}")
                        last_modified = current_modified
                except Exception as e:
                    self.logger.error(f"Error watching config file {path}: {e}")
                
                # 每秒检查一次
                time.sleep(1)
        
        watcher_thread = threading.Thread(target=watch_thread, daemon=True, name=f"ConfigWatcher-{path}")
        watcher_thread.start()
        self._file_watchers[path] = watcher_thread
    
    def _detect_format(self, file_path: Path) -> ConfigFormat:
        """检测文件格式"""
        suffix = file_path.suffix.lower()
        
        if suffix == '.json':
            return ConfigFormat.JSON
        elif suffix in ('.yaml', '.yml'):
            return ConfigFormat.YAML
        elif suffix == '.toml':
            return ConfigFormat.TOML
        elif suffix == '.ini':
            return ConfigFormat.INI
        else:
            return ConfigFormat.YAML  # 默认格式


class EnvironmentConfigProvider(ConfigProvider):
    """环境变量配置提供者"""
    
    def __init__(self, prefix: str = "PHOENIX_"):
        self.prefix = prefix
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def load(self, path: str = "") -> Dict[str, Any]:
        """加载环境变量配置"""
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # 移除前缀并转换为小写
                config_key = key[len(self.prefix):].lower()
                
                # 将下划线分隔的键转换为嵌套结构
                keys = config_key.split('_')
                current = config
                
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                
                # 尝试类型转换
                current[keys[-1]] = self._convert_value(value)
        
        return config
    
    def save(self, path: str, config: Dict[str, Any]) -> None:
        """保存到环境变量（不推荐）"""
        pass
    
    def exists(self, path: str) -> bool:
        """检查环境变量是否存在"""
        return f"{self.prefix}{path.upper()}" in os.environ
    
    def watch(self, path: str, callback: Callable) -> None:
        """监控环境变量变化（不支持）"""
        pass
    
    def _convert_value(self, value: str) -> Any:
        """尝试将字符串值转换为适当的类型"""
        # 布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # JSON值
        if value.startswith(('{', '[', '"')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # 列表（逗号分隔）
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        return value


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.providers: Dict[ConfigSource, ConfigProvider] = {
            ConfigSource.FILE: FileConfigProvider(),
            ConfigSource.ENVIRONMENT: EnvironmentConfigProvider()
        }
        self.config: Optional[ConfigModel] = None
        self.config_lock = threading.Lock()
        self.change_callbacks: List[Callable[[ConfigModel], None]] = []
        self.active_environment: str = "default"
        
    def load_config(self, config_path: Optional[Union[str, Path]] = None) -> ConfigModel:
        """加载配置"""
        with self.config_lock:
            # 1. 从文件加载基础配置
            file_config = {}
            if config_path:
                file_config = self.providers[ConfigSource.FILE].load(str(config_path))
            else:
                # 尝试默认配置文件路径
                default_paths = [
                    Path("configs/phoenix.yaml"),
                    Path("phoenixframe.yaml"),
                    Path("phoenixframe.yml"),
                    Path(".phoenixframe.yaml"),
                    Path(".phoenixframe.yml")
                ]
                
                for path in default_paths:
                    if path.exists():
                        file_config = self.providers[ConfigSource.FILE].load(str(path))
                        config_path = path
                        break
            
            # 2. 从环境变量加载覆盖配置
            env_config = self.providers[ConfigSource.ENVIRONMENT].load()
            
            # 3. 合并配置（环境变量优先）
            merged_config = self._merge_configs(file_config, env_config)
            
            # 4. 创建配置模型实例
            try:
                self.config = ConfigModel(**merged_config)
                self.active_environment = self.config.active_environment
                self.logger.info(f"Configuration loaded, active environment: {self.active_environment}")
                
                # 5. 如果有配置文件路径，开始监控其变化
                if config_path:
                    self.providers[ConfigSource.FILE].watch(
                        str(config_path), 
                        lambda path: self._on_config_file_changed(path)
                    )
                
                return self.config
            except ValidationError as e:
                self.logger.error(f"Configuration validation failed: {e}")
                raise ValueError(f"Configuration validation failed: {e}") from e
    
    def _merge_configs(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置，override_config优先"""
        merged = base_config.copy()
        
        def merge_recursive(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = merge_recursive(base[key], value)
                else:
                    base[key] = value
            return base
        
        return merge_recursive(merged, override_config)
    
    def _on_config_file_changed(self, path: str) -> None:
        """配置文件变化回调"""
        try:
            self.logger.info(f"Reloading configuration from {path}")
            new_config = self.load_config(path)
            
            # 通知所有观察者配置已更新
            for callback in self.change_callbacks:
                try:
                    callback(new_config)
                except Exception as e:
                    self.logger.error(f"Error in config change callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
    
    def get_config(self) -> ConfigModel:
        """获取当前配置"""
        if self.config is None:
            self.load_config()
        return self.config
    
    def set_config(self, config: ConfigModel) -> None:
        """设置配置"""
        with self.config_lock:
            old_config = self.config
            self.config = config
            self.active_environment = config.active_environment
            
            # 如果配置发生变化，通知观察者
            if old_config != config:
                for callback in self.change_callbacks:
                    try:
                        callback(config)
                    except Exception as e:
                        self.logger.error(f"Error in config change callback: {e}")
    
    def switch_environment(self, environment_name: str) -> None:
        """切换环境"""
        with self.config_lock:
            if self.config is None:
                raise RuntimeError("Configuration not loaded")
            
            if environment_name not in self.config.environments:
                raise ValueError(f"Environment '{environment_name}' not found in configuration")
            
            # 更新激活的环境
            self.config.active_environment = environment_name
            self.active_environment = environment_name
            
            self.logger.info(f"Switched to environment: {environment_name}")
            
            # 通知观察者环境已切换
            for callback in self.change_callbacks:
                try:
                    callback(self.config)
                except Exception as e:
                    self.logger.error(f"Error in config change callback: {e}")
    
    def get_active_environment_config(self) -> EnvironmentConfig:
        """获取当前激活环境的配置"""
        config = self.get_config()
        return config.environments.get(
            config.active_environment, 
            config.environments.get("default", EnvironmentConfig())
        )
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值的便捷函数"""
        config = self.get_config()
        keys = key.split('.')
        current = config.model_dump()
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def set_config_value(self, key: str, value: Any) -> None:
        """设置配置值的便捷函数"""
        config = self.get_config()
        keys = key.split('.')
        config_dict = config.model_dump()
        
        # 导航到目标位置
        current = config_dict
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # 设置值
        current[keys[-1]] = value
        
        # 重新创建配置对象
        new_config = ConfigModel(**config_dict)
        self.set_config(new_config)
    
    def add_change_callback(self, callback: Callable[[ConfigModel], None]) -> None:
        """添加配置变化回调"""
        self.change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[ConfigModel], None]) -> None:
        """移除配置变化回调"""
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)


# 全局配置管理器实例
_global_config_manager = ConfigManager()
_config_manager_lock = threading.Lock()


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    return _global_config_manager


def load_config(config_path: Optional[Union[str, Path]] = None) -> ConfigModel:
    """加载配置（向后兼容）"""
    manager = get_config_manager()
    return manager.load_config(config_path)


def get_config() -> ConfigModel:
    """获取配置（向后兼容）"""
    manager = get_config_manager()
    return manager.get_config()


def set_config(config: ConfigModel) -> None:
    """设置配置（向后兼容）"""
    manager = get_config_manager()
    manager.set_config(config)


def switch_environment(environment_name: str) -> None:
    """切换环境"""
    manager = get_config_manager()
    manager.switch_environment(environment_name)


def get_active_environment_config() -> EnvironmentConfig:
    """获取当前激活环境的配置"""
    manager = get_config_manager()
    return manager.get_active_environment_config()


def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数（向后兼容）"""
    manager = get_config_manager()
    return manager.get_config_value(key, default)


def set_config_value(key: str, value: Any) -> None:
    """设置配置值的便捷函数（向后兼容）"""
    manager = get_config_manager()
    manager.set_config_value(key, value)


# Alias for backward compatibility
PhoenixConfig = ConfigModel