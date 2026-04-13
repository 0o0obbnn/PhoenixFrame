"""OpenTelemetry全链路追踪演示

展示PhoenixFrame增强后的分布式追踪功能：
- 自动instrumentation
- 跨服务追踪上下文传播
- 丰富的span属性和事件
- 自动化装饰器
"""

import time
import random
from typing import Dict, Any

from ..observability.tracer import (
    setup_tracing, get_tracer, trace_test, trace_api, trace_web, trace_db,
    auto_trace, trace_test_method, TraceContext, create_trace_context_headers
)
from ..observability.logger import get_logger

# 设置日志
logger = get_logger(__name__)


def demo_basic_tracing():
    """演示基础追踪功能"""
    print("🔍 演示基础分布式追踪功能...")
    
    # 初始化追踪系统
    success = setup_tracing(
        service_name="phoenixframe-demo",
        service_version="3.2.0",
        console_export=True,
        auto_instrument=True,
        sample_rate=1.0,
        resource_attributes={
            "environment": "demo",
            "team": "phoenixframe"
        }
    )
    
    if not success:
        print("❌ 追踪系统初始化失败")
        return
    
    tracer = get_tracer("demo")
    
    # 设置关联ID用于跨服务追踪
    tracer.set_correlation_id("demo-correlation-123")
    
    # 模拟测试用例追踪
    with tracer.trace_test_case(
        test_name="test_user_login", 
        test_file="test_auth.py",
        test_suite="authentication_tests",
        test_id="AUTH_001"
    ):
        logger.info("开始执行用户登录测试")
        
        # 模拟API请求追踪
        with tracer.trace_api_request(
            method="POST",
            url="https://api.example.com/auth/login",
            status_code=200,
            response_time=0.245,
            request_size=125,
            response_size=340,
            user_agent="PhoenixFrame/3.2.0"
        ):
            time.sleep(0.1)  # 模拟网络延迟
            tracer.add_event("authentication_successful", {
                "user_id": "12345",
                "login_method": "password"
            })
        
        # 模拟页面操作追踪
        with tracer.trace_page_action(
            action="click",
            element="login_button",
            element_type="button",
            page_url="https://example.com/login",
            duration=0.05
        ):
            time.sleep(0.05)
            
        # 模拟数据库查询追踪
        with tracer.trace_database_query(
            operation="SELECT",
            table="users",
            query="SELECT id, username FROM users WHERE email = ?",
            database="auth_db",
            rows_affected=1,
            execution_time=0.025
        ):
            time.sleep(0.025)
        
        logger.info("用户登录测试完成")


@auto_trace(operation_type="business_logic", include_args=True, include_result=True)
def calculate_user_score(user_id: str, base_score: int = 100) -> Dict[str, Any]:
    """计算用户分数（带自动追踪）"""
    # 模拟复杂计算
    bonus = random.randint(1, 50)
    final_score = base_score + bonus
    
    # 添加业务事件
    tracer = get_tracer(__name__)
    tracer.add_event("score_calculated", {
        "user_id": user_id,
        "base_score": base_score,
        "bonus": bonus,
        "final_score": final_score
    })
    
    time.sleep(0.01)  # 模拟处理时间
    
    return {
        "user_id": user_id,
        "final_score": final_score,
        "calculation_time": "10ms"
    }


@trace_test_method(test_suite="user_management", test_id="USER_001")
def test_user_creation():
    """测试用户创建（带测试追踪）"""
    logger.info("开始用户创建测试")
    
    # 模拟用户创建流程
    user_data = {
        "username": "test_user",
        "email": "test@example.com"
    }
    
    tracer = get_tracer(__name__)
    tracer.set_attribute("test.user_data", str(user_data))
    
    # 模拟API调用
    with trace_api("POST", "https://api.example.com/users", 201, 0.15):
        time.sleep(0.15)
    
    # 模拟数据库验证
    with trace_db("SELECT", "users", "SELECT * FROM users WHERE username = 'test_user'"):
        time.sleep(0.02)
    
    logger.info("用户创建测试完成")
    return True


def demo_context_propagation():
    """演示跨服务上下文传播"""
    print("\n🌐 演示跨服务追踪上下文传播...")
    
    tracer = get_tracer("demo.service_a")
    
    with tracer.start_as_current_span("service_a_operation"):
        # 获取当前追踪上下文
        trace_headers = create_trace_context_headers()
        logger.info(f"生成追踪头: {trace_headers}")
        
        # 模拟服务间调用
        simulate_service_b_call(trace_headers)


def simulate_service_b_call(headers: Dict[str, str]):
    """模拟服务B的调用（恢复追踪上下文）"""
    # 使用TraceContext管理器恢复上下文
    with TraceContext(headers):
        tracer = get_tracer("demo.service_b")
        
        with tracer.start_as_current_span("service_b_operation"):
            logger.info("在服务B中执行操作，追踪上下文已恢复")
            
            # 验证关联ID是否正确传播
            correlation_id = tracer.get_correlation_id()
            logger.info(f"关联ID: {correlation_id}")
            
            # 模拟更多操作
            with trace_db("INSERT", "audit_log", "INSERT INTO audit_log ..."):
                time.sleep(0.01)


def demo_error_tracking():
    """演示错误追踪"""
    print("\n💥 演示错误和异常追踪...")
    
    tracer = get_tracer("demo.error_handling")
    
    try:
        with tracer.start_as_current_span("error_prone_operation"):
            tracer.add_event("operation_started")
            
            # 模拟一些正常操作
            time.sleep(0.05)
            
            # 模拟错误
            raise ValueError("模拟的业务逻辑错误")
            
    except ValueError as e:
        logger.error(f"捕获到预期错误: {e}")


def demo_performance_tracking():
    """演示性能追踪"""
    print("\n⚡ 演示性能追踪...")
    
    # 测试不同的业务操作
    operations = [
        ("快速操作", 0.01),
        ("中等操作", 0.1),
        ("慢速操作", 0.5)
    ]
    
    for op_name, duration in operations:
        result = calculate_user_score(f"user_{op_name}", random.randint(50, 150))
        logger.info(f"{op_name}完成: {result}")


def main():
    """运行所有演示"""
    print("🚀 PhoenixFrame OpenTelemetry 全链路追踪演示")
    print("=" * 60)
    
    try:
        # 基础追踪功能
        demo_basic_tracing()
        
        # 自动追踪装饰器
        print("\n🎯 演示自动追踪装饰器...")
        calculate_user_score("demo_user_001", 120)
        
        # 测试方法追踪
        print("\n🧪 演示测试方法追踪...")
        test_user_creation()
        
        # 上下文传播
        demo_context_propagation()
        
        # 错误追踪
        demo_error_tracking()
        
        # 性能追踪
        demo_performance_tracking()
        
        print("\n✅ 所有演示完成！")
        print("\n📊 追踪数据已发送到配置的导出器")
        print("🔍 如果启用了控制台导出，可以在上方看到详细的span信息")
        
    except Exception as e:
        logger.error(f"演示执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()