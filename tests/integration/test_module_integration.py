"""测试模块间集成"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.phoenixframe.security.key_manager import KeyManager
from src.phoenixframe.security.crypto import CryptoUtil
from src.phoenixframe.observability.logger import PhoenixLogger
from src.phoenixframe.observability.metrics import PhoenixMetrics
from src.phoenixframe.utils.data_utils import DataUtil
from src.phoenixframe.utils.file_utils import FileUtil


class TestModuleImports:
    """测试模块导入和基本初始化"""

    def test_security_modules_import(self):
        """测试安全模块导入和初始化"""
        # 测试密钥管理器
        km = KeyManager()
        assert km is not None
        assert hasattr(km, 'get_key')
        assert hasattr(km, 'set_key')

        # 测试加密工具
        crypto = CryptoUtil()
        assert crypto is not None
        assert hasattr(crypto, 'generate_key')

    def test_observability_modules_import(self):
        """测试可观测性模块导入和初始化"""
        # 测试日志器
        logger = PhoenixLogger("test_service")
        assert logger is not None
        assert hasattr(logger, 'logger')

        # 测试度量收集器
        metrics = PhoenixMetrics("test_service")
        assert metrics is not None
        assert hasattr(metrics, 'name')

    def test_utils_modules_import(self):
        """测试工具模块导入和初始化"""
        # 测试数据工具
        data_util = DataUtil()
        assert data_util is not None
        assert hasattr(DataUtil, 'generate_random_string')

        # 测试文件工具
        file_util = FileUtil()
        assert file_util is not None
        assert hasattr(FileUtil, 'read_json')
        assert hasattr(FileUtil, 'write_json')


class TestBasicIntegration:
    """测试基本模块集成"""

    def test_key_manager_basic_operations(self):
        """测试密钥管理器基本操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "keys.json"

            # 创建密钥管理器
            km = KeyManager(str(config_path))

            # 设置和获取密钥
            km.set_key("test_key", "test_value")
            retrieved_key = km.get_key("test_key")

            assert retrieved_key == "test_value"

            # 验证配置文件已创建
            assert config_path.exists()

    def test_file_utils_basic_operations(self):
        """测试文件工具基本操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.json"
            test_data = {"key": "value", "number": 42}

            # 写入JSON文件
            FileUtil.write_json(str(test_file), test_data)

            # 读取JSON文件
            loaded_data = FileUtil.read_json(str(test_file))

            assert loaded_data == test_data
            assert test_file.exists()


class TestDataUtilIntegration:
    """测试数据工具集成"""

    def test_data_util_basic_functions(self):
        """测试数据工具基本功能"""
        data_util = DataUtil()

        # 测试随机字符串生成
        random_str = data_util.generate_random_string(10)
        assert len(random_str) == 10
        assert isinstance(random_str, str)

        # 测试UUID生成
        uuid_str = data_util.generate_uuid()
        assert len(uuid_str) == 36  # UUID格式长度
        assert isinstance(uuid_str, str)

    def test_crypto_util_basic_functions(self):
        """测试加密工具基本功能"""
        crypto = CryptoUtil()

        # 测试密钥生成
        key = crypto.generate_key()
        assert key is not None
        assert len(key) > 0

        # 测试哈希功能
        text = "test data"
        hash_result = crypto.hash_data(text)
        assert hash_result is not None
        assert len(hash_result) > 0
