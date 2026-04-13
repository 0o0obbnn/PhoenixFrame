"""测试密钥管理模块"""
import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from src.phoenixframe.security.key_manager import KeyManager


class TestKeyManager:
    """测试密钥管理器"""
    
    def test_initialization_default_path(self):
        """测试默认路径初始化"""
        with patch.object(KeyManager, '_load_config'):
            km = KeyManager()
            assert km.config_path == "configs/keys.json"
            assert km.keys == {}
    
    def test_initialization_custom_path(self):
        """测试自定义路径初始化"""
        custom_path = "/custom/path/keys.json"
        with patch.object(KeyManager, '_load_config'):
            km = KeyManager(custom_path)
            assert km.config_path == custom_path
    
    def test_load_config_file_exists(self):
        """测试加载存在的配置文件"""
        test_config = {
            "api_key": "secret123",
            "db_password": {
                "source": "env",
                "env_var": "DB_PASSWORD"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            temp_file = f.name
        
        try:
            km = KeyManager(temp_file)
            assert km.keys == test_config
        finally:
            Path(temp_file).unlink()
    
    def test_load_config_file_not_exists(self):
        """测试加载不存在的配置文件"""
        km = KeyManager("nonexistent.json")
        assert km.keys == {}
    
    def test_load_config_invalid_json(self):
        """测试加载无效JSON文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            with patch('builtins.print') as mock_print:
                km = KeyManager(temp_file)
                assert km.keys == {}
                mock_print.assert_called()
        finally:
            Path(temp_file).unlink()
    
    def test_save_config_success(self):
        """测试成功保存配置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_keys.json"
            km = KeyManager(str(config_path))
            km.keys = {"test_key": "test_value"}
            
            km._save_config()
            
            # 验证文件内容
            with open(config_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            assert saved_data == {"test_key": "test_value"}
    
    def test_save_config_io_error(self):
        """测试保存配置时的IO错误"""
        km = KeyManager()
        km.config_path = "/invalid/path/keys.json"
        km.keys = {"test_key": "test_value"}

        with patch('builtins.print') as mock_print:
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                km._save_config()
                mock_print.assert_called()
    
    @patch.dict(os.environ, {'PHOENIX_KEY_API_KEY': 'env_secret'})
    def test_get_key_from_environment(self):
        """测试从环境变量获取密钥"""
        km = KeyManager()
        result = km.get_key("api_key")
        assert result == "env_secret"
    
    def test_get_key_direct_string_value(self):
        """测试获取直接存储的字符串密钥"""
        km = KeyManager()
        km.keys = {"simple_key": "simple_value"}
        
        result = km.get_key("simple_key")
        assert result == "simple_value"
    
    def test_get_key_from_direct_config(self):
        """测试从direct配置获取密钥"""
        km = KeyManager()
        km.keys = {
            "direct_key": {
                "source": "direct",
                "value": "direct_value"
            }
        }
        
        result = km.get_key("direct_key")
        assert result == "direct_value"
    
    @patch.dict(os.environ, {'CUSTOM_ENV_VAR': 'custom_value'})
    def test_get_key_from_env_config(self):
        """测试从env配置获取密钥"""
        km = KeyManager()
        km.keys = {
            "env_key": {
                "source": "env",
                "env_var": "CUSTOM_ENV_VAR"
            }
        }
        
        result = km.get_key("env_key")
        assert result == "custom_value"
    
    def test_get_key_from_file_config(self):
        """测试从文件配置获取密钥"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("file_secret_value")
            temp_file = f.name
        
        try:
            km = KeyManager()
            km.keys = {
                "file_key": {
                    "source": "file",
                    "file_path": temp_file
                }
            }
            
            result = km.get_key("file_key")
            assert result == "file_secret_value"
        finally:
            Path(temp_file).unlink()
    
    def test_get_key_from_kms_config(self):
        """测试从KMS配置获取密钥"""
        km = KeyManager()
        km.keys = {
            "kms_key": {
                "source": "kms",
                "type": "vault",
                "url": "https://vault.example.com"
            }
        }
        
        with patch.object(km, '_get_key_from_kms', return_value="kms_value") as mock_kms:
            result = km.get_key("kms_key")
            assert result == "kms_value"
            mock_kms.assert_called_once()
    
    def test_get_key_not_found(self):
        """测试获取不存在的密钥"""
        km = KeyManager()
        result = km.get_key("nonexistent_key")
        assert result is None
    
    def test_set_key_string_value(self):
        """测试设置字符串密钥"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_keys.json"
            km = KeyManager(str(config_path))
            
            km.set_key("test_key", "test_value")
            
            assert km.keys["test_key"] == "test_value"
            # 验证文件已保存
            assert config_path.exists()
    
    def test_set_key_dict_value(self):
        """测试设置字典配置密钥"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_keys.json"
            km = KeyManager(str(config_path))
            
            config = {
                "source": "env",
                "env_var": "TEST_VAR"
            }
            km.set_key("complex_key", config)
            
            assert km.keys["complex_key"] == config
    
    def test_set_key_from_env(self):
        """测试设置环境变量密钥"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_keys.json"
            km = KeyManager(str(config_path))
            
            km.set_key_from_env("env_key", "MY_ENV_VAR")
            
            expected = {
                "source": "env",
                "env_var": "MY_ENV_VAR"
            }
            assert km.keys["env_key"] == expected
    
    def test_set_key_from_file(self):
        """测试设置文件密钥"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_keys.json"
            km = KeyManager(str(config_path))
            
            km.set_key_from_file("file_key", "/path/to/secret.txt")
            
            expected = {
                "source": "file",
                "file_path": "/path/to/secret.txt"
            }
            assert km.keys["file_key"] == expected
    
    def test_set_key_from_kms(self):
        """测试设置KMS密钥"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_keys.json"
            km = KeyManager(str(config_path))
            
            kms_config = {
                "type": "vault",
                "url": "https://vault.example.com",
                "secret_path": "secret/myapp"
            }
            km.set_key_from_kms("kms_key", kms_config)
            
            expected = kms_config.copy()
            expected["source"] = "kms"
            assert km.keys["kms_key"] == expected
    
    def test_remove_key_exists(self):
        """测试删除存在的密钥"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_keys.json"
            km = KeyManager(str(config_path))
            km.keys = {"key1": "value1", "key2": "value2"}
            
            result = km.remove_key("key1")
            
            assert result is True
            assert "key1" not in km.keys
            assert "key2" in km.keys
    
    def test_remove_key_not_exists(self):
        """测试删除不存在的密钥"""
        km = KeyManager()
        result = km.remove_key("nonexistent_key")
        assert result is False
    
    def test_list_keys(self):
        """测试列出所有密钥"""
        km = KeyManager()
        km.keys = {
            "key1": "value1",
            "key2": {"source": "env"},
            "key3": "value3"
        }
        
        result = km.list_keys()
        assert set(result) == {"key1", "key2", "key3"}
    
    def test_read_key_from_file_success(self):
        """测试成功从文件读取密钥"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("  secret_content  \n")  # 包含空白字符
            temp_file = f.name
        
        try:
            km = KeyManager()
            result = km._read_key_from_file(temp_file)
            assert result == "secret_content"  # 应该去除空白字符
        finally:
            Path(temp_file).unlink()
    
    def test_read_key_from_file_io_error(self):
        """测试从文件读取密钥时的IO错误"""
        km = KeyManager()
        
        with patch('builtins.print') as mock_print:
            result = km._read_key_from_file("/nonexistent/file.txt")
            assert result is None
            mock_print.assert_called()
    
    def test_get_key_from_kms_vault_type(self):
        """测试从Vault类型KMS获取密钥"""
        km = KeyManager()
        vault_config = {
            "type": "vault",
            "url": "https://vault.example.com"
        }
        
        with patch.object(km, '_get_key_from_vault', return_value="vault_secret") as mock_vault:
            result = km._get_key_from_kms(vault_config)
            assert result == "vault_secret"
            mock_vault.assert_called_once_with(vault_config)
    
    def test_get_key_from_kms_aws_type(self):
        """测试从AWS类型KMS获取密钥"""
        km = KeyManager()
        aws_config = {
            "type": "aws",
            "key_id": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
        }
        
        with patch.object(km, '_get_key_from_aws_kms', return_value="aws_secret") as mock_aws:
            result = km._get_key_from_kms(aws_config)
            assert result == "aws_secret"
            mock_aws.assert_called_once_with(aws_config)
    
    def test_get_key_from_kms_unknown_type(self):
        """测试从未知类型KMS获取密钥"""
        km = KeyManager()
        unknown_config = {
            "type": "unknown_kms",
            "some_param": "value"
        }
        
        with patch('builtins.print') as mock_print:
            result = km._get_key_from_kms(unknown_config)
            assert result is None
            mock_print.assert_called_with("Warning: Unsupported KMS type: unknown_kms")

    @patch.dict(os.environ, {'VAULT_TOKEN': 'vault_token_123'})
    def test_get_key_from_vault_success(self):
        """测试成功从Vault获取密钥"""
        vault_config = {
            "url": "https://vault.example.com",
            "secret_path": "secret/myapp",
            "secret_key": "password"
        }

        # 模拟hvac库
        mock_hvac = Mock()
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            'data': {'data': {'password': 'vault_secret_value'}}
        }
        mock_hvac.Client.return_value = mock_client

        km = KeyManager()

        with patch.dict('sys.modules', {'hvac': mock_hvac}):
            result = km._get_key_from_vault(vault_config)

            assert result == "vault_secret_value"
            mock_hvac.Client.assert_called_with(url="https://vault.example.com", token="vault_token_123")
            mock_client.secrets.kv.v2.read_secret_version.assert_called_with(path="secret/myapp")

    def test_get_key_from_vault_incomplete_config(self):
        """测试Vault配置不完整"""
        vault_config = {
            "url": "https://vault.example.com"
            # 缺少secret_path
        }

        km = KeyManager()

        with patch('builtins.print') as mock_print:
            result = km._get_key_from_vault(vault_config)
            assert result is None
            mock_print.assert_called_with("Warning: Incomplete Vault configuration")

    def test_get_key_from_vault_auth_failed(self):
        """测试Vault认证失败"""
        vault_config = {
            "url": "https://vault.example.com",
            "token": "invalid_token",
            "secret_path": "secret/myapp"
        }

        # 模拟hvac库
        mock_hvac = Mock()
        mock_client = Mock()
        mock_client.is_authenticated.return_value = False
        mock_hvac.Client.return_value = mock_client

        km = KeyManager()

        with patch.dict('sys.modules', {'hvac': mock_hvac}):
            with patch('builtins.print') as mock_print:
                result = km._get_key_from_vault(vault_config)
                assert result is None
                mock_print.assert_called_with("Warning: Vault authentication failed")

    def test_get_key_from_vault_import_error(self):
        """测试Vault库未安装"""
        vault_config = {
            "url": "https://vault.example.com",
            "secret_path": "secret/myapp"
        }

        km = KeyManager()

        with patch('builtins.__import__', side_effect=ImportError("No module named 'hvac'")):
            with patch('builtins.print') as mock_print:
                result = km._get_key_from_vault(vault_config)
                assert result is None
                mock_print.assert_called_with("Warning: hvac library not installed. Cannot access Vault.")

    def test_get_key_from_vault_exception(self):
        """测试Vault访问异常"""
        vault_config = {
            "url": "https://vault.example.com",
            "token": "valid_token",
            "secret_path": "secret/myapp"
        }

        # 模拟hvac库抛出异常
        mock_hvac = Mock()
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("Vault error")
        mock_hvac.Client.return_value = mock_client

        km = KeyManager()

        with patch.dict('sys.modules', {'hvac': mock_hvac}):
            with patch('builtins.print') as mock_print:
                result = km._get_key_from_vault(vault_config)
                assert result is None
                mock_print.assert_called_with("Warning: Failed to get key from Vault: Vault error")

    def test_get_key_from_aws_kms_missing_key_id(self):
        """测试AWS KMS缺少key_id"""
        aws_config = {
            "region": "us-west-2"
            # 缺少key_id
        }

        km = KeyManager()

        # 模拟boto3库存在
        mock_boto3 = Mock()

        with patch.dict('sys.modules', {'boto3': mock_boto3}):
            with patch('builtins.print') as mock_print:
                result = km._get_key_from_aws_kms(aws_config)
                assert result is None
                mock_print.assert_called_with("Warning: AWS KMS key_id not specified")

    def test_get_key_from_aws_kms_import_error(self):
        """测试AWS boto3库未安装"""
        aws_config = {
            "key_id": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
        }

        km = KeyManager()

        with patch('builtins.__import__', side_effect=ImportError("No module named 'boto3'")):
            with patch('builtins.print') as mock_print:
                result = km._get_key_from_aws_kms(aws_config)
                assert result is None
                mock_print.assert_called_with("Warning: boto3 library not installed. Cannot access AWS KMS.")

    def test_get_key_from_aws_kms_exception(self):
        """测试AWS KMS访问异常"""
        aws_config = {
            "key_id": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
            "region": "us-east-1"
        }

        # 模拟boto3库
        mock_boto3 = Mock()
        mock_client = Mock()
        mock_client.describe_key.side_effect = Exception("AWS KMS error")
        mock_boto3.client.return_value = mock_client

        km = KeyManager()

        with patch.dict('sys.modules', {'boto3': mock_boto3}):
            with patch('builtins.print') as mock_print:
                result = km._get_key_from_aws_kms(aws_config)
                assert result is None
                mock_print.assert_called_with("Warning: Failed to get key from AWS KMS: AWS KMS error")

    def test_get_key_from_aws_kms_not_implemented(self):
        """测试AWS KMS功能未完全实现"""
        aws_config = {
            "key_id": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
            "region": "us-east-1"
        }

        # 模拟boto3库
        mock_boto3 = Mock()
        mock_client = Mock()
        mock_client.describe_key.return_value = {"KeyMetadata": {"KeyId": "test"}}
        mock_boto3.client.return_value = mock_client

        km = KeyManager()

        with patch.dict('sys.modules', {'boto3': mock_boto3}):
            with patch('builtins.print') as mock_print:
                result = km._get_key_from_aws_kms(aws_config)
                assert result is None
                mock_print.assert_called_with("Warning: AWS KMS integration needs specific implementation")
