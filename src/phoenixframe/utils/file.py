"""文件操作工具函数"""
import os
import shutil
from pathlib import Path
from typing import Union, Optional, List


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
    
    Returns:
        Path对象
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
        encoding: 编码格式
    
    Returns:
        文件内容
    """
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()


def write_file(file_path: Union[str, Path], content: str, encoding: str = 'utf-8') -> None:
    """
    写入文件内容
    
    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 编码格式
    """
    file_path = Path(file_path)
    # 确保目录存在
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)


def append_file(file_path: Union[str, Path], content: str, encoding: str = 'utf-8') -> None:
    """
    追加内容到文件
    
    Args:
        file_path: 文件路径
        content: 要追加的内容
        encoding: 编码格式
    """
    with open(file_path, 'a', encoding=encoding) as f:
        f.write(content)


def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """
    复制文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
    """
    shutil.copy2(src, dst)


def move_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """
    移动文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
    """
    shutil.move(src, dst)


def delete_file(file_path: Union[str, Path]) -> bool:
    """
    删除文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        是否成功删除
    """
    try:
        os.remove(file_path)
        return True
    except (FileNotFoundError, OSError):
        return False


def list_files(directory: Union[str, Path], pattern: str = "*", recursive: bool = False) -> List[Path]:
    """
    列出目录中的文件
    
    Args:
        directory: 目录路径
        pattern: 文件匹配模式
        recursive: 是否递归搜索
    
    Returns:
        文件路径列表
    """
    directory = Path(directory)
    
    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件大小（字节）
    """
    return Path(file_path).stat().st_size


def file_exists(file_path: Union[str, Path]) -> bool:
    """
    检查文件是否存在
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件是否存在
    """
    return Path(file_path).exists()


def create_temp_file(suffix: str = '.tmp', prefix: str = 'temp_', directory: Optional[Union[str, Path]] = None) -> Path:
    """
    创建临时文件
    
    Args:
        suffix: 文件后缀
        prefix: 文件前缀
        directory: 临时文件目录
    
    Returns:
        临时文件路径
    """
    import tempfile
    
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
    os.close(fd)  # 关闭文件描述符
    return Path(path)


def clean_directory(directory: Union[str, Path], pattern: str = "*") -> int:
    """
    清理目录中的文件
    
    Args:
        directory: 目录路径
        pattern: 文件匹配模式
    
    Returns:
        删除的文件数量
    """
    directory = Path(directory)
    if not directory.exists():
        return 0
    
    files = list(directory.glob(pattern))
    count = 0
    
    for file_path in files:
        if file_path.is_file():
            try:
                file_path.unlink()
                count += 1
            except OSError:
                pass
    
    return count


def backup_file(file_path: Union[str, Path], backup_suffix: str = '.bak') -> Optional[Path]:
    """
    备份文件
    
    Args:
        file_path: 文件路径
        backup_suffix: 备份文件后缀
    
    Returns:
        备份文件路径，如果备份失败返回None
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None
    
    backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)
    
    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except OSError:
        return None