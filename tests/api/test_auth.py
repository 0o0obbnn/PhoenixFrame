"""测试API认证策略模块"""
import pytest
import time
import base64
from unittest.mock import Mock, patch, MagicMock
from src.phoenixframe.api.auth import (
    AuthStrategy, BearerTokenAuth, BasicAuth, OAuth2TokenAuth, 
    ApiKeyAuth, JWTAuth, create_auth_from_config
)


class TestBearerTokenAuth:
    """测试Bearer Token认证策略"""
    
    def test_initialization(self):
        """测试初始化"""
        token = "test_bearer_token"
        auth = BearerTokenAuth(token)
        assert auth.token == token
    
    def test_get_auth_headers(self):
        """测试获取认证头"""
        token = "test_bearer_token"
        auth = BearerTokenAuth(token)
        headers = auth.get_auth_headers()
        
        assert headers == {'Authorization': f'Bearer {token}'}
    
    def test_refresh_auth(self):
        """测试刷新认证（Bearer Token不需要刷新）"""
        auth = BearerTokenAuth("token")
        result = auth.refresh_auth()
        assert result is True


class TestBasicAuth:
    """测试Basic认证策略"""
    
    def test_initialization(self):
        """测试初始化"""
        username = "testuser"
        password = "testpass"
        auth = BasicAuth(username, password)
        
        assert auth.username == username
        assert auth.password == password
    
    def test_get_auth_headers(self):
        """测试获取认证头"""
        username = "testuser"
        password = "testpass"
        auth = BasicAuth(username, password)
        headers = auth.get_auth_headers()
        
        # 验证Base64编码
        credentials = f"{username}:{password}"
        expected_encoded = base64.b64encode(credentials.encode()).decode()
        expected_header = f'Basic {expected_encoded}'
        
        assert headers == {'Authorization': expected_header}
    
    def test_refresh_auth(self):
        """测试刷新认证（Basic认证不需要刷新）"""
        auth = BasicAuth("user", "pass")
        result = auth.refresh_auth()
        assert result is True


class TestOAuth2TokenAuth:
    """测试OAuth2 Token认证策略"""
    
    def test_initialization_with_initial_token(self):
        """测试带初始token的初始化"""
        auth = OAuth2TokenAuth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://auth.example.com/token",
            initial_token="initial_token"
        )
        
        assert auth.client_id == "test_client"
        assert auth.client_secret == "test_secret"
        assert auth.token_url == "https://auth.example.com/token"
        assert auth.access_token == "initial_token"
    
    @patch('src.phoenixframe.api.auth.requests.post')
    def test_initialization_without_initial_token(self, mock_post):
        """测试不带初始token的初始化（会自动获取）"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        auth = OAuth2TokenAuth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://auth.example.com/token"
        )
        
        assert auth.access_token == "new_token"
        mock_post.assert_called_once()
    
    def test_get_auth_headers_valid_token(self):
        """测试获取认证头（token有效）"""
        auth = OAuth2TokenAuth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://auth.example.com/token",
            initial_token="valid_token"
        )
        auth.token_expires_at = time.time() + 3600  # 1小时后过期
        
        headers = auth.get_auth_headers()
        assert headers == {'Authorization': 'Bearer valid_token'}
    
    @patch('src.phoenixframe.api.auth.requests.post')
    def test_get_auth_headers_expired_token(self, mock_post):
        """测试获取认证头（token过期，需要刷新）"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'refreshed_token',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        auth = OAuth2TokenAuth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://auth.example.com/token",
            initial_token="expired_token"
        )
        auth.token_expires_at = time.time() - 100  # 已过期
        
        headers = auth.get_auth_headers()
        assert headers == {'Authorization': 'Bearer refreshed_token'}
        mock_post.assert_called()
    
    @patch('src.phoenixframe.api.auth.requests.post')
    def test_refresh_auth_client_credentials(self, mock_post):
        """测试客户端凭证模式刷新"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 7200,
            'refresh_token': 'new_refresh_token'
        }
        mock_post.return_value = mock_response
        
        auth = OAuth2TokenAuth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://auth.example.com/token",
            initial_token="old_token"
        )
        
        result = auth.refresh_auth()
        
        assert result is True
        assert auth.access_token == "new_access_token"
        assert auth.refresh_token == "new_refresh_token"
        
        # 验证请求参数
        expected_data = {
            'grant_type': 'client_credentials',
            'client_id': 'test_client',
            'client_secret': 'test_secret'
        }
        mock_post.assert_called_with("https://auth.example.com/token", data=expected_data)
    
    @patch('src.phoenixframe.api.auth.requests.post')
    def test_refresh_auth_with_refresh_token(self, mock_post):
        """测试使用refresh_token刷新"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        auth = OAuth2TokenAuth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://auth.example.com/token",
            initial_token="old_token",
            refresh_token="old_refresh_token"
        )
        
        result = auth.refresh_auth()
        
        assert result is True
        assert auth.access_token == "new_access_token"
        
        # 验证使用refresh_token模式
        expected_data = {
            'grant_type': 'refresh_token',
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'refresh_token': 'old_refresh_token'
        }
        mock_post.assert_called_with("https://auth.example.com/token", data=expected_data)
    
    @patch('src.phoenixframe.api.auth.requests.post')
    def test_refresh_auth_failure(self, mock_post):
        """测试刷新失败"""
        mock_post.side_effect = Exception("Network error")
        
        auth = OAuth2TokenAuth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://auth.example.com/token",
            initial_token="token"
        )
        
        result = auth.refresh_auth()
        assert result is False


class TestApiKeyAuth:
    """测试API Key认证策略"""
    
    def test_initialization_default_header(self):
        """测试默认header名称的初始化"""
        api_key = "test_api_key"
        auth = ApiKeyAuth(api_key)
        
        assert auth.api_key == api_key
        assert auth.header_name == 'X-API-Key'
    
    def test_initialization_custom_header(self):
        """测试自定义header名称的初始化"""
        api_key = "test_api_key"
        header_name = "Custom-API-Key"
        auth = ApiKeyAuth(api_key, header_name)
        
        assert auth.api_key == api_key
        assert auth.header_name == header_name
    
    def test_get_auth_headers_default(self):
        """测试获取认证头（默认header名称）"""
        api_key = "test_api_key"
        auth = ApiKeyAuth(api_key)
        headers = auth.get_auth_headers()
        
        assert headers == {'X-API-Key': api_key}
    
    def test_get_auth_headers_custom(self):
        """测试获取认证头（自定义header名称）"""
        api_key = "test_api_key"
        header_name = "Custom-API-Key"
        auth = ApiKeyAuth(api_key, header_name)
        headers = auth.get_auth_headers()
        
        assert headers == {header_name: api_key}
    
    def test_refresh_auth(self):
        """测试刷新认证（API Key不需要刷新）"""
        auth = ApiKeyAuth("key")
        result = auth.refresh_auth()
        assert result is True


class TestJWTAuth:
    """测试JWT认证策略"""

    @patch('src.phoenixframe.api.auth.requests.post')
    def test_initialization_successful_login(self, mock_post):
        """测试成功登录的初始化"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'jwt_token_123'
        }
        mock_post.return_value = mock_response

        auth = JWTAuth(
            username="testuser",
            password="testpass",
            login_url="https://api.example.com/login"
        )

        assert auth.username == "testuser"
        assert auth.password == "testpass"
        assert auth.login_url == "https://api.example.com/login"
        assert auth.jwt_token == "jwt_token_123"

        # 验证登录请求
        expected_data = {
            'username': 'testuser',
            'password': 'testpass'
        }
        mock_post.assert_called_with("https://api.example.com/login", json=expected_data)

    @patch('src.phoenixframe.api.auth.requests.post')
    def test_get_auth_headers_valid_token(self, mock_post):
        """测试获取认证头（token有效）"""
        mock_response = Mock()
        mock_response.json.return_value = {'access_token': 'valid_jwt_token'}
        mock_post.return_value = mock_response

        auth = JWTAuth("user", "pass", "https://api.example.com/login")
        auth.token_expires_at = time.time() + 3600  # 1小时后过期

        headers = auth.get_auth_headers()
        assert headers == {'Authorization': 'Bearer valid_jwt_token'}

    @patch('src.phoenixframe.api.auth.requests.post')
    def test_get_auth_headers_expired_token(self, mock_post):
        """测试获取认证头（token过期，需要刷新）"""
        # 第一次调用（初始化）
        mock_response1 = Mock()
        mock_response1.json.return_value = {'access_token': 'initial_token'}

        # 第二次调用（刷新）
        mock_response2 = Mock()
        mock_response2.json.return_value = {'access_token': 'refreshed_jwt_token'}

        mock_post.side_effect = [mock_response1, mock_response2]

        auth = JWTAuth("user", "pass", "https://api.example.com/login")
        auth.token_expires_at = time.time() - 100  # 已过期

        headers = auth.get_auth_headers()
        assert headers == {'Authorization': 'Bearer refreshed_jwt_token'}
        assert mock_post.call_count == 2

    @patch('src.phoenixframe.api.auth.requests.post')
    def test_refresh_auth_with_jwt_parsing(self, mock_post):
        """测试刷新认证并解析JWT过期时间"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'token': 'jwt_with_exp_claim'  # 使用'token'字段而不是'access_token'
        }
        mock_post.return_value = mock_response

        # 模拟JWT库存在并成功解码
        future_exp = int(time.time()) + 7200  # 2小时后过期
        with patch('builtins.__import__') as mock_import:
            mock_jwt = Mock()
            mock_jwt.decode.return_value = {'exp': future_exp}
            mock_import.return_value = mock_jwt

            auth = JWTAuth("user", "pass", "https://api.example.com/login")

            assert auth.jwt_token == "jwt_with_exp_claim"
            assert auth.token_expires_at == future_exp

    @patch('src.phoenixframe.api.auth.requests.post')
    def test_refresh_auth_jwt_parsing_failure(self, mock_post):
        """测试JWT解析失败时的默认过期时间"""
        mock_response = Mock()
        mock_response.json.return_value = {'access_token': 'invalid_jwt_token'}
        mock_post.return_value = mock_response

        # 模拟JWT库不存在或解析失败
        with patch('builtins.__import__', side_effect=ImportError("No module named 'jwt'")):
            auth = JWTAuth("user", "pass", "https://api.example.com/login")

            # 应该设置默认过期时间（1小时）
            expected_min_exp = time.time() + 3500  # 略小于1小时，考虑执行时间
            assert auth.token_expires_at >= expected_min_exp

    @patch('src.phoenixframe.api.auth.requests.post')
    def test_refresh_auth_failure(self, mock_post):
        """测试登录失败"""
        mock_post.side_effect = Exception("Login failed")

        auth = JWTAuth("user", "pass", "https://api.example.com/login")
        result = auth.refresh_auth()

        assert result is False


class TestCreateAuthFromConfig:
    """测试认证策略工厂函数"""

    def test_create_bearer_auth(self):
        """测试创建Bearer Token认证"""
        config = {
            'type': 'bearer',
            'token': 'test_bearer_token'
        }

        auth = create_auth_from_config(config)

        assert isinstance(auth, BearerTokenAuth)
        assert auth.token == 'test_bearer_token'

    def test_create_basic_auth(self):
        """测试创建Basic认证"""
        config = {
            'type': 'basic',
            'username': 'testuser',
            'password': 'testpass'
        }

        auth = create_auth_from_config(config)

        assert isinstance(auth, BasicAuth)
        assert auth.username == 'testuser'
        assert auth.password == 'testpass'

    @patch('src.phoenixframe.api.auth.requests.post')
    def test_create_oauth2_auth(self, mock_post):
        """测试创建OAuth2认证"""
        mock_response = Mock()
        mock_response.json.return_value = {'access_token': 'token', 'expires_in': 3600}
        mock_post.return_value = mock_response

        config = {
            'type': 'oauth2',
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'token_url': 'https://auth.example.com/token',
            'initial_token': 'initial_token',
            'refresh_token': 'refresh_token'
        }

        auth = create_auth_from_config(config)

        assert isinstance(auth, OAuth2TokenAuth)
        assert auth.client_id == 'test_client'
        assert auth.client_secret == 'test_secret'
        assert auth.token_url == 'https://auth.example.com/token'

    def test_create_apikey_auth_default_header(self):
        """测试创建API Key认证（默认header）"""
        config = {
            'type': 'apikey',
            'api_key': 'test_api_key'
        }

        auth = create_auth_from_config(config)

        assert isinstance(auth, ApiKeyAuth)
        assert auth.api_key == 'test_api_key'
        assert auth.header_name == 'X-API-Key'

    def test_create_apikey_auth_custom_header(self):
        """测试创建API Key认证（自定义header）"""
        config = {
            'type': 'apikey',
            'api_key': 'test_api_key',
            'header_name': 'Custom-Key'
        }

        auth = create_auth_from_config(config)

        assert isinstance(auth, ApiKeyAuth)
        assert auth.api_key == 'test_api_key'
        assert auth.header_name == 'Custom-Key'

    @patch('src.phoenixframe.api.auth.requests.post')
    def test_create_jwt_auth(self, mock_post):
        """测试创建JWT认证"""
        mock_response = Mock()
        mock_response.json.return_value = {'access_token': 'jwt_token'}
        mock_post.return_value = mock_response

        config = {
            'type': 'jwt',
            'username': 'testuser',
            'password': 'testpass',
            'login_url': 'https://api.example.com/login'
        }

        auth = create_auth_from_config(config)

        assert isinstance(auth, JWTAuth)
        assert auth.username == 'testuser'
        assert auth.password == 'testpass'
        assert auth.login_url == 'https://api.example.com/login'

    def test_create_unknown_auth_type(self):
        """测试未知认证类型"""
        config = {
            'type': 'unknown_type',
            'some_param': 'value'
        }

        auth = create_auth_from_config(config)
        assert auth is None

    def test_create_auth_case_insensitive(self):
        """测试认证类型大小写不敏感"""
        config = {
            'type': 'BEARER',
            'token': 'test_token'
        }

        auth = create_auth_from_config(config)
        assert isinstance(auth, BearerTokenAuth)
