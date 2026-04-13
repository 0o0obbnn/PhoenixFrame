"""测试加密解密工具模块"""
import pytest
from unittest.mock import patch, Mock
from src.phoenixframe.security.crypto import CryptoUtil


def test_crypto_util_initialization():
    """测试CryptoUtil初始化"""
    # 测试正常初始化
    with patch('src.phoenixframe.security.crypto.CRYPTOGRAPHY_AVAILABLE', True):
        crypto = CryptoUtil()
        assert crypto is not None
    
    # 测试缺少cryptography库时的错误
    with patch('src.phoenixframe.security.crypto.CRYPTOGRAPHY_AVAILABLE', False):
        with pytest.raises(ImportError, match="cryptography library is not installed"):
            CryptoUtil()


@patch('src.phoenixframe.security.crypto.CRYPTOGRAPHY_AVAILABLE', True)
@patch('src.phoenixframe.security.crypto.Fernet')
def test_generate_key(mock_fernet):
    """测试生成对称加密密钥"""
    mock_key = b"test_key_32_bytes_long_for_fernet"
    mock_fernet.generate_key.return_value = mock_key
    
    key = CryptoUtil.generate_key()
    
    assert key == mock_key
    mock_fernet.generate_key.assert_called_once()


@patch('src.phoenixframe.security.crypto.CRYPTOGRAPHY_AVAILABLE', True)
@patch('src.phoenixframe.security.crypto.Fernet')
def test_symmetric_encryption_decryption(mock_fernet_class):
    """测试对称加密解密"""
    # 模拟Fernet实例
    mock_fernet = Mock()
    mock_fernet_class.return_value = mock_fernet
    
    # 模拟加密结果
    test_data = "Hello, World!"
    test_key = b"test_key"
    encrypted_data = b"encrypted_data"
    
    mock_fernet.encrypt.return_value = encrypted_data
    mock_fernet.decrypt.return_value = test_data.encode('utf-8')
    
    # 测试加密
    result = CryptoUtil.encrypt_symmetric(test_data, test_key)
    assert result == encrypted_data
    mock_fernet.encrypt.assert_called_with(test_data.encode('utf-8'))
    
    # 测试解密
    decrypted = CryptoUtil.decrypt_symmetric(encrypted_data, test_key)
    assert decrypted == test_data.encode('utf-8')
    mock_fernet.decrypt.assert_called_with(encrypted_data)


@patch('src.phoenixframe.security.crypto.CRYPTOGRAPHY_AVAILABLE', True)
@patch('src.phoenixframe.security.crypto.rsa')
def test_generate_rsa_keypair(mock_rsa):
    """测试生成RSA密钥对"""
    mock_private_key = Mock()
    mock_public_key = Mock()
    mock_private_key.public_key.return_value = mock_public_key
    mock_rsa.generate_private_key.return_value = mock_private_key
    
    private_key, public_key = CryptoUtil.generate_rsa_keypair(2048)
    
    assert private_key == mock_private_key
    assert public_key == mock_public_key
    mock_rsa.generate_private_key.assert_called_with(
        public_exponent=65537,
        key_size=2048
    )


@patch('src.phoenixframe.security.crypto.CRYPTOGRAPHY_AVAILABLE', True)
def test_hash_data():
    """测试数据哈希"""
    with patch('src.phoenixframe.security.crypto.hashes') as mock_hashes:
        mock_digest = Mock()
        mock_hash_obj = Mock()
        mock_hash_obj.finalize.return_value = b'\x12\x34\x56\x78'
        mock_digest.return_value = mock_hash_obj
        mock_hashes.Hash = mock_digest
        mock_hashes.SHA256 = Mock()
        
        result = CryptoUtil.hash_data("test data", "sha256")
        
        assert result == "12345678"
        mock_hash_obj.update.assert_called_with(b"test data")
        mock_hash_obj.finalize.assert_called_once()


def test_base64_encoding_decoding():
    """测试Base64编码解码"""
    test_data = "Hello, World!"
    
    # 测试编码
    encoded = CryptoUtil.encode_base64(test_data)
    assert isinstance(encoded, str)
    
    # 测试解码
    decoded = CryptoUtil.decode_base64(encoded)
    assert decoded == test_data.encode('utf-8')
    
    # 测试字节数据编码
    test_bytes = b"Hello, Bytes!"
    encoded_bytes = CryptoUtil.encode_base64(test_bytes)
    decoded_bytes = CryptoUtil.decode_base64(encoded_bytes)
    assert decoded_bytes == test_bytes


@patch('src.phoenixframe.security.crypto.os.urandom')
def test_secure_random_bytes(mock_urandom):
    """测试生成安全随机字节"""
    mock_urandom.return_value = b'\x12\x34\x56\x78'
    
    result = CryptoUtil.secure_random_bytes(4)
    
    assert result == b'\x12\x34\x56\x78'
    mock_urandom.assert_called_with(4)


@patch('src.phoenixframe.security.crypto.os.urandom')
def test_secure_random_string(mock_urandom):
    """测试生成安全随机字符串"""
    # 模拟随机字节，每个字节对应字符集中的一个字符
    mock_urandom.return_value = bytes([0, 1, 2, 3, 4])
    
    charset = "abcde"
    result = CryptoUtil.secure_random_string(5, charset)
    
    assert len(result) == 5
    assert all(c in charset for c in result)
    mock_urandom.assert_called_with(5)


@patch('src.phoenixframe.security.crypto.CRYPTOGRAPHY_AVAILABLE', True)
@patch('src.phoenixframe.security.crypto.PBKDF2HMAC')
@patch('src.phoenixframe.security.crypto.os.urandom')
@patch('src.phoenixframe.security.crypto.base64.urlsafe_b64encode')
def test_derive_key_from_password(mock_b64encode, mock_urandom, mock_pbkdf2):
    """测试从密码派生密钥"""
    mock_salt = b'test_salt_16_bytes'
    mock_urandom.return_value = mock_salt
    
    mock_kdf = Mock()
    mock_kdf.derive.return_value = b'derived_key_32_bytes_long_for_test'
    mock_pbkdf2.return_value = mock_kdf
    
    mock_b64encode.return_value = b'encoded_key'
    
    # 测试不提供盐值
    key, salt = CryptoUtil.derive_key_from_password("password123")
    
    assert salt == mock_salt
    assert key == b'encoded_key'
    mock_kdf.derive.assert_called_with(b'password123')
    
    # 测试提供盐值
    provided_salt = b'provided_salt_16'
    key2, salt2 = CryptoUtil.derive_key_from_password("password123", provided_salt)
    
    assert salt2 == provided_salt


def test_hash_data_unsupported_algorithm():
    """测试不支持的哈希算法"""
    with patch('src.phoenixframe.security.crypto.CRYPTOGRAPHY_AVAILABLE', True):
        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            CryptoUtil.hash_data("test", "unsupported")
