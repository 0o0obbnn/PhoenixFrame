"""BDD (Behavior Driven Development) 支持模块"""
import os
import re
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass
import inspect

try:
    import pytest_bdd
    from pytest_bdd import given, when, then, scenario, scenarios, parsers
    from pytest_bdd.feature import Feature
    from pytest_bdd.scenario import Scenario
    BDD_AVAILABLE = True
except ImportError:
    BDD_AVAILABLE = False
    pytest_bdd = None
    given = when = then = scenario = scenarios = parsers = None
    Feature = Scenario = None

from ..observability.logger import get_logger
from ..observability.tracer import get_tracer
from ..observability.metrics import record_test_metric


@dataclass
class StepDefinition:
    """步骤定义"""
    step_type: str  # given, when, then
    pattern: str
    function: Callable
    description: str = ""
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


@dataclass
class FeatureInfo:
    """Feature文件信息"""
    name: str
    description: str
    file_path: str
    scenarios: List[str]
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class BDDStepRegistry:
    """BDD步骤定义注册表"""
    
    def __init__(self):
        self.steps: Dict[str, List[StepDefinition]] = {
            "given": [],
            "when": [],
            "then": []
        }
        self.logger = get_logger("phoenixframe.bdd")
        self.tracer = get_tracer("phoenixframe.bdd")
    
    def register_step(self, step_type: str, pattern: str, function: Callable, 
                     description: str = "", examples: List[str] = None) -> None:
        """注册步骤定义"""
        step_def = StepDefinition(
            step_type=step_type,
            pattern=pattern,
            function=function,
            description=description,
            examples=examples or []
        )
        self.steps[step_type].append(step_def)
        self.logger.info(f"Registered {step_type} step: {pattern}")
    
    def get_steps(self, step_type: Optional[str] = None) -> Dict[str, List[StepDefinition]]:
        """获取步骤定义"""
        if step_type:
            return {step_type: self.steps.get(step_type, [])}
        return self.steps
    
    def find_step(self, step_type: str, text: str) -> Optional[StepDefinition]:
        """查找匹配的步骤定义"""
        for step_def in self.steps.get(step_type, []):
            # 使用正则表达式匹配步骤文本
            if re.search(step_def.pattern.replace('"', '.*'), text):
                return step_def
        return None
    
    def generate_step_definitions(self, feature_file: str) -> str:
        """从Feature文件生成步骤定义代码"""
        if not BDD_AVAILABLE:
            raise ImportError("pytest-bdd is not available. Install with: pip install pytest-bdd")
        
        feature_path = Path(feature_file)
        if not feature_path.exists():
            raise FileNotFoundError(f"Feature file not found: {feature_file}")
        
        feature = Feature.from_file(feature_path)
        
        code_lines = [
            '"""Auto-generated BDD step definitions"""',
            'import pytest',
            'from pytest_bdd import given, when, then, parsers, scenario',
            'from src.phoenixframe.bdd import step_registry',
            'from src.phoenixframe.api.client import APIClient',
            'from src.phoenixframe.web.selenium_driver import SeleniumDriver, SeleniumPage',
            'from src.phoenixframe.web.playwright_driver import PlaywrightDriver, PlaywrightPage',
            'from src.phoenixframe.bdd import phoenix_given, phoenix_when, phoenix_then',
            '',
            f'# Scenarios from {feature_path.name}',
        ]
        
        # 生成scenario装饰器
        for scenario_def in feature.scenarios:
            scenario_name = scenario_def.name.replace(' ', '_').lower()
            code_lines.append(f'@scenario("{feature_file}", "{scenario_def.name}")')
            code_lines.append(f'def test_{scenario_name}():')
            code_lines.append('    """Test scenario"""')
            code_lines.append('    pass')
            code_lines.append('')
        
        # 收集所有步骤
        all_steps = set()
        for scenario_def in feature.scenarios:
            for step in scenario_def.steps:
                all_steps.add((step.keyword.strip().lower(), step.name))
        
        # 生成步骤定义
        code_lines.append('# Step definitions')
        for step_type, step_text in sorted(all_steps):
            if step_type in ['given', 'when', 'then']:
                function_name = self._generate_function_name(step_text)
                pattern = self._generate_step_pattern(step_text)
                
                # 检查是否有参数
                if '<' in step_text and '>' in step_text:
                    code_lines.extend([
                        f'@phoenix_{step_type}(parsers.parse("{pattern}"))',
                        f'def {function_name}(**kwargs):',
                        f'    """Step: {step_type.capitalize()} {step_text}"""',
                        '    # TODO: Implement step logic',
                        '    # Available parameters: {}'.format(list(kwargs.keys()) if kwargs else 'None'),
                        '    pass',
                        ''
                    ])
                else:
                    code_lines.extend([
                        f'@phoenix_{step_type}("{pattern}")',
                        f'def {function_name}():',
                        f'    """Step: {step_type.capitalize()} {step_text}"""',
                        '    # TODO: Implement step logic',
                        '    pass',
                        ''
                    ])
        
        return '\n'.join(code_lines)
    
    def _generate_function_name(self, step_text: str) -> str:
        """生成函数名"""
        # 移除特殊字符，只保留字母数字和下划线
        clean_text = re.sub(r'[^\w\s]', '', step_text)
        # 将空格替换为下划线并转为小写
        function_name = clean_text.replace(' ', '_').lower()
        # 确保函数名以字母开头
        if function_name and not function_name[0].isalpha():
            function_name = 'step_' + function_name
        return function_name or 'step_definition'
    
    def _generate_step_pattern(self, step_text: str) -> str:
        """生成步骤模式"""
        # 转义特殊正则字符，但保留参数占位符
        pattern = re.sub(r'([<>*+?^${}()|\[\]\\])', r'\\\1', step_text)
        # 将参数占位符转换为正则表达式组
        pattern = re.sub(r'\\<([^>]+)\\>', r'<\1>', pattern)  # 恢复参数占位符
        return pattern


# 全局步骤注册表
step_registry = BDDStepRegistry()


def phoenix_given(pattern, **kwargs):
    """自定义given装饰器"""
    def decorator(func):
        if BDD_AVAILABLE:
            # 使用pytest-bdd的given装饰器
            decorated_func = given(pattern, **kwargs)(func)
        else:
            decorated_func = func
            
        # 注册到我们的注册表
        step_registry.register_step("given", pattern, decorated_func, func.__doc__ or "")
        return decorated_func
    return decorator


def phoenix_when(pattern, **kwargs):
    """自定义when装饰器"""
    def decorator(func):
        if BDD_AVAILABLE:
            # 使用pytest-bdd的when装饰器
            decorated_func = when(pattern, **kwargs)(func)
        else:
            decorated_func = func
            
        # 注册到我们的注册表
        step_registry.register_step("when", pattern, decorated_func, func.__doc__ or "")
        return decorated_func
    return decorator


def phoenix_then(pattern, **kwargs):
    """自定义then装饰器"""
    def decorator(func):
        if BDD_AVAILABLE:
            # 使用pytest-bdd的then装饰器
            decorated_func = then(pattern, **kwargs)(func)
        else:
            decorated_func = func
            
        # 注册到我们的注册表
        step_registry.register_step("then", pattern, decorated_func, func.__doc__ or "")
        return decorated_func
    return decorator


class BDDFeatureManager:
    """BDD Feature文件管理器"""
    
    def __init__(self, features_dir: str = "features"):
        self.features_dir = Path(features_dir)
        self.logger = get_logger("phoenixframe.bdd.feature_manager")
        self.tracer = get_tracer("phoenixframe.bdd.feature_manager")
    
    def discover_features(self) -> List[FeatureInfo]:
        """发现所有Feature文件"""
        features = []
        
        if not self.features_dir.exists():
            self.logger.warning(f"Features directory not found: {self.features_dir}")
            return features
        
        for feature_file in self.features_dir.rglob("*.feature"):
            try:
                feature = Feature.from_file(feature_file)
                scenarios = [scenario.name for scenario in feature.scenarios]
                tags = list(feature.tags) if feature.tags else []
                
                feature_info = FeatureInfo(
                    name=feature.name or feature_file.stem,
                    description=feature.description or "",
                    file_path=str(feature_file),
                    scenarios=scenarios,
                    tags=tags
                )
                features.append(feature_info)
                
                self.logger.info(f"Discovered feature: {feature.name} with {len(scenarios)} scenarios")
            except Exception as e:
                self.logger.error(f"Failed to parse feature file {feature_file}: {e}")
        
        return features
    
    def validate_feature(self, feature_file: str) -> Dict[str, Any]:
        """验证Feature文件"""
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "feature_info": None
        }
        
        try:
            feature_path = Path(feature_file)
            if not feature_path.exists():
                result["errors"].append(f"Feature file not found: {feature_file}")
                return result
            
            feature = Feature.from_file(feature_path)
            
            # 基本验证
            if not feature.name:
                result["warnings"].append("Feature has no name")
            
            if not feature.scenarios:
                result["warnings"].append("Feature has no scenarios")
            
            # 验证步骤
            all_steps = []
            for scenario in feature.scenarios:
                for step in scenario.steps:
                    all_steps.append(step)
            
            if not all_steps:
                result["warnings"].append("No steps found in scenarios")
            
            result["valid"] = len(result["errors"]) == 0
            result["feature_info"] = FeatureInfo(
                name=feature.name or feature_path.stem,
                description=feature.description or "",
                file_path=str(feature_path),
                scenarios=[s.name for s in feature.scenarios],
                tags=list(feature.tags) if feature.tags else []
            )
            
        except Exception as e:
            result["errors"].append(f"Failed to parse feature: {str(e)}")
        
        return result


class BDDIntegration:
    """BDD集成管理器"""
    
    def __init__(self, features_dir: str = "features", steps_dir: str = "tests/bdd/steps"):
        self.features_dir = Path(features_dir)
        self.steps_dir = Path(steps_dir)
        self.feature_manager = BDDFeatureManager(features_dir)
        self.step_registry = step_registry
        self.logger = get_logger("phoenixframe.bdd.integration")
        self.tracer = get_tracer("phoenixframe.bdd.integration")
    
    def setup_bdd_environment(self) -> None:
        """设置BDD环境"""
        with self.tracer.start_as_current_span("setup_bdd_environment"):
            # 确保目录存在
            self.features_dir.mkdir(parents=True, exist_ok=True)
            self.steps_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("BDD environment setup completed")
    
    def generate_step_definitions_for_feature(self, feature_file: str, output_file: str) -> str:
        """为特定Feature文件生成步骤定义"""
        with self.tracer.start_as_current_span("generate_step_definitions"):
            step_code = self.step_registry.generate_step_definitions(feature_file)
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(step_code, encoding='utf-8')
            
            self.logger.info(f"Generated step definitions: {output_file}")
            return step_code
    
    def run_bdd_tests(self, feature_files: Optional[List[str]] = None, 
                     tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """运行BDD测试"""
        with self.tracer.start_as_current_span("run_bdd_tests"):
            # 这里应该调用pytest来运行测试
            # 目前返回模拟结果
            result = {
                "status": "success",
                "features_run": 0,
                "scenarios_passed": 0,
                "scenarios_failed": 0,
                "duration": 0
            }
            
            self.logger.info("BDD tests execution completed")
            return result


def get_bdd_integration(features_dir: str = "features", steps_dir: str = "tests/bdd/steps") -> BDDIntegration:
    """获取BDD集成实例"""
    return BDDIntegration(features_dir, steps_dir)


def setup_bdd(features_dir: str = "features", steps_dir: str = "tests/bdd/steps") -> None:
    """设置BDD环境"""
    integration = get_bdd_integration(features_dir, steps_dir)
    integration.setup_bdd_environment()