"""PhoenixFrame - 企业级自动化测试框架"""

# 版本信息
__version__ = "3.2.0"
__author__ = "PhoenixFrame Team"
__description__ = "Enterprise-level automated testing framework"

# 尝试导入核心组件，失败时提供友好错误信息
def _safe_import_with_error(module_path, component_name, feature_name):
    """安全导入并在失败时提供错误信息"""
    try:
        module = __import__(module_path, fromlist=[component_name])
        return getattr(module, component_name)
    except ImportError as e:
        def placeholder(*args, **kwargs):
            raise ImportError(
                f"{feature_name} 功能不可用。缺少依赖: {str(e)}\n"
                f"请运行: pip install phoenixframe[all]"
            )
        return placeholder

# 核心组件（延迟导入）
def get_core_components():
    """获取核心组件"""
    try:
        from .core.config import PhoenixConfig
        from .core.runner import PhoenixRunner
        return PhoenixConfig, PhoenixRunner
    except ImportError:
        return None, None

# CLI入口点（始终可用）
try:
    from .cli import main
except ImportError:
    def main():
        print("CLI功能不可用，请安装依赖：pip install click")

__all__ = [
    "__version__",
    "__author__", 
    "__description__",
    "main",
    "get_core_components"
]
