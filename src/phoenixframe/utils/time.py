"""时间处理工具函数"""
import time
from datetime import datetime, timedelta
from typing import Union, Optional


def get_timestamp(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    获取当前时间戳
    
    Args:
        format: 时间格式
    
    Returns:
        格式化的时间字符串
    """
    return datetime.now().strftime(format)


def format_duration(seconds: float) -> str:
    """
    格式化持续时间
    
    Args:
        seconds: 秒数
    
    Returns:
        格式化的持续时间字符串
    """
    if seconds < 1:
        return f"{seconds*1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.2f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {minutes}m {remaining_seconds:.2f}s"


def parse_duration(duration_str: str) -> float:
    """
    解析持续时间字符串为秒数
    
    Args:
        duration_str: 持续时间字符串 (如 "1h 30m", "45s", "2.5m")
    
    Returns:
        秒数
    """
    duration_str = duration_str.strip().lower()
    total_seconds = 0.0
    
    # 处理小时
    if 'h' in duration_str:
        parts = duration_str.split('h')
        hours = float(parts[0].strip())
        total_seconds += hours * 3600
        duration_str = parts[1].strip() if len(parts) > 1 else ""
    
    # 处理分钟
    if 'm' in duration_str and 'ms' not in duration_str:
        parts = duration_str.split('m')
        minutes = float(parts[0].strip()) if parts[0].strip() else 0
        total_seconds += minutes * 60
        duration_str = parts[1].strip() if len(parts) > 1 else ""
    
    # 处理毫秒
    if 'ms' in duration_str:
        parts = duration_str.split('ms')
        milliseconds = float(parts[0].strip()) if parts[0].strip() else 0
        total_seconds += milliseconds / 1000
        duration_str = parts[1].strip() if len(parts) > 1 else ""
    
    # 处理秒
    if 's' in duration_str:
        parts = duration_str.split('s')
        seconds = float(parts[0].strip()) if parts[0].strip() else 0
        total_seconds += seconds
    elif duration_str and not any(unit in duration_str for unit in ['h', 'm', 's']):
        # 如果只是数字，默认为秒
        total_seconds += float(duration_str)
    
    return total_seconds


def get_iso_timestamp() -> str:
    """
    获取ISO格式的时间戳
    
    Returns:
        ISO格式时间字符串
    """
    return datetime.now().isoformat()


def get_unix_timestamp() -> float:
    """
    获取Unix时间戳
    
    Returns:
        Unix时间戳
    """
    return time.time()


def sleep_until(target_time: Union[datetime, str], check_interval: float = 1.0) -> None:
    """
    睡眠直到指定时间
    
    Args:
        target_time: 目标时间
        check_interval: 检查间隔（秒）
    """
    if isinstance(target_time, str):
        target_time = datetime.fromisoformat(target_time)
    
    while datetime.now() < target_time:
        remaining = (target_time - datetime.now()).total_seconds()
        if remaining <= 0:
            break
        
        sleep_duration = min(check_interval, remaining)
        time.sleep(sleep_duration)


def time_diff(start_time: Union[datetime, str], end_time: Optional[Union[datetime, str]] = None) -> float:
    """
    计算时间差
    
    Args:
        start_time: 开始时间
        end_time: 结束时间，默认为当前时间
    
    Returns:
        时间差（秒）
    """
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    
    if end_time is None:
        end_time = datetime.now()
    elif isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)
    
    return (end_time - start_time).total_seconds()


def add_time(base_time: Union[datetime, str], **kwargs) -> datetime:
    """
    在基础时间上添加时间
    
    Args:
        base_time: 基础时间
        **kwargs: 时间增量参数 (days, hours, minutes, seconds, etc.)
    
    Returns:
        新的时间
    """
    if isinstance(base_time, str):
        base_time = datetime.fromisoformat(base_time)
    
    delta = timedelta(**kwargs)
    return base_time + delta


def is_timeout(start_time: Union[datetime, str], timeout_seconds: float) -> bool:
    """
    检查是否超时
    
    Args:
        start_time: 开始时间
        timeout_seconds: 超时时间（秒）
    
    Returns:
        是否超时
    """
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    return elapsed > timeout_seconds


def wait_for(condition_func, timeout: float = 30.0, interval: float = 1.0, timeout_message: str = "Timeout waiting for condition") -> bool:
    """
    等待条件满足
    
    Args:
        condition_func: 条件函数
        timeout: 超时时间（秒）
        interval: 检查间隔（秒）
        timeout_message: 超时错误信息
    
    Returns:
        条件是否满足
    
    Raises:
        TimeoutError: 超时异常
    """
    start_time = datetime.now()
    
    while True:
        if condition_func():
            return True
        
        if is_timeout(start_time, timeout):
            raise TimeoutError(timeout_message)
        
        time.sleep(interval)


class Timer:
    """简单的计时器类"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """开始计时"""
        self.start_time = datetime.now()
        self.end_time = None
        return self
    
    def stop(self):
        """停止计时"""
        self.end_time = datetime.now()
        return self
    
    def elapsed(self) -> float:
        """获取已过时间（秒）"""
        if self.start_time is None:
            return 0.0
        
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def elapsed_str(self) -> str:
        """获取格式化的已过时间"""
        return format_duration(self.elapsed())
    
    def __enter__(self):
        """上下文管理器入口"""
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
    
    def __str__(self):
        return self.elapsed_str()