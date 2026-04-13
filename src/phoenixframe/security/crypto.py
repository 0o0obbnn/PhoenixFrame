"""加密解密工具模块"""
import base64
import os
from typing import Union, Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


class CryptoUtil:
    """加密解密工具类"""
    
    def __init__(self):
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError("cryptography library is not installed. Please install it with: pip install cryptography")
    
    @staticmethod
    def generate_key() -> bytes:
        """生成对称加密密钥"""
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt_symmetric(data: Union[str, bytes], key: bytes) -> bytes:
        """
        对称加密
        
        Args:
            data: 要加密的数据
            key: 加密密钥
            
        Returns:
            bytes: 加密后的数据
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        fernet = Fernet(key)
        return fernet.encrypt(data)
    
    @staticmethod
    def decrypt_symmetric(encrypted_data: bytes, key: bytes) -> bytes:
        """
        对称解密
        
        Args:
            encrypted_data: 加密的数据
            key: 解密密钥
            
        Returns:
            bytes: 解密后的数据
        """
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data)
    
    @staticmethod
    def generate_rsa_keypair(key_size: int = 2048) -> tuple:
        """
        生成RSA密钥对
        
        Args:
            key_size: 密钥长度
            
        Returns:
            tuple: (私钥, 公钥)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        public_key = private_key.public_key()
        
        return private_key, public_key
    
    @staticmethod
    def encrypt_rsa(data: Union[str, bytes], public_key) -> bytes:
        """
        RSA加密
        
        Args:
            data: 要加密的数据
            public_key: RSA公钥
            
        Returns:
            bytes: 加密后的数据
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return encrypted
    
    @staticmethod
    def decrypt_rsa(encrypted_data: bytes, private_key) -> bytes:
        """
        RSA解密
        
        Args:
            encrypted_data: 加密的数据
            private_key: RSA私钥
            
        Returns:
            bytes: 解密后的数据
        """
        decrypted = private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple:
        """
        从密码派生密钥
        
        Args:
            password: 密码
            salt: 盐值，如果为None则自动生成
            
        Returns:
            tuple: (密钥, 盐值)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    @staticmethod
    def hash_data(data: Union[str, bytes], algorithm: str = "sha256") -> str:
        """
        计算数据哈希值
        
        Args:
            data: 要哈希的数据
            algorithm: 哈希算法
            
        Returns:
            str: 哈希值（十六进制）
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if algorithm.lower() == "sha256":
            digest = hashes.Hash(hashes.SHA256())
        elif algorithm.lower() == "sha512":
            digest = hashes.Hash(hashes.SHA512())
        elif algorithm.lower() == "md5":
            digest = hashes.Hash(hashes.MD5())
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        digest.update(data)
        return digest.finalize().hex()
    
    @staticmethod
    def encode_base64(data: Union[str, bytes]) -> str:
        """Base64编码"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.b64encode(data).decode('utf-8')
    
    @staticmethod
    def decode_base64(encoded_data: str) -> bytes:
        """Base64解码"""
        return base64.b64decode(encoded_data)
    
    @staticmethod
    def secure_random_bytes(length: int) -> bytes:
        """生成安全随机字节"""
        return os.urandom(length)
    
    @staticmethod
    def secure_random_string(length: int, charset: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") -> str:
        """
        生成安全随机字符串
        
        Args:
            length: 字符串长度
            charset: 字符集
            
        Returns:
            str: 随机字符串
        """
        random_bytes = os.urandom(length)
        return ''.join(charset[b % len(charset)] for b in random_bytes)
