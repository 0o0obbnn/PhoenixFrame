"""声明式API测试引擎"""
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from .client import APIClient
from .validators import ValidatorRegistry


class DeclarativeAPIRunner:
    """声明式API测试运行器"""
    
    def __init__(self, api_client: Optional[APIClient] = None):
        """
        初始化声明式运行器
        
        Args:
            api_client: API客户端实例，如果不提供则创建新实例
        """
        self.api_client = api_client or APIClient()
        self.validator_registry = ValidatorRegistry()
        self.variables = {}  # 存储测试变量
        
    def run_yaml_file(self, yaml_file: Union[str, Path]) -> Dict[str, Any]:
        """运行YAML测试文件"""
        yaml_path = Path(yaml_file)
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_file}")
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_content = yaml.safe_load(f)
        
        return self.run_yaml_test(yaml_content)
    
    def run_yaml_test(self, yaml_content: Dict[str, Any]) -> Dict[str, Any]:
        """运行YAML测试内容"""
        results = {
            'passed': 0,
            'failed': 0,
            'errors': [],
            'test_results': []
        }
        
        # 处理全局变量
        if 'variables' in yaml_content:
            self.variables.update(yaml_content['variables'])
        
        # 处理setup钩子
        if 'setup' in yaml_content:
            self._run_hooks(yaml_content['setup'])
        
        try:
            # 运行测试步骤
            tests = yaml_content.get('tests', [])
            for i, test in enumerate(tests):
                test_result = self._run_single_test(test, i)
                results['test_results'].append(test_result)
                
                if test_result['passed']:
                    results['passed'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].extend(test_result['errors'])
        
        finally:
            # 处理teardown钩子
            if 'teardown' in yaml_content:
                self._run_hooks(yaml_content['teardown'])
        
        return results
    
    def _run_single_test(self, test: Dict[str, Any], test_index: int) -> Dict[str, Any]:
        """运行单个测试"""
        test_result = {
            'name': test.get('name', f'test_{test_index}'),
            'passed': False,
            'errors': [],
            'response_data': None
        }
        
        try:
            # 替换变量
            test = self._substitute_variables(test)
            
            # 发送请求
            method = test.get('method', 'GET').lower()
            endpoint = test['url']
            
            # 准备请求参数
            request_kwargs = {}
            if 'headers' in test:
                request_kwargs['headers'] = test['headers']
            if 'params' in test:
                request_kwargs['params'] = test['params']
            if 'json' in test:
                request_kwargs['json'] = test['json']
            if 'data' in test:
                request_kwargs['data'] = test['data']
            if 'files' in test:
                request_kwargs['files'] = test['files']
            
            # 发送请求
            response = getattr(self.api_client, method)(endpoint, **request_kwargs)
            test_result['response_data'] = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response.text
            }
            
            # 运行验证
            if 'validate' in test:
                self._run_validations(response, test['validate'])
            
            # 提取变量
            if 'extract' in test:
                self._extract_variables(response, test['extract'])
            
            test_result['passed'] = True
            
        except Exception as e:
            test_result['errors'].append(str(e))
        
        return test_result
    
    def _run_validations(self, response, validations: List[Dict[str, Any]]):
        """运行验证规则"""
        for validation in validations:
            validator_name = validation.get('validator')
            if not validator_name:
                continue
            
            validator = self.validator_registry.get_validator(validator_name)
            if validator:
                validator.validate(response, validation)
    
    def _extract_variables(self, response, extractions: Dict[str, str]):
        """从响应中提取变量"""
        for var_name, jsonpath in extractions.items():
            try:
                value = response.get_json_value(jsonpath)
                self.variables[var_name] = value
            except Exception:
                # 提取失败不应该导致测试失败，只记录警告
                pass
    
    def _substitute_variables(self, data: Any) -> Any:
        """递归替换变量"""
        if isinstance(data, dict):
            return {k: self._substitute_variables(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_variables(item) for item in data]
        elif isinstance(data, str):
            # 简单的变量替换，格式：${variable_name}
            for var_name, var_value in self.variables.items():
                data = data.replace(f'${{{var_name}}}', str(var_value))
            return data
        else:
            return data
    
    def _run_hooks(self, hooks: List[Dict[str, Any]]):
        """运行钩子函数"""
        for hook in hooks:
            hook_type = hook.get('type')
            if hook_type == 'python':
                # 执行Python代码
                code = hook.get('code', '')
                exec(code, {'variables': self.variables, 'api_client': self.api_client})
            elif hook_type == 'request':
                # 发送HTTP请求
                self._run_single_test(hook, 0)
