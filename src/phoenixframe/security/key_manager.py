"""密钥管理模块"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Union


class KeyManager:
    """密钥管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化密钥管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or "configs/keys.json"
        self.keys: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """加载密钥配置"""
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.keys = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load key config from {self.config_path}: {e}")
                self.keys = {}
        else:
            self.keys = {}
    
    def _save_config(self) -> None:
        """保存密钥配置"""
        config_file = Path(self.config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.keys, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Failed to save key config to {self.config_path}: {e}")
    
    def get_key(self, key_name: str) -> Optional[str]:
        """
        获取密钥
        
        优先级：环境变量 > KMS > 本地文件 > 配置文件
        
        Args:
            key_name: 密钥名称
            
        Returns:
            Optional[str]: 密钥值
        """
        # 1. 尝试从环境变量获取
        env_key = f"PHOENIX_KEY_{key_name.upper()}"
        env_value = os.getenv(env_key)
        if env_value:
            return env_value
        
        # 2. 尝试从配置文件获取
        key_config = self.keys.get(key_name, {})
        if isinstance(key_config, str):
            # 直接存储的密钥值（不推荐）
            return key_config
        elif isinstance(key_config, dict):
            # 从不同来源获取密钥
            source = key_config.get("source", "direct")
            
            if source == "env":
                # 从环境变量获取
                env_var = key_config.get("env_var")
                if env_var:
                    return os.getenv(env_var)
            
            elif source == "file":
                # 从文件获取
                file_path = key_config.get("file_path")
                if file_path:
                    return self._read_key_from_file(file_path)
            
            elif source == "kms":
                # 从KMS获取（需要实现具体的KMS集成）
                return self._get_key_from_kms(key_config)
            
            elif source == "direct":
                # 直接存储的值
                return key_config.get("value")
        
        return None
    
    def set_key(self, key_name: str, value: Union[str, Dict[str, Any]]) -> None:
        """
        设置密钥
        
        Args:
            key_name: 密钥名称
            value: 密钥值或配置
        """
        self.keys[key_name] = value
        self._save_config()
    
    def set_key_from_env(self, key_name: str, env_var: str) -> None:
        """
        设置从环境变量获取的密钥
        
        Args:
            key_name: 密钥名称
            env_var: 环境变量名
        """
        self.keys[key_name] = {
            "source": "env",
            "env_var": env_var
        }
        self._save_config()
    
    def set_key_from_file(self, key_name: str, file_path: str) -> None:
        """
        设置从文件获取的密钥
        
        Args:
            key_name: 密钥名称
            file_path: 文件路径
        """
        self.keys[key_name] = {
            "source": "file",
            "file_path": file_path
        }
        self._save_config()
    
    def set_key_from_kms(self, key_name: str, kms_config: Dict[str, Any]) -> None:
        """
        设置从KMS获取的密钥
        
        Args:
            key_name: 密钥名称
            kms_config: KMS配置
        """
        kms_config["source"] = "kms"
        self.keys[key_name] = kms_config
        self._save_config()
    
    def remove_key(self, key_name: str) -> bool:
        """
        删除密钥
        
        Args:
            key_name: 密钥名称
            
        Returns:
            bool: 是否删除成功
        """
        if key_name in self.keys:
            del self.keys[key_name]
            self._save_config()
            return True
        return False
    
    def list_keys(self) -> list:
        """
        列出所有密钥名称
        
        Returns:
            list: 密钥名称列表
        """
        return list(self.keys.keys())
    
    def _read_key_from_file(self, file_path: str) -> Optional[str]:
        """从文件读取密钥"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except IOError as e:
            print(f"Warning: Failed to read key from file {file_path}: {e}")
            return None
    
    def _get_key_from_kms(self, kms_config: Dict[str, Any]) -> Optional[str]:
        """
        从KMS获取密钥
        
        Args:
            kms_config: KMS配置
            
        Returns:
            Optional[str]: 密钥值
        """
        kms_type = kms_config.get("type", "").lower()
        
        if kms_type == "vault":
            return self._get_key_from_vault(kms_config)
        elif kms_type == "aws":
            return self._get_key_from_aws_kms(kms_config)
        else:
            print(f"Warning: Unsupported KMS type: {kms_type}")
            return None
    
    def _get_key_from_vault(self, vault_config: Dict[str, Any]) -> Optional[str]:
        """从HashiCorp Vault获取密钥"""
        try:
            import hvac
            
            vault_url = vault_config.get("url")
            vault_token = vault_config.get("token") or os.getenv("VAULT_TOKEN")
            secret_path = vault_config.get("secret_path")
            secret_key = vault_config.get("secret_key", "value")
            
            if not all([vault_url, vault_token, secret_path]):
                print("Warning: Incomplete Vault configuration")
                return None
            
            client = hvac.Client(url=vault_url, token=vault_token)
            
            if not client.is_authenticated():
                print("Warning: Vault authentication failed")
                return None
            
            response = client.secrets.kv.v2.read_secret_version(path=secret_path)
            return response['data']['data'].get(secret_key)
            
        except ImportError:
            print("Warning: hvac library not installed. Cannot access Vault.")
            return None
        except Exception as e:
            print(f"Warning: Failed to get key from Vault: {e}")
            return None
    
    def _get_key_from_aws_kms(self, aws_config: Dict[str, Any]) -> Optional[str]:
        """从AWS KMS获取密钥"""
        try:
            import boto3
            
            key_id = aws_config.get("key_id")
            region = aws_config.get("region", "us-east-1")
            
            if not key_id:
                print("Warning: AWS KMS key_id not specified")
                return None
            
            kms_client = boto3.client('kms', region_name=region)
            
            # 这里需要根据具体需求实现密钥获取逻辑
            # 例如解密数据或获取数据密钥
            response = kms_client.describe_key(KeyId=key_id)
            
            # 实际实现需要根据具体的KMS使用场景
            print("Warning: AWS KMS integration needs specific implementation")
            return None
            
        except ImportError:
            print("Warning: boto3 library not installed. Cannot access AWS KMS.")
            return None
        except Exception as e:
            print(f"Warning: Failed to get key from AWS KMS: {e}")
            return None
