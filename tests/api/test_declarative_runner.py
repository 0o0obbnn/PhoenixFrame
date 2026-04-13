"""测试声明式API测试引擎"""
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.phoenixframe.api.declarative_runner import DeclarativeAPIRunner
from src.phoenixframe.api.client import APIClient
from src.phoenixframe.api.response import APIResponse


class TestDeclarativeAPIRunner:
    """测试声明式API运行器"""
    
    def test_initialization_with_client(self):
        """测试使用提供的API客户端初始化"""
        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)
        
        assert runner.api_client is mock_client
        assert runner.variables == {}
        assert runner.validator_registry is not None
    
    def test_initialization_without_client(self):
        """测试不提供API客户端的初始化"""
        with patch('src.phoenixframe.api.declarative_runner.APIClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            runner = DeclarativeAPIRunner()
            
            assert runner.api_client is mock_client
            mock_client_class.assert_called_once()
    
    def test_run_yaml_file_not_found(self):
        """测试运行不存在的YAML文件"""
        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)

        with pytest.raises(FileNotFoundError, match="YAML file not found"):
            runner.run_yaml_file("nonexistent.yaml")
    
    def test_run_yaml_file_success(self):
        """测试成功运行YAML文件"""
        yaml_content = {
            'tests': [
                {
                    'name': 'test_api',
                    'method': 'GET',
                    'url': '/api/test'
                }
            ]
        }
        
        # 创建临时YAML文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_file = f.name
        
        try:
            mock_client = Mock()
            mock_response = Mock(spec=APIResponse)
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.text = '{"success": true}'
            mock_client.get.return_value = mock_response
            
            runner = DeclarativeAPIRunner(mock_client)
            
            with patch.object(runner, 'run_yaml_test') as mock_run_test:
                mock_run_test.return_value = {'passed': 1, 'failed': 0}
                
                result = runner.run_yaml_file(temp_file)
                
                assert result == {'passed': 1, 'failed': 0}
                mock_run_test.assert_called_once_with(yaml_content)
        
        finally:
            Path(temp_file).unlink()
    
    def test_run_yaml_test_with_variables(self):
        """测试运行包含变量的YAML测试"""
        yaml_content = {
            'variables': {
                'base_url': 'https://api.example.com',
                'api_key': 'test_key'
            },
            'tests': [
                {
                    'name': 'test_with_variables',
                    'method': 'GET',
                    'url': '${base_url}/users'
                }
            ]
        }
        
        mock_client = Mock()
        mock_response = Mock(spec=APIResponse)
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{"users": []}'
        mock_client.get.return_value = mock_response
        
        runner = DeclarativeAPIRunner(mock_client)
        result = runner.run_yaml_test(yaml_content)
        
        assert result['passed'] == 1
        assert result['failed'] == 0
        assert runner.variables['base_url'] == 'https://api.example.com'
        assert runner.variables['api_key'] == 'test_key'
        
        # 验证变量替换
        mock_client.get.assert_called_with('https://api.example.com/users')
    
    def test_run_yaml_test_with_setup_teardown(self):
        """测试运行包含setup和teardown的YAML测试"""
        yaml_content = {
            'setup': [
                {
                    'type': 'python',
                    'code': 'variables["setup_done"] = True'
                }
            ],
            'teardown': [
                {
                    'type': 'python',
                    'code': 'variables["teardown_done"] = True'
                }
            ],
            'tests': [
                {
                    'name': 'simple_test',
                    'method': 'GET',
                    'url': '/test'
                }
            ]
        }
        
        mock_client = Mock()
        mock_response = Mock(spec=APIResponse)
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{}'
        mock_client.get.return_value = mock_response
        
        runner = DeclarativeAPIRunner(mock_client)
        result = runner.run_yaml_test(yaml_content)
        
        assert result['passed'] == 1
        assert runner.variables['setup_done'] is True
        assert runner.variables['teardown_done'] is True
    
    def test_run_yaml_test_with_exception_still_runs_teardown(self):
        """测试即使测试失败，teardown仍然会执行"""
        yaml_content = {
            'teardown': [
                {
                    'type': 'python',
                    'code': 'variables["teardown_executed"] = True'
                }
            ],
            'tests': [
                {
                    'name': 'failing_test',
                    'method': 'GET',
                    'url': '/test'
                }
            ]
        }
        
        mock_client = Mock()
        mock_client.get.side_effect = Exception("Request failed")
        
        runner = DeclarativeAPIRunner(mock_client)
        result = runner.run_yaml_test(yaml_content)
        
        assert result['failed'] == 1
        assert runner.variables['teardown_executed'] is True
    
    def test_run_single_test_get_request(self):
        """测试运行单个GET请求"""
        test = {
            'name': 'get_test',
            'method': 'GET',
            'url': '/api/users',
            'headers': {'Authorization': 'Bearer token'},
            'params': {'page': 1}
        }
        
        mock_client = Mock()
        mock_response = Mock(spec=APIResponse)
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.text = '{"users": []}'
        mock_client.get.return_value = mock_response
        
        runner = DeclarativeAPIRunner(mock_client)
        result = runner._run_single_test(test, 0)
        
        assert result['name'] == 'get_test'
        assert result['passed'] is True
        assert result['errors'] == []
        assert result['response_data']['status_code'] == 200
        
        mock_client.get.assert_called_with(
            '/api/users',
            headers={'Authorization': 'Bearer token'},
            params={'page': 1}
        )
    
    def test_run_single_test_post_request(self):
        """测试运行单个POST请求"""
        test = {
            'name': 'post_test',
            'method': 'POST',
            'url': '/api/users',
            'json': {'name': 'John', 'email': 'john@example.com'},
            'data': {'extra': 'data'},
            'files': {'avatar': 'file_content'}
        }
        
        mock_client = Mock()
        mock_response = Mock(spec=APIResponse)
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = '{"id": 123}'
        mock_client.post.return_value = mock_response
        
        runner = DeclarativeAPIRunner(mock_client)
        result = runner._run_single_test(test, 0)
        
        assert result['passed'] is True
        mock_client.post.assert_called_with(
            '/api/users',
            json={'name': 'John', 'email': 'john@example.com'},
            data={'extra': 'data'},
            files={'avatar': 'file_content'}
        )
    
    def test_run_single_test_with_validation(self):
        """测试运行包含验证的单个测试"""
        test = {
            'name': 'test_with_validation',
            'method': 'GET',
            'url': '/api/status',
            'validate': [
                {
                    'validator': 'status_code',
                    'expected': 200
                }
            ]
        }
        
        mock_client = Mock()
        mock_response = Mock(spec=APIResponse)
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{"status": "ok"}'
        mock_client.get.return_value = mock_response
        
        mock_validator = Mock()
        
        runner = DeclarativeAPIRunner(mock_client)
        
        with patch.object(runner.validator_registry, 'get_validator', return_value=mock_validator):
            result = runner._run_single_test(test, 0)
            
            assert result['passed'] is True
            mock_validator.validate.assert_called_once_with(
                mock_response, 
                {'validator': 'status_code', 'expected': 200}
            )
    
    def test_run_single_test_with_extraction(self):
        """测试运行包含变量提取的单个测试"""
        test = {
            'name': 'test_with_extraction',
            'method': 'GET',
            'url': '/api/user',
            'extract': {
                'user_id': '$.id',
                'user_name': '$.name'
            }
        }
        
        mock_client = Mock()
        mock_response = Mock(spec=APIResponse)
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{"id": 123, "name": "John"}'
        mock_response.get_json_value.side_effect = lambda path: {
            '$.id': 123,
            '$.name': 'John'
        }[path]
        mock_client.get.return_value = mock_response
        
        runner = DeclarativeAPIRunner(mock_client)
        result = runner._run_single_test(test, 0)
        
        assert result['passed'] is True
        assert runner.variables['user_id'] == 123
        assert runner.variables['user_name'] == 'John'
    
    def test_run_single_test_extraction_failure(self):
        """测试变量提取失败不影响测试结果"""
        test = {
            'name': 'test_extraction_failure',
            'method': 'GET',
            'url': '/api/user',
            'extract': {
                'invalid_path': '$.nonexistent'
            }
        }
        
        mock_client = Mock()
        mock_response = Mock(spec=APIResponse)
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{}'
        mock_response.get_json_value.side_effect = Exception("Path not found")
        mock_client.get.return_value = mock_response
        
        runner = DeclarativeAPIRunner(mock_client)
        result = runner._run_single_test(test, 0)
        
        # 提取失败不应该影响测试通过
        assert result['passed'] is True
        assert 'invalid_path' not in runner.variables
    
    def test_run_single_test_request_failure(self):
        """测试请求失败的处理"""
        test = {
            'name': 'failing_test',
            'method': 'GET',
            'url': '/api/error'
        }
        
        mock_client = Mock()
        mock_client.get.side_effect = Exception("Connection error")
        
        runner = DeclarativeAPIRunner(mock_client)
        result = runner._run_single_test(test, 0)
        
        assert result['passed'] is False
        assert len(result['errors']) == 1
        assert "Connection error" in result['errors'][0]

    def test_substitute_variables_string(self):
        """测试字符串变量替换"""
        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)
        runner.variables = {
            'base_url': 'https://api.example.com',
            'version': 'v1',
            'user_id': 123
        }

        # 测试单个变量替换
        result = runner._substitute_variables('${base_url}/users')
        assert result == 'https://api.example.com/users'

        # 测试多个变量替换
        result = runner._substitute_variables('${base_url}/${version}/users/${user_id}')
        assert result == 'https://api.example.com/v1/users/123'

        # 测试无变量的字符串
        result = runner._substitute_variables('plain string')
        assert result == 'plain string'

    def test_substitute_variables_dict(self):
        """测试字典变量替换"""
        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)
        runner.variables = {
            'api_key': 'secret123',
            'user_id': 456
        }

        data = {
            'headers': {
                'Authorization': 'Bearer ${api_key}'
            },
            'url': '/users/${user_id}',
            'static_field': 'no_variables'
        }

        result = runner._substitute_variables(data)

        expected = {
            'headers': {
                'Authorization': 'Bearer secret123'
            },
            'url': '/users/456',
            'static_field': 'no_variables'
        }

        assert result == expected

    def test_substitute_variables_list(self):
        """测试列表变量替换"""
        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)
        runner.variables = {
            'endpoint': '/api/v1',
            'method': 'GET'
        }

        data = [
            '${endpoint}/users',
            {'method': '${method}'},
            'static_item'
        ]

        result = runner._substitute_variables(data)

        expected = [
            '/api/v1/users',
            {'method': 'GET'},
            'static_item'
        ]

        assert result == expected

    def test_substitute_variables_other_types(self):
        """测试其他类型的变量替换"""
        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)
        runner.variables = {'key': 'value'}

        # 数字
        assert runner._substitute_variables(123) == 123

        # 布尔值
        assert runner._substitute_variables(True) is True

        # None
        assert runner._substitute_variables(None) is None

    def test_run_validations(self):
        """测试运行验证规则"""
        mock_response = Mock()
        validations = [
            {
                'validator': 'status_code',
                'expected': 200
            },
            {
                'validator': 'json_path',
                'path': '$.status',
                'expected': 'success'
            },
            {
                # 无效的验证器（缺少validator字段）
                'expected': 'ignored'
            }
        ]

        mock_validator1 = Mock()
        mock_validator2 = Mock()

        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)

        with patch.object(runner.validator_registry, 'get_validator') as mock_get_validator:
            mock_get_validator.side_effect = lambda name: {
                'status_code': mock_validator1,
                'json_path': mock_validator2
            }.get(name)

            runner._run_validations(mock_response, validations)

            # 验证调用
            mock_validator1.validate.assert_called_once_with(
                mock_response,
                {'validator': 'status_code', 'expected': 200}
            )
            mock_validator2.validate.assert_called_once_with(
                mock_response,
                {'validator': 'json_path', 'path': '$.status', 'expected': 'success'}
            )

    def test_run_validations_unknown_validator(self):
        """测试运行未知验证器"""
        mock_response = Mock()
        validations = [
            {
                'validator': 'unknown_validator',
                'expected': 'value'
            }
        ]

        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)

        with patch.object(runner.validator_registry, 'get_validator', return_value=None):
            # 不应该抛出异常
            runner._run_validations(mock_response, validations)

    def test_extract_variables(self):
        """测试从响应中提取变量"""
        mock_response = Mock()
        mock_response.get_json_value.side_effect = lambda path: {
            '$.user.id': 123,
            '$.user.name': 'John Doe',
            '$.user.email': 'john@example.com'
        }[path]

        extractions = {
            'user_id': '$.user.id',
            'user_name': '$.user.name',
            'user_email': '$.user.email'
        }

        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)
        runner._extract_variables(mock_response, extractions)

        assert runner.variables['user_id'] == 123
        assert runner.variables['user_name'] == 'John Doe'
        assert runner.variables['user_email'] == 'john@example.com'

    def test_run_hooks_python_type(self):
        """测试运行Python类型的钩子"""
        hooks = [
            {
                'type': 'python',
                'code': 'variables["test_var"] = "test_value"'
            },
            {
                'type': 'python',
                'code': 'variables["calculated"] = 2 + 3'
            }
        ]

        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)
        runner._run_hooks(hooks)

        assert runner.variables['test_var'] == 'test_value'
        assert runner.variables['calculated'] == 5

    def test_run_hooks_request_type(self):
        """测试运行请求类型的钩子"""
        hooks = [
            {
                'type': 'request',
                'method': 'GET',
                'url': '/api/setup'
            }
        ]

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{}'
        mock_client.get.return_value = mock_response

        runner = DeclarativeAPIRunner(mock_client)

        with patch.object(runner, '_run_single_test') as mock_run_test:
            runner._run_hooks(hooks)

            mock_run_test.assert_called_once_with(hooks[0], 0)

    def test_run_hooks_unknown_type(self):
        """测试运行未知类型的钩子"""
        hooks = [
            {
                'type': 'unknown_type',
                'data': 'should_be_ignored'
            }
        ]

        mock_client = Mock(spec=APIClient)
        runner = DeclarativeAPIRunner(mock_client)
        # 不应该抛出异常
        runner._run_hooks(hooks)
