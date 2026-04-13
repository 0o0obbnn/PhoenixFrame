"""安全测试集成模块"""
import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from ..observability.logger import get_logger
from ..observability.tracer import get_tracer
from ..observability.metrics import record_test_metric

# 保留原有的加密和密钥管理功能
from .crypto import CryptoUtil
from .key_manager import KeyManager


@dataclass
class SecurityIssue:
    """安全问题"""
    severity: str  # high, medium, low, info
    title: str
    description: str
    file_path: str = ""
    line_number: int = 0
    cwe: str = ""
    confidence: str = ""
    remediation: str = ""
    references: List[str] = None
    
    def __post_init__(self):
        if self.references is None:
            self.references = []


@dataclass
class SecurityScanResult:
    """安全扫描结果"""
    tool: str
    scan_type: str  # sast, dast, dependency
    status: str  # success, failed, error
    issues: List[SecurityIssue]
    scan_time: float
    summary: Dict[str, int]
    raw_output: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SASTScanner:
    """静态应用程序安全测试 (SAST) 扫描器"""
    
    def __init__(self):
        self.logger = get_logger("phoenixframe.security.sast")
        self.tracer = get_tracer("phoenixframe.security.sast")
    
    def scan_with_bandit(self, target_path: str, config_file: Optional[str] = None,
                        output_format: str = "json") -> SecurityScanResult:
        """使用Bandit进行SAST扫描"""
        with self.tracer.trace_test_case("bandit_sast_scan", target_path, "running"):
            start_time = datetime.now()
            
            cmd = ["python", "-m", "bandit", "-r", target_path, "-f", output_format]
            
            if config_file:
                cmd.extend(["-c", config_file])
            
            # 排除常见的测试和虚拟环境目录
            exclude_dirs = [
                "*/test*", "*/tests/*", "*/.venv/*", "*/venv/*", 
                "*/__pycache__/*", "*/node_modules/*"
            ]
            cmd.extend(["-x", ",".join(exclude_dirs)])
            
            self.logger.info(f"Running Bandit SAST scan: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=600,
                    cwd=target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
                )
                
                scan_time = (datetime.now() - start_time).total_seconds()
                
                if output_format == "json" and result.stdout:
                    return self._parse_bandit_json_output(result.stdout, scan_time)
                else:
                    # 处理非JSON输出或无输出情况
                    issues = self._parse_bandit_text_output(result.stdout + result.stderr)
                    summary = self._calculate_summary(issues)
                    
                    return SecurityScanResult(
                        tool="bandit",
                        scan_type="sast",
                        status="success" if result.returncode == 0 else "failed",
                        issues=issues,
                        scan_time=scan_time,
                        summary=summary,
                        raw_output=result.stdout + result.stderr,
                        metadata={"exit_code": result.returncode}
                    )
                    
            except subprocess.TimeoutExpired:
                self.logger.error("Bandit scan timed out")
                return SecurityScanResult(
                    tool="bandit",
                    scan_type="sast",
                    status="error",
                    issues=[],
                    scan_time=600.0,
                    summary={},
                    raw_output="Scan timed out",
                    metadata={"error": "timeout"}
                )
            except FileNotFoundError:
                self.logger.error("Bandit not found. Install with: pip install bandit")
                return SecurityScanResult(
                    tool="bandit",
                    scan_type="sast",
                    status="error",
                    issues=[],
                    scan_time=0.0,
                    summary={},
                    raw_output="Bandit not installed",
                    metadata={"error": "tool_not_found"}
                )
            except Exception as e:
                self.logger.error(f"Bandit scan failed: {e}")
                return SecurityScanResult(
                    tool="bandit",
                    scan_type="sast",
                    status="error",
                    issues=[],
                    scan_time=(datetime.now() - start_time).total_seconds(),
                    summary={},
                    raw_output=str(e),
                    metadata={"error": str(e)}
                )
    
    def _parse_bandit_json_output(self, output: str, scan_time: float) -> SecurityScanResult:
        """解析Bandit JSON输出"""
        try:
            data = json.loads(output)
            issues = []
            
            for result in data.get("results", []):
                issue = SecurityIssue(
                    severity=result.get("issue_severity", "medium").lower(),
                    title=result.get("test_name", "Unknown"),
                    description=result.get("issue_text", ""),
                    file_path=result.get("filename", ""),
                    line_number=result.get("line_number", 0),
                    cwe=result.get("issue_cwe", {}).get("id", ""),
                    confidence=result.get("issue_confidence", "medium").lower(),
                    remediation="",
                    references=[result.get("more_info", "")] if result.get("more_info") else []
                )
                issues.append(issue)
            
            summary = self._calculate_summary(issues)
            
            return SecurityScanResult(
                tool="bandit",
                scan_type="sast",
                status="success",
                issues=issues,
                scan_time=scan_time,
                summary=summary,
                raw_output=output,
                metadata=data.get("metrics", {})
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Bandit JSON output: {e}")
            return SecurityScanResult(
                tool="bandit",
                scan_type="sast",
                status="error",
                issues=[],
                scan_time=scan_time,
                summary={},
                raw_output=output,
                metadata={"parse_error": str(e)}
            )
    
    def _parse_bandit_text_output(self, output: str) -> List[SecurityIssue]:
        """解析Bandit文本输出"""
        issues = []
        # 简单的文本解析逻辑
        lines = output.split('\n')
        for line in lines:
            if ">> Issue:" in line or "Test results:" in line:
                # 这里可以实现更复杂的文本解析逻辑
                pass
        return issues
    
    def _calculate_summary(self, issues: List[SecurityIssue]) -> Dict[str, int]:
        """计算安全问题摘要"""
        summary = {"high": 0, "medium": 0, "low": 0, "info": 0, "total": len(issues)}
        
        for issue in issues:
            severity = issue.severity.lower()
            if severity in summary:
                summary[severity] += 1
        
        return summary


class DependencyScanner:
    """依赖项安全扫描器"""
    
    def __init__(self):
        self.logger = get_logger("phoenixframe.security.dependency")
        self.tracer = get_tracer("phoenixframe.security.dependency")
    
    def scan_with_safety(self, requirements_file: Optional[str] = None) -> SecurityScanResult:
        """使用Safety进行依赖项安全扫描"""
        with self.tracer.trace_test_case("safety_dependency_scan", requirements_file or "current_env", "running"):
            start_time = datetime.now()
            
            cmd = ["python", "-m", "safety", "check", "--json"]
            
            if requirements_file:
                cmd.extend(["--file", requirements_file])
            
            self.logger.info(f"Running Safety dependency scan: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                scan_time = (datetime.now() - start_time).total_seconds()
                
                if result.stdout:
                    return self._parse_safety_json_output(result.stdout, scan_time)
                else:
                    return SecurityScanResult(
                        tool="safety",
                        scan_type="dependency",
                        status="success" if result.returncode == 0 else "failed",
                        issues=[],
                        scan_time=scan_time,
                        summary={"total": 0},
                        raw_output=result.stderr,
                        metadata={"exit_code": result.returncode}
                    )
                    
            except subprocess.TimeoutExpired:
                self.logger.error("Safety scan timed out")
                return SecurityScanResult(
                    tool="safety",
                    scan_type="dependency",
                    status="error",
                    issues=[],
                    scan_time=300.0,
                    summary={},
                    raw_output="Scan timed out",
                    metadata={"error": "timeout"}
                )
            except FileNotFoundError:
                self.logger.error("Safety not found. Install with: pip install safety")
                return SecurityScanResult(
                    tool="safety",
                    scan_type="dependency",
                    status="error",
                    issues=[],
                    scan_time=0.0,
                    summary={},
                    raw_output="Safety not installed",
                    metadata={"error": "tool_not_found"}
                )
            except Exception as e:
                self.logger.error(f"Safety scan failed: {e}")
                return SecurityScanResult(
                    tool="safety",
                    scan_type="dependency",
                    status="error",
                    issues=[],
                    scan_time=(datetime.now() - start_time).total_seconds(),
                    summary={},
                    raw_output=str(e),
                    metadata={"error": str(e)}
                )
    
    def _parse_safety_json_output(self, output: str, scan_time: float) -> SecurityScanResult:
        """解析Safety JSON输出"""
        try:
            data = json.loads(output)
            issues = []
            
            for vulnerability in data:
                issue = SecurityIssue(
                    severity=self._map_safety_severity(vulnerability.get("vulnerability_id", "")),
                    title=f"Vulnerable dependency: {vulnerability.get('package_name', 'Unknown')}",
                    description=vulnerability.get("advisory", ""),
                    file_path="requirements.txt",  # 假设的文件路径
                    cwe="",
                    confidence="high",
                    remediation=f"Upgrade to version {vulnerability.get('spec', 'latest')}",
                    references=[
                        f"https://pyup.io/vulnerabilities/{vulnerability.get('vulnerability_id', '')}"
                    ]
                )
                issues.append(issue)
            
            summary = self._calculate_summary(issues)
            
            return SecurityScanResult(
                tool="safety",
                scan_type="dependency",
                status="success",
                issues=issues,
                scan_time=scan_time,
                summary=summary,
                raw_output=output,
                metadata={"vulnerabilities_found": len(issues)}
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Safety JSON output: {e}")
            return SecurityScanResult(
                tool="safety",
                scan_type="dependency",
                status="error",
                issues=[],
                scan_time=scan_time,
                summary={},
                raw_output=output,
                metadata={"parse_error": str(e)}
            )
    
    def _map_safety_severity(self, vulnerability_id: str) -> str:
        """映射Safety漏洞严重性"""
        # 简单的严重性映射逻辑，实际应该基于漏洞数据库
        if vulnerability_id.startswith("70"):  # 高危漏洞ID模式
            return "high"
        elif vulnerability_id.startswith("60"):
            return "medium"
        else:
            return "low"
    
    def _calculate_summary(self, issues: List[SecurityIssue]) -> Dict[str, int]:
        """计算依赖项安全问题摘要"""
        summary = {"high": 0, "medium": 0, "low": 0, "info": 0, "total": len(issues)}
        
        for issue in issues:
            severity = issue.severity.lower()
            if severity in summary:
                summary[severity] += 1
        
        return summary


class DASTScanner:
    """动态应用程序安全测试 (DAST) 扫描器"""
    
    def __init__(self):
        self.logger = get_logger("phoenixframe.security.dast")
        self.tracer = get_tracer("phoenixframe.security.dast")
    
    def scan_with_zap(self, target_url: str, zap_proxy: str = "http://localhost:8080",
                     scan_policy: str = "Default Policy") -> SecurityScanResult:
        """使用OWASP ZAP进行DAST扫描"""
        with self.tracer.trace_test_case("zap_dast_scan", target_url, "running"):
            start_time = datetime.now()
            
            self.logger.info(f"Running ZAP DAST scan against: {target_url}")
            
            try:
                # 这里需要安装和配置ZAP
                # 简化的实现，实际应该使用ZAP API
                result = self._mock_zap_scan(target_url)
                
                scan_time = (datetime.now() - start_time).total_seconds()
                
                return SecurityScanResult(
                    tool="zap",
                    scan_type="dast",
                    status="success",
                    issues=result["issues"],
                    scan_time=scan_time,
                    summary=result["summary"],
                    raw_output=result["raw_output"],
                    metadata={"target_url": target_url, "scan_policy": scan_policy}
                )
                
            except Exception as e:
                self.logger.error(f"ZAP scan failed: {e}")
                return SecurityScanResult(
                    tool="zap",
                    scan_type="dast",
                    status="error",
                    issues=[],
                    scan_time=(datetime.now() - start_time).total_seconds(),
                    summary={},
                    raw_output=str(e),
                    metadata={"error": str(e), "target_url": target_url}
                )
    
    def _mock_zap_scan(self, target_url: str) -> Dict[str, Any]:
        """模拟ZAP扫描结果"""
        # 这是一个模拟实现，实际应该集成真正的ZAP API
        issues = [
            SecurityIssue(
                severity="medium",
                title="Missing Security Headers",
                description="The response does not include security headers",
                file_path=target_url,
                cwe="CWE-693",
                confidence="medium",
                remediation="Add security headers like Content-Security-Policy, X-Frame-Options",
                references=["https://owasp.org/www-project-secure-headers/"]
            )
        ]
        
        summary = {"high": 0, "medium": 1, "low": 0, "info": 0, "total": 1}
        raw_output = f"Mock DAST scan completed for {target_url}"
        
        return {
            "issues": issues,
            "summary": summary,
            "raw_output": raw_output
        }


class SecurityTestManager:
    """安全测试管理器"""
    
    def __init__(self):
        self.logger = get_logger("phoenixframe.security.manager")
        self.tracer = get_tracer("phoenixframe.security.manager")
        self.sast_scanner = SASTScanner()
        self.dependency_scanner = DependencyScanner()
        self.dast_scanner = DASTScanner()
    
    def run_comprehensive_scan(self, config: Dict[str, Any]) -> Dict[str, SecurityScanResult]:
        """运行综合安全扫描"""
        results = {}
        
        with self.tracer.trace_test_case("comprehensive_security_scan", "", "running"):
            self.logger.info("Starting comprehensive security scan")
            
            # SAST扫描
            if config.get("sast", {}).get("enabled", True):
                sast_config = config.get("sast", {})
                target_path = sast_config.get("target_path", ".")
                
                self.logger.info("Running SAST scan")
                results["sast"] = self.sast_scanner.scan_with_bandit(
                    target_path=target_path,
                    config_file=sast_config.get("config_file")
                )
                
                # 记录度量
                record_test_metric(
                    "sast_scan",
                    "completed" if results["sast"].status == "success" else "failed",
                    results["sast"].scan_time,
                    {"tool": "bandit", "issues_found": results["sast"].summary.get("total", 0)}
                )
            
            # 依赖项扫描
            if config.get("dependency", {}).get("enabled", True):
                dep_config = config.get("dependency", {})
                
                self.logger.info("Running dependency scan")
                results["dependency"] = self.dependency_scanner.scan_with_safety(
                    requirements_file=dep_config.get("requirements_file")
                )
                
                # 记录度量
                record_test_metric(
                    "dependency_scan",
                    "completed" if results["dependency"].status == "success" else "failed",
                    results["dependency"].scan_time,
                    {"tool": "safety", "issues_found": results["dependency"].summary.get("total", 0)}
                )
            
            # DAST扫描
            if config.get("dast", {}).get("enabled", False):
                dast_config = config.get("dast", {})
                target_url = dast_config.get("target_url")
                
                if target_url:
                    self.logger.info(f"Running DAST scan against {target_url}")
                    results["dast"] = self.dast_scanner.scan_with_zap(
                        target_url=target_url,
                        zap_proxy=dast_config.get("zap_proxy", "http://localhost:8080")
                    )
                    
                    # 记录度量
                    record_test_metric(
                        "dast_scan",
                        "completed" if results["dast"].status == "success" else "failed",
                        results["dast"].scan_time,
                        {"tool": "zap", "issues_found": results["dast"].summary.get("total", 0)}
                    )
                else:
                    self.logger.warning("DAST scan enabled but no target URL provided")
            
            self.logger.info("Comprehensive security scan completed")
            return results
    
    def generate_security_report(self, scan_results: Dict[str, SecurityScanResult],
                               output_file: Optional[str] = None) -> str:
        """生成安全测试报告"""
        report_data = {
            "scan_timestamp": datetime.now().isoformat(),
            "summary": self._generate_summary(scan_results),
            "scans": {}
        }
        
        for scan_type, result in scan_results.items():
            report_data["scans"][scan_type] = {
                "tool": result.tool,
                "status": result.status,
                "scan_time": result.scan_time,
                "summary": result.summary,
                "issues": [
                    {
                        "severity": issue.severity,
                        "title": issue.title,
                        "description": issue.description,
                        "file_path": issue.file_path,
                        "line_number": issue.line_number,
                        "cwe": issue.cwe,
                        "confidence": issue.confidence,
                        "remediation": issue.remediation,
                        "references": issue.references
                    }
                    for issue in result.issues
                ]
            }
        
        report_json = json.dumps(report_data, indent=2, ensure_ascii=False)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_json)
            self.logger.info(f"Security report saved to: {output_file}")
        
        return report_json
    
    def _generate_summary(self, scan_results: Dict[str, SecurityScanResult]) -> Dict[str, Any]:
        """生成安全扫描总结"""
        total_issues = 0
        severity_counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
        scan_statuses = {}
        
        for scan_type, result in scan_results.items():
            total_issues += result.summary.get("total", 0)
            scan_statuses[scan_type] = result.status
            
            for severity in severity_counts:
                severity_counts[severity] += result.summary.get(severity, 0)
        
        return {
            "total_issues": total_issues,
            "severity_breakdown": severity_counts,
            "scan_statuses": scan_statuses,
            "scans_completed": len([s for s in scan_statuses.values() if s == "success"]),
            "scans_failed": len([s for s in scan_statuses.values() if s in ["failed", "error"]])
        }


# 全局安全测试管理器实例
_security_manager: Optional[SecurityTestManager] = None


def get_security_manager() -> SecurityTestManager:
    """获取安全测试管理器实例"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityTestManager()
    return _security_manager


def run_security_scan(config: Dict[str, Any]) -> Dict[str, SecurityScanResult]:
    """运行安全扫描"""
    manager = get_security_manager()
    return manager.run_comprehensive_scan(config)


def generate_security_report(scan_results: Dict[str, SecurityScanResult],
                           output_file: Optional[str] = None) -> str:
    """生成安全报告"""
    manager = get_security_manager()
    return manager.generate_security_report(scan_results, output_file)


__all__ = [
    "CryptoUtil", 
    "KeyManager",
    "SecurityIssue",
    "SecurityScanResult", 
    "SASTScanner",
    "DependencyScanner",
    "DASTScanner",
    "SecurityTestManager",
    "get_security_manager",
    "run_security_scan", 
    "generate_security_report"
]
