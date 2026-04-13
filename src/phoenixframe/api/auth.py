"""API认证策略"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
import time
import requests


class AuthStrategy(ABC):
    """认证策略基类"""
    
    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        pass
    
    @abstractmethod
    def refresh_auth(self) -> bool:
        """刷新认证信息"""
        pass


class BearerTokenAuth(AuthStrategy):
    """Bearer Token认证策略"""
    
    def __init__(self, token: str):
        self.token = token
    
    def get_auth_headers(self) -> Dict[str, str]:
        return {'Authorization': f'Bearer {self.token}'}
    
    def refresh_auth(self) -> bool:
        # 静态token不需要刷新
        return True


class BasicAuth(AuthStrategy):
    """Basic认证策略"""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
    
    def get_auth_headers(self) -> Dict[str, str]:
        import base64
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {'Authorization': f'Basic {encoded_credentials}'}
    
    def refresh_auth(self) -> bool:
        # Basic认证不需要刷新
        return True


class OAuth2TokenAuth(AuthStrategy):
    """OAuth2 Token认证策略，支持自动刷新"""
    
    def __init__(self, client_id: str, client_secret: str, token_url: str, 
                 initial_token: Optional[str] = None, refresh_token: Optional[str] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.access_token = initial_token
        self.refresh_token = refresh_token
        self.token_expires_at = 0
        
        # 如果没有初始token，立即获取
        if not self.access_token:
            self.refresh_auth()
    
    def get_auth_headers(self) -> Dict[str, str]:
        # 检查token是否即将过期（提前30秒刷新）
        if time.time() >= (self.token_expires_at - 30):
            self.refresh_auth()
        
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def refresh_auth(self) -> bool:
        """刷新访问令牌"""
        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            # 如果有refresh_token，使用refresh_token方式
            if self.refresh_token:
                data['grant_type'] = 'refresh_token'
                data['refresh_token'] = self.refresh_token
            
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # 计算token过期时间
            expires_in = token_data.get('expires_in', 3600)  # 默认1小时
            self.token_expires_at = time.time() + expires_in
            
            # 更新refresh_token（如果有）
            if 'refresh_token' in token_data:
                self.refresh_token = token_data['refresh_token']
            
            return True
            
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            return False


class ApiKeyAuth(AuthStrategy):
    """API Key认证策略"""
    
    def __init__(self, api_key: str, header_name: str = 'X-API-Key'):
        self.api_key = api_key
        self.header_name = header_name
    
    def get_auth_headers(self) -> Dict[str, str]:
        return {self.header_name: self.api_key}
    
    def refresh_auth(self) -> bool:
        # API Key不需要刷新
        return True


class JWTAuth(AuthStrategy):
    """JWT认证策略，支持自动刷新"""
    
    def __init__(self, username: str, password: str, login_url: str):
        self.username = username
        self.password = password
        self.login_url = login_url
        self.jwt_token = None
        self.token_expires_at = 0
        
        # 立即登录获取token
        self.refresh_auth()
    
    def get_auth_headers(self) -> Dict[str, str]:
        # 检查token是否即将过期（提前30秒刷新）
        if time.time() >= (self.token_expires_at - 30):
            self.refresh_auth()
        
        return {'Authorization': f'Bearer {self.jwt_token}'}
    
    def refresh_auth(self) -> bool:
        """通过用户名密码登录获取JWT token"""
        try:
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            response = requests.post(self.login_url, json=login_data)
            response.raise_for_status()
            
            token_data = response.json()
            self.jwt_token = token_data.get('access_token') or token_data.get('token')
            
            # 尝试解析JWT token的过期时间
            if self.jwt_token:
                try:
                    import jwt
                    decoded = jwt.decode(self.jwt_token, options={"verify_signature": False})
                    self.token_expires_at = decoded.get('exp', time.time() + 3600)
                except Exception as e:
                    # 如果解析失败，默认1小时过期
                    self.token_expires_at = time.time() + 3600
            
            return True
            
        except Exception as e:
            print(f"Failed to login and get JWT token: {e}")
            return False


def create_auth_from_config(auth_config: Dict[str, str]) -> Optional[AuthStrategy]:
    """从配置创建认证策略"""
    auth_type = auth_config.get('type', '').lower()
    
    if auth_type == 'bearer':
        return BearerTokenAuth(auth_config['token'])
    elif auth_type == 'basic':
        return BasicAuth(auth_config['username'], auth_config['password'])
    elif auth_type == 'oauth2':
        return OAuth2TokenAuth(
            auth_config['client_id'],
            auth_config['client_secret'],
            auth_config['token_url'],
            auth_config.get('initial_token'),
            auth_config.get('refresh_token')
        )
    elif auth_type == 'apikey':
        return ApiKeyAuth(
            auth_config['api_key'],
            auth_config.get('header_name', 'X-API-Key')
        )
    elif auth_type == 'jwt':
        return JWTAuth(
            auth_config['username'],
            auth_config['password'],
            auth_config['login_url']
        )
    else:
        return None
