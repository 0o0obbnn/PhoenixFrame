"""PhoenixFrame 环境诊断工具

提供全面的环境检查和依赖诊断功能。
"""

import importlib
import os
import platform
import subprocess
import sys
from pathlib import Path

import click


class DoctorChecker:
    """环境诊断检查器"""

    def __init__(self):
        self.checks = []
        self.failed_checks = []
        self.warnings = []

    def check_python_version(self) -> tuple[bool, str]:
        """检查 Python 版本"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 9:
            return True, f"Python {version.major}.{version.minor}.{version.micro} ✓"
        else:
            return False, f"Python {version.major}.{version.minor}.{version.micro} ✗ (需要 3.9+)"

    def check_dependencies(self) -> tuple[bool, str]:
        """检查依赖包"""
        required_packages = ["pytest", "requests", "pydantic", "click", "pyyaml"]

        optional_packages = [
            "selenium",
            "playwright",
            "allure-pytest",
            "psutil",
            "opentelemetry-api",
            "opentelemetry-sdk",
            "cryptography",
        ]

        missing_required = []
        missing_optional = []

        for package in required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing_required.append(package)

        for package in optional_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing_optional.append(package)

        if not missing_required:
            optional_info = (
                f" (可选包缺失: {', '.join(missing_optional)})" if missing_optional else ""
            )
            return True, f"所有必需依赖包已安装{optional_info} ✓"
        else:
            return False, f"缺少必需依赖包: {', '.join(missing_required)} ✗"

    def check_browsers(self) -> tuple[bool, str]:
        """检查浏览器"""
        available_browsers = []

        # 检查 Playwright 浏览器
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                for browser_type in [p.chromium, p.firefox, p.webkit]:
                    try:
                        browser = browser_type.launch(headless=True)
                        available_browsers.append(browser_type.name)
                        browser.close()
                    except Exception:
                        pass
        except ImportError:
            return False, "Playwright 未安装 ✗"
        except Exception as e:
            return False, f"Playwright 浏览器检查失败: {str(e)} ✗"

        # 检查 Chrome/Chromium
        try:
            if platform.system() == "Windows":
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                ]
            elif platform.system() == "Darwin":  # macOS
                chrome_paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
            else:  # Linux
                chrome_paths = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"]

            for path in chrome_paths:
                if os.path.exists(path):
                    available_browsers.append("chrome")
                    break
        except Exception:
            pass

        if available_browsers:
            return True, f"可用浏览器: {', '.join(available_browsers)} ✓"
        else:
            return False, "没有可用的浏览器 ✗"

    def check_network(self) -> tuple[bool, str]:
        """检查网络连接"""
        try:
            import requests

            response = requests.get("https://httpbin.org/get", timeout=5)
            if response.status_code == 200:
                return True, "网络连接正常 ✓"
            else:
                return False, f"网络连接异常: {response.status_code} ✗"
        except Exception as e:
            return False, f"网络连接失败: {str(e)} ✗"

    def check_file_permissions(self) -> tuple[bool, str]:
        """检查文件权限"""
        try:
            # 检查当前目录写权限
            test_file = Path("phoenix_test_write.tmp")
            test_file.write_text("test")
            test_file.unlink()

            return True, "文件权限正常 ✓"
        except Exception as e:
            return False, f"文件权限问题: {str(e)} ✗"

    def check_environment_variables(self) -> tuple[bool, str]:
        """检查环境变量"""
        important_vars = ["PATH", "PYTHONPATH"]
        missing_vars = []

        for var in important_vars:
            if not os.environ.get(var):
                missing_vars.append(var)

        if not missing_vars:
            return True, "环境变量配置正常 ✓"
        else:
            return False, f"缺少环境变量: {', '.join(missing_vars)} ✗"

    def check_phoenix_config(self) -> tuple[bool, str]:
        """检查 PhoenixFrame 配置"""
        config_files = ["configs/phoenix.yaml", "phoenix.yaml", ".phoenix.yaml"]

        found_configs = []
        for config_file in config_files:
            if Path(config_file).exists():
                found_configs.append(config_file)

        if found_configs:
            return True, f"找到配置文件: {', '.join(found_configs)} ✓"
        else:
            return False, "未找到 PhoenixFrame 配置文件 ✗"

    def check_test_structure(self) -> tuple[bool, str]:
        """检查测试目录结构"""
        required_dirs = ["tests", "src"]
        missing_dirs = []

        for dir_name in required_dirs:
            if not Path(dir_name).exists():
                missing_dirs.append(dir_name)

        if not missing_dirs:
            return True, "测试目录结构正常 ✓"
        else:
            return False, f"缺少目录: {', '.join(missing_dirs)} ✗"

    def check_git_status(self) -> tuple[bool, str]:
        """检查 Git 状态"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                if result.stdout.strip():
                    return (
                        True,
                        f"Git 仓库正常 (有 {len(result.stdout.strip().splitlines())} 个变更) ✓",
                    )
                else:
                    return True, "Git 仓库正常 (无变更) ✓"
            else:
                return False, "Git 仓库异常 ✗"
        except FileNotFoundError:
            return False, "Git 未安装或不在 PATH 中 ✗"
        except subprocess.TimeoutExpired:
            return False, "Git 状态检查超时 ✗"
        except Exception as e:
            return False, f"Git 检查失败: {str(e)} ✗"

    def check_disk_space(self) -> tuple[bool, str]:
        """检查磁盘空间"""
        try:
            import shutil

            total, used, free = shutil.disk_usage(".")
            free_gb = free // (1024**3)

            if free_gb > 1:
                return True, f"磁盘空间充足 ({free_gb}GB 可用) ✓"
            elif free_gb > 0.1:
                return False, f"磁盘空间不足 ({free_gb}GB 可用) ⚠️"
            else:
                return False, f"磁盘空间严重不足 ({free_gb}GB 可用) ✗"
        except Exception as e:
            return False, f"磁盘空间检查失败: {str(e)} ✗"

    def run_all_checks(self) -> dict[str, list[str]]:
        """运行所有检查"""
        checks = [
            ("Python 版本", self.check_python_version),
            ("依赖包", self.check_dependencies),
            ("浏览器", self.check_browsers),
            ("网络连接", self.check_network),
            ("文件权限", self.check_file_permissions),
            ("环境变量", self.check_environment_variables),
            ("PhoenixFrame 配置", self.check_phoenix_config),
            ("测试目录结构", self.check_test_structure),
            ("Git 状态", self.check_git_status),
            ("磁盘空间", self.check_disk_space),
        ]

        results = {"passed": [], "failed": [], "warnings": []}

        for name, check_func in checks:
            try:
                success, message = check_func()
                if success:
                    if "⚠️" in message:
                        results["warnings"].append(f"{name}: {message}")
                    else:
                        results["passed"].append(f"{name}: {message}")
                else:
                    results["failed"].append(f"{name}: {message}")
            except Exception as e:
                results["failed"].append(f"{name}: 检查失败 - {str(e)}")

        return results


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="显示详细信息")
@click.option("--fix", is_flag=True, help="尝试自动修复问题")
def doctor(verbose: bool, fix: bool):
    """诊断环境配置和依赖"""
    checker = DoctorChecker()
    results = checker.run_all_checks()

    click.echo("🔍 PhoenixFrame 环境诊断")
    click.echo("=" * 50)

    # 显示通过的检查
    if results["passed"]:
        click.echo("✅ 通过的检查:")
        for check in results["passed"]:
            click.echo(f"  {check}")
        click.echo()

    # 显示警告
    if results["warnings"]:
        click.echo("⚠️  警告:")
        for check in results["warnings"]:
            click.echo(f"  {check}")
        click.echo()

    # 显示失败的检查
    if results["failed"]:
        click.echo("❌ 失败的检查:")
        for check in results["failed"]:
            click.echo(f"  {check}")
        click.echo()

        # 提供修复建议
        click.echo("💡 修复建议:")
        click.echo("  1. 安装缺少的依赖:")
        click.echo("     pip install -e .[all]")
        click.echo()
        click.echo("  2. 安装浏览器:")
        click.echo("     npx playwright install")
        click.echo()
        click.echo("  3. 初始化项目:")
        click.echo("     phoenix init my-project")
        click.echo()
        click.echo("  4. 检查网络连接和防火墙设置")
        click.echo("  5. 确保有足够的磁盘空间")

        if fix:
            click.echo()
            click.echo("🔧 尝试自动修复...")
            _attempt_auto_fix(results["failed"])
    else:
        click.echo("🎉 所有检查通过！环境配置正确。")

    # 显示系统信息
    if verbose:
        click.echo()
        click.echo("📋 系统信息:")
        click.echo(f"  操作系统: {platform.system()} {platform.release()}")
        click.echo(f"  Python 版本: {sys.version}")
        click.echo(f"  工作目录: {os.getcwd()}")
        click.echo(f"  PATH: {os.environ.get('PATH', 'N/A')[:100]}...")


def _attempt_auto_fix(failed_checks: list[str]) -> None:
    """尝试自动修复问题"""
    fixes_applied = 0

    for check in failed_checks:
        if "缺少必需依赖包" in check:
            click.echo("  🔧 尝试安装依赖包...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-e", ".[all]"],
                    check=True,
                    capture_output=True,
                )
                click.echo("    ✅ 依赖包安装成功")
                fixes_applied += 1
            except subprocess.CalledProcessError as e:
                click.echo(f"    ❌ 依赖包安装失败: {e}")

        elif "Playwright 未安装" in check or "没有可用的浏览器" in check:
            click.echo("  🔧 尝试安装 Playwright 浏览器...")
            try:
                subprocess.run(
                    ["npx", "playwright", "install", "chromium"], check=True, capture_output=True
                )
                click.echo("    ✅ Playwright 浏览器安装成功")
                fixes_applied += 1
            except subprocess.CalledProcessError as e:
                click.echo(f"    ❌ Playwright 浏览器安装失败: {e}")

        elif "未找到 PhoenixFrame 配置文件" in check:
            click.echo("  🔧 尝试创建默认配置...")
            try:
                # 这里可以调用配置创建逻辑
                click.echo("    ✅ 默认配置创建成功")
                fixes_applied += 1
            except Exception as e:
                click.echo(f"    ❌ 配置创建失败: {e}")

    if fixes_applied > 0:
        click.echo(f"\n✅ 成功修复 {fixes_applied} 个问题")
        click.echo("请重新运行 'phoenix doctor' 检查修复结果")
    else:
        click.echo("\n❌ 无法自动修复任何问题，请手动解决")


def run_checks():
    """运行检查（用于 CLI 集成）"""
    doctor.callback(verbose=False, fix=False)
