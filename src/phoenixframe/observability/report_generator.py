"""报告生成器

提供多种格式的测试报告生成功能，包括：
- HTML格式报告（包含图表和交互功能）
- JSON格式报告（用于API集成）
- XML格式报告（兼容CI/CD工具）
- 报告模板管理
- 自定义报告样式
"""

import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import jinja2

from ..observability.logger import get_logger


@dataclass
class TestResult:
    """测试结果数据类"""
    name: str
    status: str  # "passed", "failed", "skipped", "error"
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0  # 秒
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    test_data: Dict[str, Any] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.end_time and self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()


@dataclass 
class TestSuite:
    """测试套件数据类"""
    name: str
    tests: List[TestResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    setup_duration: float = 0.0
    teardown_duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_tests(self) -> int:
        return len(self.tests)
    
    @property
    def passed_tests(self) -> int:
        return len([t for t in self.tests if t.status == "passed"])
    
    @property
    def failed_tests(self) -> int:
        return len([t for t in self.tests if t.status == "failed"])
    
    @property
    def skipped_tests(self) -> int:
        return len([t for t in self.tests if t.status == "skipped"])
    
    @property
    def error_tests(self) -> int:
        return len([t for t in self.tests if t.status == "error"])
    
    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100


@dataclass
class ReportSummary:
    """报告摘要数据类"""
    total_suites: int = 0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    total_duration: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    environment: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100


@dataclass
class TestReport:
    """完整测试报告数据类"""
    summary: ReportSummary
    suites: List[TestSuite] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    generator_version: str = "PhoenixFrame 3.3.0"


class ReportGenerator(ABC):
    """报告生成器抽象基类"""
    
    def __init__(self, output_dir: Union[str, Path] = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @abstractmethod
    def generate(self, report: TestReport, filename: Optional[str] = None) -> str:
        """
        生成报告
        
        Args:
            report: 测试报告数据
            filename: 输出文件名
            
        Returns:
            str: 生成的报告文件路径
        """
        pass
    
    def _get_filename(self, base_name: str, extension: str) -> str:
        """生成文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_name}_{timestamp}.{extension}"


class JSONReportGenerator(ReportGenerator):
    """JSON报告生成器"""
    
    def generate(self, report: TestReport, filename: Optional[str] = None) -> str:
        """生成JSON格式报告"""
        if not filename:
            filename = self._get_filename("test_report", "json")
        
        output_path = self.output_dir / filename
        
        try:
            # 转换为可序列化的字典
            report_dict = self._serialize_report(report)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"JSON report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to generate JSON report: {e}")
            raise
    
    def _serialize_report(self, report: TestReport) -> Dict[str, Any]:
        """序列化报告数据"""
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        report_dict = asdict(report)
        
        # 转换datetime对象
        def process_dict(d):
            if isinstance(d, dict):
                return {k: process_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [process_dict(item) for item in d]
            elif isinstance(d, datetime):
                return d.isoformat()
            else:
                return d
        
        return process_dict(report_dict)


class XMLReportGenerator(ReportGenerator):
    """XML报告生成器（JUnit格式兼容）"""
    
    def generate(self, report: TestReport, filename: Optional[str] = None) -> str:
        """生成XML格式报告"""
        if not filename:
            filename = self._get_filename("test_report", "xml")
        
        output_path = self.output_dir / filename
        
        try:
            root = self._create_xml_structure(report)
            
            # 格式化XML
            self._indent_xml(root)
            
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            self.logger.info(f"XML report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to generate XML report: {e}")
            raise
    
    def _create_xml_structure(self, report: TestReport) -> ET.Element:
        """创建XML结构"""
        root = ET.Element("testsuites")
        
        # 添加摘要属性
        summary = report.summary
        root.set("tests", str(summary.total_tests))
        root.set("failures", str(summary.failed_tests))
        root.set("errors", str(summary.error_tests))
        root.set("skipped", str(summary.skipped_tests))
        root.set("time", str(summary.total_duration))
        
        if summary.start_time:
            root.set("timestamp", summary.start_time.isoformat())
        
        # 添加测试套件
        for suite in report.suites:
            suite_elem = ET.SubElement(root, "testsuite")
            suite_elem.set("name", suite.name)
            suite_elem.set("tests", str(suite.total_tests))
            suite_elem.set("failures", str(suite.failed_tests))
            suite_elem.set("errors", str(suite.error_tests))
            suite_elem.set("skipped", str(suite.skipped_tests))
            suite_elem.set("time", str(suite.duration))
            
            if suite.start_time:
                suite_elem.set("timestamp", suite.start_time.isoformat())
            
            # 添加测试用例
            for test in suite.tests:
                test_elem = ET.SubElement(suite_elem, "testcase")
                test_elem.set("name", test.name)
                test_elem.set("time", str(test.duration))
                
                if test.status == "failed":
                    failure_elem = ET.SubElement(test_elem, "failure")
                    failure_elem.set("message", test.error_message or "Test failed")
                    if test.error_traceback:
                        failure_elem.text = test.error_traceback
                
                elif test.status == "error":
                    error_elem = ET.SubElement(test_elem, "error")
                    error_elem.set("message", test.error_message or "Test error")
                    if test.error_traceback:
                        error_elem.text = test.error_traceback
                
                elif test.status == "skipped":
                    skipped_elem = ET.SubElement(test_elem, "skipped")
                    skipped_elem.set("message", "Test skipped")
                
                # 添加系统输出
                if test.logs:
                    stdout_elem = ET.SubElement(test_elem, "system-out")
                    stdout_elem.text = "\n".join(test.logs)
        
        return root
    
    def _indent_xml(self, elem, level=0):
        """格式化XML缩进"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i


class HTMLReportGenerator(ReportGenerator):
    """HTML报告生成器"""
    
    def __init__(self, output_dir: Union[str, Path] = "reports", template_dir: Optional[str] = None):
        super().__init__(output_dir)
        self.template_dir = Path(template_dir) if template_dir else Path(__file__).parent / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化Jinja2环境
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # 创建默认模板
        self._create_default_templates()
    
    def generate(self, report: TestReport, filename: Optional[str] = None) -> str:
        """生成HTML格式报告"""
        if not filename:
            filename = self._get_filename("test_report", "html")
        
        output_path = self.output_dir / filename
        
        try:
            # 加载模板
            template = self.jinja_env.get_template("report.html")
            
            # 准备模板数据
            template_data = self._prepare_template_data(report)
            
            # 渲染HTML
            html_content = template.render(**template_data)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 复制静态资源
            self._copy_static_resources()
            
            self.logger.info(f"HTML report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            raise
    
    def _prepare_template_data(self, report: TestReport) -> Dict[str, Any]:
        """准备模板数据"""
        return {
            'report': report,
            'summary': report.summary,
            'suites': report.suites,
            'generated_at': report.generated_at,
            'generator_version': report.generator_version,
            'charts_data': self._prepare_charts_data(report),
            'metadata': report.metadata
        }
    
    def _prepare_charts_data(self, report: TestReport) -> Dict[str, Any]:
        """准备图表数据"""
        summary = report.summary
        
        # 饼图数据（测试结果分布）
        pie_data = {
            'labels': ['Passed', 'Failed', 'Skipped', 'Error'],
            'data': [summary.passed_tests, summary.failed_tests, 
                    summary.skipped_tests, summary.error_tests],
            'colors': ['#28a745', '#dc3545', '#6c757d', '#fd7e14']
        }
        
        # 柱状图数据（各套件测试结果）
        bar_data = {
            'labels': [suite.name for suite in report.suites],
            'datasets': [
                {
                    'label': 'Passed',
                    'data': [suite.passed_tests for suite in report.suites],
                    'backgroundColor': '#28a745'
                },
                {
                    'label': 'Failed',
                    'data': [suite.failed_tests for suite in report.suites],
                    'backgroundColor': '#dc3545'
                },
                {
                    'label': 'Skipped',
                    'data': [suite.skipped_tests for suite in report.suites],
                    'backgroundColor': '#6c757d'
                }
            ]
        }
        
        # 时间线数据
        timeline_data = []
        for suite in report.suites:
            for test in suite.tests:
                if test.start_time:
                    timeline_data.append({
                        'name': f"{suite.name}.{test.name}",
                        'start': test.start_time.isoformat(),
                        'end': test.end_time.isoformat() if test.end_time else test.start_time.isoformat(),
                        'status': test.status,
                        'duration': test.duration
                    })
        
        return {
            'pie': pie_data,
            'bar': bar_data,
            'timeline': timeline_data
        }
    
    def _create_default_templates(self):
        """创建默认HTML模板"""
        template_path = self.template_dir / "report.html"
        
        if not template_path.exists():
            html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhoenixFrame 测试报告</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .status-passed { color: #28a745; }
        .status-failed { color: #dc3545; }
        .status-skipped { color: #6c757d; }
        .status-error { color: #fd7e14; }
        .test-details { display: none; }
        .test-row.active .test-details { display: table-row; }
        .chart-container { position: relative; height: 400px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <header class="bg-primary text-white p-3 mb-4">
            <h1>PhoenixFrame 测试报告</h1>
            <p class="mb-0">生成时间: {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }} | 版本: {{ generator_version }}</p>
        </header>

        <!-- 摘要卡片 -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card border-primary">
                    <div class="card-body text-center">
                        <h3 class="card-title text-primary">{{ summary.total_tests }}</h3>
                        <p class="card-text">总测试数</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card border-success">
                    <div class="card-body text-center">
                        <h3 class="card-title text-success">{{ summary.passed_tests }}</h3>
                        <p class="card-text">通过</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card border-danger">
                    <div class="card-body text-center">
                        <h3 class="card-title text-danger">{{ summary.failed_tests }}</h3>
                        <p class="card-text">失败</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card border-warning">
                    <div class="card-body text-center">
                        <h3 class="card-title text-warning">{{ "%.1f"|format(summary.success_rate) }}%</h3>
                        <p class="card-text">成功率</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- 图表区域 -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>测试结果分布</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="pieChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>各套件测试结果</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="barChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 测试套件详情 -->
        {% for suite in suites %}
        <div class="card mb-3">
            <div class="card-header">
                <h5>{{ suite.name }}</h5>
                <small class="text-muted">
                    总计: {{ suite.total_tests }} | 
                    通过: <span class="status-passed">{{ suite.passed_tests }}</span> | 
                    失败: <span class="status-failed">{{ suite.failed_tests }}</span> | 
                    跳过: <span class="status-skipped">{{ suite.skipped_tests }}</span> |
                    耗时: {{ "%.2f"|format(suite.duration) }}s
                </small>
            </div>
            <div class="card-body">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>测试名称</th>
                            <th>状态</th>
                            <th>耗时</th>
                            <th>开始时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for test in suite.tests %}
                        <tr class="test-row" onclick="toggleDetails(this)">
                            <td>{{ test.name }}</td>
                            <td><span class="status-{{ test.status }}">{{ test.status.upper() }}</span></td>
                            <td>{{ "%.3f"|format(test.duration) }}s</td>
                            <td>{{ test.start_time.strftime('%H:%M:%S') if test.start_time else '-' }}</td>
                        </tr>
                        {% if test.error_message or test.screenshots or test.logs %}
                        <tr class="test-details">
                            <td colspan="4">
                                <div class="alert alert-info">
                                    {% if test.error_message %}
                                    <h6>错误信息:</h6>
                                    <pre>{{ test.error_message }}</pre>
                                    {% endif %}
                                    {% if test.error_traceback %}
                                    <h6>堆栈跟踪:</h6>
                                    <pre class="small">{{ test.error_traceback }}</pre>
                                    {% endif %}
                                    {% if test.screenshots %}
                                    <h6>截图:</h6>
                                    {% for screenshot in test.screenshots %}
                                    <img src="{{ screenshot }}" class="img-thumbnail" style="max-width: 200px;" alt="Screenshot">
                                    {% endfor %}
                                    {% endif %}
                                    {% if test.logs %}
                                    <h6>日志:</h6>
                                    <pre class="small">{{ test.logs | join('\n') }}</pre>
                                    {% endif %}
                                </div>
                            </td>
                        </tr>
                        {% endif %}
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endfor %}
    </div>

    <script>
        // 饼图
        const pieCtx = document.getElementById('pieChart').getContext('2d');
        new Chart(pieCtx, {
            type: 'pie',
            data: {
                labels: {{ charts_data.pie.labels | tojson }},
                datasets: [{
                    data: {{ charts_data.pie.data | tojson }},
                    backgroundColor: {{ charts_data.pie.colors | tojson }}
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });

        // 柱状图
        const barCtx = document.getElementById('barChart').getContext('2d');
        new Chart(barCtx, {
            type: 'bar',
            data: {{ charts_data.bar | tojson }},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true },
                    y: { stacked: true }
                }
            }
        });

        // 切换测试详情
        function toggleDetails(row) {
            row.classList.toggle('active');
        }
    </script>
</body>
</html>'''
            
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
    
    def _copy_static_resources(self):
        """复制静态资源文件"""
        # 这里可以添加CSS、JS等静态资源的复制逻辑
        pass


class ReportManager:
    """报告管理器"""
    
    def __init__(self, output_dir: Union[str, Path] = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # 初始化生成器
        self.generators = {
            'json': JSONReportGenerator(output_dir),
            'xml': XMLReportGenerator(output_dir),
            'html': HTMLReportGenerator(output_dir)
        }
    
    def generate_report(self, 
                       report: TestReport, 
                       formats: List[str] = None,
                       filename_base: Optional[str] = None) -> Dict[str, str]:
        """
        生成多种格式的报告
        
        Args:
            report: 测试报告数据
            formats: 要生成的格式列表，默认为['html', 'json']
            filename_base: 文件名基础部分
            
        Returns:
            Dict[str, str]: 格式到文件路径的映射
        """
        if formats is None:
            formats = ['html', 'json']
        
        results = {}
        
        for format_name in formats:
            if format_name not in self.generators:
                self.logger.warning(f"Unsupported format: {format_name}")
                continue
            
            try:
                generator = self.generators[format_name]
                filename = f"{filename_base}.{format_name}" if filename_base else None
                file_path = generator.generate(report, filename)
                results[format_name] = file_path
                
            except Exception as e:
                self.logger.error(f"Failed to generate {format_name} report: {e}")
        
        return results
    
    def add_generator(self, name: str, generator: ReportGenerator):
        """添加自定义报告生成器"""
        self.generators[name] = generator
    
    def create_report_from_data(self, 
                               test_data: List[Dict[str, Any]],
                               suite_name: str = "Default Suite") -> TestReport:
        """
        从测试数据创建报告
        
        Args:
            test_data: 测试数据列表
            suite_name: 测试套件名称
            
        Returns:
            TestReport: 创建的测试报告
        """
        tests = []
        for data in test_data:
            test = TestResult(
                name=data.get('name', 'Unknown Test'),
                status=data.get('status', 'unknown'),
                start_time=data.get('start_time', datetime.now()),
                end_time=data.get('end_time'),
                error_message=data.get('error_message'),
                error_traceback=data.get('error_traceback'),
                test_data=data.get('test_data', {}),
                screenshots=data.get('screenshots', []),
                logs=data.get('logs', []),
                metadata=data.get('metadata', {})
            )
            tests.append(test)
        
        suite = TestSuite(name=suite_name, tests=tests)
        
        # 计算摘要
        summary = ReportSummary(
            total_suites=1,
            total_tests=suite.total_tests,
            passed_tests=suite.passed_tests,
            failed_tests=suite.failed_tests,
            skipped_tests=suite.skipped_tests,
            error_tests=suite.error_tests,
            total_duration=suite.duration,
            start_time=min((t.start_time for t in tests if t.start_time), default=datetime.now()),
            end_time=max((t.end_time for t in tests if t.end_time), default=datetime.now())
        )
        
        return TestReport(summary=summary, suites=[suite])


# 便捷函数
def generate_html_report(report: TestReport, output_path: Optional[str] = None) -> str:
    """生成HTML报告的便捷函数"""
    generator = HTMLReportGenerator()
    return generator.generate(report, output_path)


def generate_json_report(report: TestReport, output_path: Optional[str] = None) -> str:
    """生成JSON报告的便捷函数"""
    generator = JSONReportGenerator()
    return generator.generate(report, output_path)


def generate_xml_report(report: TestReport, output_path: Optional[str] = None) -> str:
    """生成XML报告的便捷函数"""
    generator = XMLReportGenerator()
    return generator.generate(report, output_path)