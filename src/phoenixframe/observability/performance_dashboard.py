"""性能仪表板生成器

提供实时性能监控仪表板，包括：
- 实时性能指标展示
- 交互式图表和可视化
- 告警状态监控
- 性能趋势分析
- 导出和共享功能
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics

from .performance_monitor import get_performance_analyzer, get_performance_profiler
from .metrics import get_metrics_collector
from ..observability.logger import get_logger


class PerformanceDashboard:
    """性能仪表板生成器"""
    
    def __init__(self, output_dir: str = "dashboard"):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.analyzer = get_performance_analyzer()
        self.profiler = get_performance_profiler()
        self.metrics_collector = get_metrics_collector()
    
    def generate_dashboard(self, auto_refresh: bool = True) -> str:
        """生成性能仪表板HTML文件"""
        dashboard_data = self._collect_dashboard_data()
        html_content = self._generate_html(dashboard_data, auto_refresh)
        
        dashboard_path = self.output_dir / "performance_dashboard.html"
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 生成数据API端点
        self._generate_data_api(dashboard_data)
        
        self.logger.info(f"Performance dashboard generated: {dashboard_path}")
        return str(dashboard_path)
    
    def _collect_dashboard_data(self) -> Dict[str, Any]:
        """收集仪表板数据"""
        # 性能摘要
        performance_summary = self.analyzer.get_performance_summary()
        
        # 性能分析数据
        profile_summary = self.profiler.get_profile_summary()
        
        # 指标摘要
        metrics_summary = self.metrics_collector.get_summary()
        
        # 准备图表数据
        charts_data = self._prepare_charts_data()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "performance_summary": performance_summary,
            "profile_summary": profile_summary,
            "metrics_summary": metrics_summary,
            "charts_data": charts_data
        }
    
    def _prepare_charts_data(self) -> Dict[str, Any]:
        """准备图表数据"""
        snapshots = list(self.analyzer.snapshots)
        
        if not snapshots:
            return {
                "system_metrics": {"timestamps": [], "cpu": [], "memory": [], "disk": []},
                "test_metrics": {"timestamps": [], "pass_rate": [], "duration": []},
                "alerts": []
            }
        
        # 系统指标时间序列
        timestamps = [s.timestamp.strftime("%H:%M:%S") for s in snapshots[-60:]]  # 最近60个点
        cpu_data = [s.cpu_percent for s in snapshots[-60:]]
        memory_data = [s.memory_percent for s in snapshots[-60:]]
        disk_data = [s.disk_usage_percent for s in snapshots[-60:]]
        
        # 测试指标时间序列
        test_timestamps = []
        test_pass_rates = []
        test_durations = []
        
        for snapshot in snapshots[-60:]:
            if 'test_pass_rate' in snapshot.custom_metrics:
                test_timestamps.append(snapshot.timestamp.strftime("%H:%M:%S"))
                test_pass_rates.append(snapshot.custom_metrics['test_pass_rate'])
                test_durations.append(snapshot.custom_metrics.get('avg_test_duration', 0))
        
        # 告警数据
        alerts_data = []
        for alert in list(self.analyzer.alerts)[-10:]:  # 最近10个告警
            alerts_data.append({
                "timestamp": alert.timestamp.strftime("%H:%M:%S"),
                "severity": alert.severity,
                "category": alert.category,
                "message": alert.message,
                "value": alert.current_value
            })
        
        # 性能分布数据
        if snapshots:
            cpu_distribution = self._calculate_distribution([s.cpu_percent for s in snapshots])
            memory_distribution = self._calculate_distribution([s.memory_percent for s in snapshots])
        else:
            cpu_distribution = memory_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        return {
            "system_metrics": {
                "timestamps": timestamps,
                "cpu": cpu_data,
                "memory": memory_data,
                "disk": disk_data
            },
            "test_metrics": {
                "timestamps": test_timestamps,
                "pass_rate": test_pass_rates,
                "duration": test_durations
            },
            "alerts": alerts_data,
            "distributions": {
                "cpu": cpu_distribution,
                "memory": memory_distribution
            }
        }
    
    def _calculate_distribution(self, values: List[float]) -> Dict[str, int]:
        """计算数值分布"""
        if not values:
            return {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        return {
            "low": len([v for v in values if v <= 25]),
            "medium": len([v for v in values if 25 < v <= 50]),
            "high": len([v for v in values if 50 < v <= 75]),
            "critical": len([v for v in values if v > 75])
        }
    
    def _generate_html(self, dashboard_data: Dict[str, Any], auto_refresh: bool) -> str:
        """生成仪表板HTML"""
        refresh_script = '''
        <script>
        // 自动刷新
        setInterval(function() {
            location.reload();
        }, 30000); // 30秒刷新一次
        </script>
        ''' if auto_refresh else ''
        
        html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhoenixFrame 性能监控仪表板</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .metric-card {{
            transition: all 0.3s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .alert-item {{
            border-left: 4px solid;
            margin-bottom: 10px;
            padding: 10px 15px;
        }}
        .alert-critical {{ border-left-color: #dc3545; }}
        .alert-high {{ border-left-color: #fd7e14; }}
        .alert-medium {{ border-left-color: #ffc107; }}
        .alert-low {{ border-left-color: #6c757d; }}
        .status-good {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-danger {{ color: #dc3545; }}
        .chart-container {{ position: relative; height: 300px; }}
        .last-updated {{ font-size: 0.8em; color: #6c757d; }}
    </style>
    {refresh_script}
</head>
<body class="bg-light">
    <div class="container-fluid">
        <!-- 头部 -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="bg-white p-3 rounded shadow-sm">
                    <h1 class="mb-0">PhoenixFrame 性能监控仪表板</h1>
                    <div class="last-updated">最后更新: {dashboard_data["timestamp"]}</div>
                </div>
            </div>
        </div>

        <!-- 系统状态卡片 -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <h4 class="card-title">CPU 使用率</h4>
                        <h2 class="{'status-danger' if dashboard_data['performance_summary']['current_status']['cpu_percent'] > 80 else 'status-warning' if dashboard_data['performance_summary']['current_status']['cpu_percent'] > 60 else 'status-good'}">
                            {dashboard_data['performance_summary']['current_status']['cpu_percent']:.1f}%
                        </h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <h4 class="card-title">内存使用率</h4>
                        <h2 class="{'status-danger' if dashboard_data['performance_summary']['current_status']['memory_percent'] > 85 else 'status-warning' if dashboard_data['performance_summary']['current_status']['memory_percent'] > 70 else 'status-good'}">
                            {dashboard_data['performance_summary']['current_status']['memory_percent']:.1f}%
                        </h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <h4 class="card-title">磁盘使用率</h4>
                        <h2 class="{'status-danger' if dashboard_data['performance_summary']['current_status']['disk_usage_percent'] > 90 else 'status-warning' if dashboard_data['performance_summary']['current_status']['disk_usage_percent'] > 80 else 'status-good'}">
                            {dashboard_data['performance_summary']['current_status']['disk_usage_percent']:.1f}%
                        </h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <h4 class="card-title">活跃线程</h4>
                        <h2 class="status-good">
                            {dashboard_data['performance_summary']['current_status']['thread_count']}
                        </h2>
                    </div>
                </div>
            </div>
        </div>

        <!-- 图表区域 -->
        <div class="row mb-4">
            <!-- 系统性能趋势 -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>系统性能趋势</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="systemChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 测试性能趋势 -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>测试性能趋势</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="testChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 性能分布和告警 -->
        <div class="row mb-4">
            <!-- CPU/内存分布 -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>性能分布</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6">
                                <h6>CPU 分布</h6>
                                <div class="chart-container" style="height: 200px;">
                                    <canvas id="cpuDistChart"></canvas>
                                </div>
                            </div>
                            <div class="col-6">
                                <h6>内存分布</h6>
                                <div class="chart-container" style="height: 200px;">
                                    <canvas id="memoryDistChart"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 告警列表 -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>最近告警</h5>
                    </div>
                    <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                        {self._generate_alerts_html(dashboard_data['charts_data']['alerts'])}
                    </div>
                </div>
            </div>
        </div>

        <!-- 详细统计 -->
        <div class="row mb-4">
            <!-- 内存分析 -->
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5>内存分析</h5>
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <strong>当前使用:</strong> {dashboard_data['performance_summary']['memory_profile']['current_usage_mb']:.1f} MB
                        </div>
                        <div class="mb-2">
                            <strong>峰值使用:</strong> {dashboard_data['performance_summary']['memory_profile']['peak_usage_mb']:.1f} MB
                        </div>
                        <div class="mb-2">
                            <strong>增长率:</strong> {dashboard_data['performance_summary']['memory_profile']['growth_rate_mb_per_min']:.2f} MB/min
                        </div>
                        <div>
                            <strong>潜在泄漏:</strong>
                            <ul class="mb-0">
                                {' '.join([f'<li>{leak}</li>' for leak in dashboard_data['performance_summary']['memory_profile']['potential_leaks']]) or '<li>无</li>'}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- CPU分析 -->
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5>CPU分析</h5>
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <strong>平均使用:</strong> {dashboard_data['performance_summary']['cpu_profile']['avg_usage_percent']:.1f}%
                        </div>
                        <div class="mb-2">
                            <strong>峰值使用:</strong> {dashboard_data['performance_summary']['cpu_profile']['peak_usage_percent']:.1f}%
                        </div>
                        <div>
                            <strong>瓶颈指标:</strong>
                            <ul class="mb-0">
                                {' '.join([f'<li>{indicator}</li>' for indicator in dashboard_data['performance_summary']['cpu_profile']['bottleneck_indicators']]) or '<li>无</li>'}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 性能回归 -->
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5>性能回归检测</h5>
                    </div>
                    <div class="card-body">
                        <ul class="mb-0">
                            {' '.join([f'<li class="text-warning">{regression}</li>' for regression in dashboard_data['performance_summary']['performance_regressions']]) or '<li class="text-success">无回归检测到</li>'}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 图表配置
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;

        // 系统性能趋势图
        const systemCtx = document.getElementById('systemChart').getContext('2d');
        new Chart(systemCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(dashboard_data['charts_data']['system_metrics']['timestamps'])},
                datasets: [{{
                    label: 'CPU %',
                    data: {json.dumps(dashboard_data['charts_data']['system_metrics']['cpu'])},
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    tension: 0.1
                }}, {{
                    label: 'Memory %',
                    data: {json.dumps(dashboard_data['charts_data']['system_metrics']['memory'])},
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    tension: 0.1
                }}, {{
                    label: 'Disk %',
                    data: {json.dumps(dashboard_data['charts_data']['system_metrics']['disk'])},
                    borderColor: 'rgb(255, 206, 86)',
                    backgroundColor: 'rgba(255, 206, 86, 0.1)',
                    tension: 0.1
                }}]
            }},
            options: {{
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});

        // 测试性能趋势图
        const testCtx = document.getElementById('testChart').getContext('2d');
        new Chart(testCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(dashboard_data['charts_data']['test_metrics']['timestamps'])},
                datasets: [{{
                    label: 'Pass Rate %',
                    data: {json.dumps(dashboard_data['charts_data']['test_metrics']['pass_rate'])},
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    yAxisID: 'y',
                    tension: 0.1
                }}, {{
                    label: 'Avg Duration (s)',
                    data: {json.dumps(dashboard_data['charts_data']['test_metrics']['duration'])},
                    borderColor: 'rgb(153, 102, 255)',
                    backgroundColor: 'rgba(153, 102, 255, 0.1)',
                    yAxisID: 'y1',
                    tension: 0.1
                }}]
            }},
            options: {{
                interaction: {{
                    mode: 'index',
                    intersect: false,
                }},
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        max: 100,
                        title: {{
                            display: true,
                            text: 'Pass Rate %'
                        }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Duration (s)'
                        }},
                        grid: {{
                            drawOnChartArea: false,
                        }},
                    }}
                }}
            }}
        }});

        // CPU分布图
        const cpuDistCtx = document.getElementById('cpuDistChart').getContext('2d');
        new Chart(cpuDistCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Low (0-25%)', 'Medium (25-50%)', 'High (50-75%)', 'Critical (75-100%)'],
                datasets: [{{
                    data: [
                        {dashboard_data['charts_data']['distributions']['cpu']['low']},
                        {dashboard_data['charts_data']['distributions']['cpu']['medium']},
                        {dashboard_data['charts_data']['distributions']['cpu']['high']},
                        {dashboard_data['charts_data']['distributions']['cpu']['critical']}
                    ],
                    backgroundColor: ['#28a745', '#ffc107', '#fd7e14', '#dc3545']
                }}]
            }},
            options: {{
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});

        // 内存分布图
        const memoryDistCtx = document.getElementById('memoryDistChart').getContext('2d');
        new Chart(memoryDistCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Low (0-25%)', 'Medium (25-50%)', 'High (50-75%)', 'Critical (75-100%)'],
                datasets: [{{
                    data: [
                        {dashboard_data['charts_data']['distributions']['memory']['low']},
                        {dashboard_data['charts_data']['distributions']['memory']['medium']},
                        {dashboard_data['charts_data']['distributions']['memory']['high']},
                        {dashboard_data['charts_data']['distributions']['memory']['critical']}
                    ],
                    backgroundColor: ['#28a745', '#ffc107', '#fd7e14', '#dc3545']
                }}]
            }},
            options: {{
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
        
        return html_template
    
    def _generate_alerts_html(self, alerts: List[Dict[str, Any]]) -> str:
        """生成告警HTML"""
        if not alerts:
            return '<div class="text-muted">暂无告警</div>'
        
        alerts_html = []
        for alert in alerts:
            css_class = f"alert-{alert['severity']}"
            alerts_html.append(f'''
                <div class="alert-item {css_class}">
                    <div class="d-flex justify-content-between">
                        <strong>{alert['category'].upper()}</strong>
                        <small>{alert['timestamp']}</small>
                    </div>
                    <div>{alert['message']}</div>
                    <div class="small text-muted">当前值: {alert['value']:.2f}</div>
                </div>
            ''')
        
        return ''.join(alerts_html)
    
    def _generate_data_api(self, dashboard_data: Dict[str, Any]):
        """生成数据API文件"""
        api_path = self.output_dir / "dashboard_data.json"
        with open(api_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False, default=str)
    
    def start_live_dashboard(self, port: int = 8080, interval: int = 30):
        """启动实时仪表板服务"""
        try:
            import http.server
            import socketserver
            import threading
            import webbrowser
            
            # 设置HTTP服务器
            class DashboardHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(self.output_dir), **kwargs)
            
            # 定期更新仪表板
            def update_dashboard():
                while True:
                    try:
                        self.generate_dashboard(auto_refresh=False)
                        time.sleep(interval)
                    except Exception as e:
                        self.logger.error(f"Error updating dashboard: {e}")
                        time.sleep(interval)
            
            # 启动更新线程
            update_thread = threading.Thread(target=update_dashboard, daemon=True)
            update_thread.start()
            
            # 生成初始仪表板
            self.generate_dashboard(auto_refresh=False)
            
            # 启动HTTP服务器
            with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
                dashboard_url = f"http://localhost:{port}/performance_dashboard.html"
                self.logger.info(f"Dashboard server started at {dashboard_url}")
                
                # 自动打开浏览器
                try:
                    webbrowser.open(dashboard_url)
                except Exception:
                    pass
                
                httpd.serve_forever()
                
        except ImportError:
            self.logger.error("HTTP server not available")
        except Exception as e:
            self.logger.error(f"Failed to start dashboard server: {e}")


# 便捷函数
def generate_performance_dashboard(output_dir: str = "dashboard") -> str:
    """生成性能仪表板"""
    dashboard = PerformanceDashboard(output_dir)
    return dashboard.generate_dashboard()


def start_live_dashboard(port: int = 8080, output_dir: str = "dashboard", interval: int = 30):
    """启动实时性能仪表板"""
    dashboard = PerformanceDashboard(output_dir)
    dashboard.start_live_dashboard(port, interval)