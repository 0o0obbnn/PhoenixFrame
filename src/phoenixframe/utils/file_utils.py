"""文件操作工具模块"""
import os
import json
import yaml
import csv
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class FileUtil:
    """文件操作工具类"""
    
    @staticmethod
    def read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        读取JSON文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: JSON数据
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def write_json(file_path: Union[str, Path], data: Dict[str, Any], 
                   indent: int = 2, ensure_ascii: bool = False) -> None:
        """
        写入JSON文件
        
        Args:
            file_path: 文件路径
            data: 要写入的数据
            indent: 缩进空格数
            ensure_ascii: 是否确保ASCII编码
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
    
    @staticmethod
    def read_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        读取YAML文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: YAML数据
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def write_yaml(file_path: Union[str, Path], data: Dict[str, Any]) -> None:
        """
        写入YAML文件
        
        Args:
            file_path: 文件路径
            data: 要写入的数据
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    @staticmethod
    def read_csv(file_path: Union[str, Path], delimiter: str = ',') -> List[Dict[str, Any]]:
        """
        读取CSV文件
        
        Args:
            file_path: 文件路径
            delimiter: 分隔符
            
        Returns:
            List[Dict[str, Any]]: CSV数据
        """
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                data.append(dict(row))
        return data
    
    @staticmethod
    def write_csv(file_path: Union[str, Path], data: List[Dict[str, Any]], 
                  delimiter: str = ',') -> None:
        """
        写入CSV文件
        
        Args:
            file_path: 文件路径
            data: 要写入的数据
            delimiter: 分隔符
        """
        if not data:
            return
        
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(data)
    
    @staticmethod
    def read_text(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
        """
        读取文本文件
        
        Args:
            file_path: 文件路径
            encoding: 编码格式
            
        Returns:
            str: 文件内容
        """
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    
    @staticmethod
    def write_text(file_path: Union[str, Path], content: str, 
                   encoding: str = 'utf-8') -> None:
        """
        写入文本文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 编码格式
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
    
    @staticmethod
    def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
        """
        复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
        """
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    
    @staticmethod
    def move_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
        """
        移动文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
        """
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
    
    @staticmethod
    def delete_file(file_path: Union[str, Path]) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否删除成功
        """
        try:
            os.remove(file_path)
            return True
        except OSError:
            return False
    
    @staticmethod
    def create_directory(dir_path: Union[str, Path]) -> None:
        """
        创建目录
        
        Args:
            dir_path: 目录路径
        """
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def delete_directory(dir_path: Union[str, Path]) -> bool:
        """
        删除目录
        
        Args:
            dir_path: 目录路径
            
        Returns:
            bool: 是否删除成功
        """
        try:
            shutil.rmtree(dir_path)
            return True
        except OSError:
            return False
    
    @staticmethod
    def list_files(dir_path: Union[str, Path], pattern: str = "*", 
                   recursive: bool = False) -> List[Path]:
        """
        列出目录中的文件
        
        Args:
            dir_path: 目录路径
            pattern: 文件模式
            recursive: 是否递归搜索
            
        Returns:
            List[Path]: 文件路径列表
        """
        path = Path(dir_path)
        if recursive:
            return list(path.rglob(pattern))
        else:
            return list(path.glob(pattern))
    
    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            int: 文件大小（字节）
        """
        return os.path.getsize(file_path)
    
    @staticmethod
    def file_exists(file_path: Union[str, Path]) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否存在
        """
        return Path(file_path).exists()
    
    @staticmethod
    def is_file(path: Union[str, Path]) -> bool:
        """
        检查路径是否为文件
        
        Args:
            path: 路径
            
        Returns:
            bool: 是否为文件
        """
        return Path(path).is_file()
    
    @staticmethod
    def is_directory(path: Union[str, Path]) -> bool:
        """
        检查路径是否为目录
        
        Args:
            path: 路径
            
        Returns:
            bool: 是否为目录
        """
        return Path(path).is_dir()
