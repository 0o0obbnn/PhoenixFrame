"""测试数据版本控制模块"""
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from . import TestDataset, DataRepository
from ..observability.logger import get_logger
from ..observability.tracer import get_tracer


class ChangeType(Enum):
    """变更类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"


@dataclass
class DataChange:
    """数据变更记录"""
    change_id: str
    change_type: ChangeType
    dataset_id: str
    timestamp: datetime
    author: str
    message: str
    previous_version: Optional[str] = None
    new_version: Optional[str] = None
    affected_records: int = 0
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataVersion:
    """数据版本"""
    version: str
    dataset_id: str
    timestamp: datetime
    author: str
    message: str
    checksum: str
    file_path: str
    parent_version: Optional[str] = None
    record_count: int = 0
    schema_version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Branch:
    """数据分支"""
    name: str
    dataset_id: str
    head_version: str
    created_at: datetime
    created_by: str
    description: str = ""
    is_protected: bool = False
    parent_branch: Optional[str] = None


class DataVersionControl:
    """数据版本控制系统"""
    
    def __init__(self, repository_path: str = "data_versions"):
        self.repository_path = Path(repository_path)
        self.repository_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = get_logger("phoenixframe.data.version")
        self.tracer = get_tracer("phoenixframe.data.version")
        
        # 版本控制文件
        self.versions_file = self.repository_path / "versions.json"
        self.changes_file = self.repository_path / "changes.json"
        self.branches_file = self.repository_path / "branches.json"
        
        # 数据存储目录
        self.data_dir = self.repository_path / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # 加载版本信息
        self._versions = self._load_versions()
        self._changes = self._load_changes()
        self._branches = self._load_branches()
        
        # 当前分支
        self._current_branch = "main"
        
        # 创建主分支（如果不存在）
        if "main" not in self._branches:
            self._create_main_branch()
    
    def commit(self, dataset: TestDataset, message: str, author: str = "system") -> str:
        """提交数据版本"""
        with self.tracer.trace_test_case(f"data_commit_{dataset.name}", "", "running"):
            try:
                dataset_id = self._get_dataset_id(dataset.name)
                version = self._generate_version(dataset_id)
                
                # 计算数据校验和
                checksum = self._calculate_checksum(dataset.data)
                
                # 检查是否有变更
                if self._is_unchanged(dataset_id, checksum):
                    self.logger.info(f"No changes detected for dataset {dataset.name}")
                    return self._get_latest_version(dataset_id)
                
                # 保存数据文件（确保目录存在）
                version_file = self.data_dir / f"{dataset_id}_{version}.json"
                version_file.parent.mkdir(parents=True, exist_ok=True)
                dataset_dict = {
                    "name": dataset.name,
                    "description": dataset.description,
                    "data": dataset.data,
                    "schema": dataset.schema,
                    "version": version,
                    "tags": dataset.tags,
                    "created_at": dataset.created_at.isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "metadata": dataset.metadata
                }
                
                with open(version_file, 'w', encoding='utf-8') as f:
                    json.dump(dataset_dict, f, indent=2, ensure_ascii=False)
                
                # 创建版本记录
                parent_version = self._get_latest_version(dataset_id)
                data_version = DataVersion(
                    version=version,
                    dataset_id=dataset_id,
                    timestamp=datetime.now(),
                    author=author,
                    message=message,
                    checksum=checksum,
                    file_path=str(version_file),
                    parent_version=parent_version,
                    record_count=len(dataset.data),
                    tags=dataset.tags.copy(),
                    metadata=dataset.metadata.copy()
                )
                
                self._versions[version] = data_version
                
                # 创建变更记录
                change_type = ChangeType.CREATE if not parent_version else ChangeType.UPDATE
                change = DataChange(
                    change_id=self._generate_change_id(),
                    change_type=change_type,
                    dataset_id=dataset_id,
                    timestamp=datetime.now(),
                    author=author,
                    message=message,
                    previous_version=parent_version,
                    new_version=version,
                    affected_records=len(dataset.data),
                    checksum=checksum
                )
                
                self._changes[change.change_id] = change
                
                # 更新分支头部
                if self._current_branch in self._branches:
                    self._branches[self._current_branch].head_version = version
                
                # 保存所有变更
                self._save_versions()
                self._save_changes()
                self._save_branches()
                
                self.logger.info(f"Committed dataset {dataset.name} as version {version}")
                return version
                
            except Exception as e:
                self.logger.error(f"Failed to commit dataset {dataset.name}: {e}")
                raise
    
    def checkout(self, dataset_id: str, version: Optional[str] = None, branch: Optional[str] = None) -> TestDataset:
        """检出指定版本的数据集"""
        with self.tracer.trace_test_case(f"data_checkout_{dataset_id}", "", "running"):
            try:
                target_version = version
                
                if branch:
                    if branch not in self._branches:
                        raise ValueError(f"Branch {branch} not found")
                    target_version = self._branches[branch].head_version
                    self._current_branch = branch
                
                if not target_version:
                    target_version = self._get_latest_version(dataset_id)
                
                if target_version not in self._versions:
                    raise ValueError(f"Version {target_version} not found")
                
                version_info = self._versions[target_version]
                version_file = Path(version_info.file_path)
                
                if not version_file.exists():
                    raise FileNotFoundError(f"Version file not found: {version_file}")
                
                with open(version_file, 'r', encoding='utf-8') as f:
                    dataset_dict = json.load(f)
                
                dataset = TestDataset(
                    name=dataset_dict["name"],
                    description=dataset_dict["description"],
                    data=dataset_dict["data"],
                    schema=dataset_dict.get("schema"),
                    version=dataset_dict["version"],
                    tags=dataset_dict.get("tags", []),
                    created_at=datetime.fromisoformat(dataset_dict["created_at"]),
                    updated_at=datetime.fromisoformat(dataset_dict["updated_at"]),
                    metadata=dataset_dict.get("metadata", {})
                )
                
                self.logger.info(f"Checked out dataset {dataset_id} version {target_version}")
                return dataset
                
            except Exception as e:
                self.logger.error(f"Failed to checkout dataset {dataset_id}: {e}")
                raise
    
    def create_branch(self, branch_name: str, from_version: Optional[str] = None, 
                     description: str = "", author: str = "system") -> Branch:
        """创建新分支"""
        if branch_name in self._branches:
            raise ValueError(f"Branch {branch_name} already exists")
        
        head_version = from_version or self._get_latest_version_in_branch(self._current_branch)
        
        branch = Branch(
            name=branch_name,
            dataset_id="",  # 分支可以包含多个数据集
            head_version=head_version,
            created_at=datetime.now(),
            created_by=author,
            description=description,
            parent_branch=self._current_branch
        )
        
        self._branches[branch_name] = branch
        self._save_branches()
        
        self.logger.info(f"Created branch {branch_name}")
        return branch
    
    def merge_branch(self, source_branch: str, target_branch: str = None, 
                    message: str = "", author: str = "system") -> List[str]:
        """合并分支"""
        if source_branch not in self._branches:
            raise ValueError(f"Source branch {source_branch} not found")
        
        target_branch = target_branch or "main"
        if target_branch not in self._branches:
            raise ValueError(f"Target branch {target_branch} not found")
        
        source_head = self._branches[source_branch].head_version
        target_head = self._branches[target_branch].head_version
        
        # 简化的合并策略：直接更新目标分支头部
        # 在实际应用中，这里需要更复杂的合并逻辑
        merged_versions = []
        
        # 获取源分支的所有版本
        source_versions = self._get_branch_versions(source_branch)
        
        for version in source_versions:
            if version not in self._get_branch_versions(target_branch):
                merged_versions.append(version)
        
        # 更新目标分支头部
        self._branches[target_branch].head_version = source_head
        
        # 创建合并变更记录
        merge_message = message or f"Merge branch {source_branch} into {target_branch}"
        change = DataChange(
            change_id=self._generate_change_id(),
            change_type=ChangeType.UPDATE,
            dataset_id="",
            timestamp=datetime.now(),
            author=author,
            message=merge_message,
            previous_version=target_head,
            new_version=source_head,
            metadata={"merge": True, "source_branch": source_branch, "target_branch": target_branch}
        )
        
        self._changes[change.change_id] = change
        self._save_branches()
        self._save_changes()
        
        self.logger.info(f"Merged branch {source_branch} into {target_branch}")
        return merged_versions
    
    def get_version_history(self, dataset_id: str, limit: int = 50) -> List[DataVersion]:
        """获取版本历史"""
        versions = []
        
        for version_key, version in self._versions.items():
            if version.dataset_id == dataset_id:
                versions.append(version)
        
        # 按时间排序
        versions.sort(key=lambda v: v.timestamp, reverse=True)
        return versions[:limit]
    
    def get_change_log(self, dataset_id: str = None, limit: int = 50) -> List[DataChange]:
        """获取变更日志"""
        changes = []
        
        for change_key, change in self._changes.items():
            if dataset_id is None or change.dataset_id == dataset_id:
                changes.append(change)
        
        # 按时间排序
        changes.sort(key=lambda c: c.timestamp, reverse=True)
        return changes[:limit]
    
    def compare_versions(self, dataset_id: str, version1: str, version2: str) -> Dict[str, Any]:
        """比较两个版本"""
        if version1 not in self._versions or version2 not in self._versions:
            raise ValueError("One or both versions not found")
        
        dataset1 = self.checkout(dataset_id, version1)
        dataset2 = self.checkout(dataset_id, version2)
        
        comparison = {
            "version1": version1,
            "version2": version2,
            "record_count_diff": len(dataset2.data) - len(dataset1.data),
            "schema_changed": dataset1.schema != dataset2.schema,
            "data_checksum1": self._calculate_checksum(dataset1.data),
            "data_checksum2": self._calculate_checksum(dataset2.data),
            "changes": []
        }
        
        # 详细的数据比较（简化版）
        data1_ids = {item.get("id", i): item for i, item in enumerate(dataset1.data)}
        data2_ids = {item.get("id", i): item for i, item in enumerate(dataset2.data)}
        
        # 新增记录
        for record_id in data2_ids:
            if record_id not in data1_ids:
                comparison["changes"].append({
                    "type": "added",
                    "record_id": record_id,
                    "record": data2_ids[record_id]
                })
        
        # 删除记录
        for record_id in data1_ids:
            if record_id not in data2_ids:
                comparison["changes"].append({
                    "type": "deleted",
                    "record_id": record_id,
                    "record": data1_ids[record_id]
                })
        
        # 修改记录
        for record_id in data1_ids:
            if record_id in data2_ids and data1_ids[record_id] != data2_ids[record_id]:
                comparison["changes"].append({
                    "type": "modified",
                    "record_id": record_id,
                    "old_record": data1_ids[record_id],
                    "new_record": data2_ids[record_id]
                })
        
        return comparison
    
    def rollback(self, dataset_id: str, target_version: str, message: str = "", author: str = "system") -> str:
        """回滚到指定版本"""
        if target_version not in self._versions:
            raise ValueError(f"Target version {target_version} not found")
        
        # 检出目标版本
        dataset = self.checkout(dataset_id, target_version)
        
        # 创建新的回滚版本
        rollback_message = message or f"Rollback to version {target_version}"
        new_version = self.commit(dataset, rollback_message, author)
        
        # 创建回滚变更记录
        change = DataChange(
            change_id=self._generate_change_id(),
            change_type=ChangeType.RESTORE,
            dataset_id=dataset_id,
            timestamp=datetime.now(),
            author=author,
            message=rollback_message,
            previous_version=self._get_latest_version(dataset_id),
            new_version=new_version,
            metadata={"rollback_target": target_version}
        )
        
        self._changes[change.change_id] = change
        self._save_changes()
        
        self.logger.info(f"Rolled back dataset {dataset_id} to version {target_version}")
        return new_version
    
    def tag_version(self, version: str, tag: str, description: str = "", author: str = "system") -> None:
        """为版本添加标签"""
        if version not in self._versions:
            raise ValueError(f"Version {version} not found")
        
        version_info = self._versions[version]
        if tag not in version_info.tags:
            version_info.tags.append(tag)
            version_info.metadata[f"tag_{tag}"] = {
                "description": description,
                "created_by": author,
                "created_at": datetime.now().isoformat()
            }
            
            self._save_versions()
            self.logger.info(f"Tagged version {version} with {tag}")
    
    def list_branches(self) -> List[Branch]:
        """列出所有分支"""
        return list(self._branches.values())
    
    def get_current_branch(self) -> str:
        """获取当前分支"""
        return self._current_branch
    
    def switch_branch(self, branch_name: str) -> None:
        """切换分支"""
        if branch_name not in self._branches:
            raise ValueError(f"Branch {branch_name} not found")
        
        self._current_branch = branch_name
        self.logger.info(f"Switched to branch {branch_name}")
    
    def _get_dataset_id(self, dataset_name: str) -> str:
        """获取数据集ID"""
        return dataset_name.lower().replace(" ", "_")
    
    def _generate_version(self, dataset_id: str) -> str:
        """生成版本号，确保同一秒内也能唯一"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{dataset_id}_{timestamp}"
    
    def _generate_change_id(self) -> str:
        """生成变更ID"""
        return f"change_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 10000}"
    
    def _calculate_checksum(self, data: List[Dict[str, Any]]) -> str:
        """计算数据校验和"""
        data_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_json.encode()).hexdigest()[:16]
    
    def _is_unchanged(self, dataset_id: str, checksum: str) -> bool:
        """检查数据是否未变更"""
        latest_version = self._get_latest_version(dataset_id)
        if not latest_version:
            return False
        
        return self._versions[latest_version].checksum == checksum
    
    def _get_latest_version(self, dataset_id: str) -> Optional[str]:
        """获取最新版本"""
        versions = [v for v in self._versions.values() if v.dataset_id == dataset_id]
        if not versions:
            return None
        
        latest = max(versions, key=lambda v: v.timestamp)
        return latest.version
    
    def _get_latest_version_in_branch(self, branch_name: str) -> Optional[str]:
        """获取分支中的最新版本"""
        if branch_name not in self._branches:
            return None
        
        return self._branches[branch_name].head_version
    
    def _get_branch_versions(self, branch_name: str) -> List[str]:
        """获取分支的所有版本"""
        # 简化实现：返回所有版本
        # 实际应用中需要追踪分支的版本链
        return list(self._versions.keys())
    
    def _create_main_branch(self) -> None:
        """创建主分支"""
        main_branch = Branch(
            name="main",
            dataset_id="",
            head_version="",
            created_at=datetime.now(),
            created_by="system",
            description="Main branch",
            is_protected=True
        )
        
        self._branches["main"] = main_branch
        self._save_branches()
    
    def _load_versions(self) -> Dict[str, DataVersion]:
        """加载版本信息"""
        if not self.versions_file.exists():
            return {}
        
        try:
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            versions = {}
            for version_key, version_data in data.items():
                version = DataVersion(
                    version=version_data["version"],
                    dataset_id=version_data["dataset_id"],
                    timestamp=datetime.fromisoformat(version_data["timestamp"]),
                    author=version_data["author"],
                    message=version_data["message"],
                    checksum=version_data["checksum"],
                    file_path=version_data["file_path"],
                    parent_version=version_data.get("parent_version"),
                    record_count=version_data.get("record_count", 0),
                    schema_version=version_data.get("schema_version", "1.0"),
                    tags=version_data.get("tags", []),
                    metadata=version_data.get("metadata", {})
                )
                versions[version_key] = version
            
            return versions
        except Exception as e:
            self.logger.error(f"Failed to load versions: {e}")
            return {}
    
    def _save_versions(self) -> None:
        """保存版本信息"""
        data = {}
        for version_key, version in self._versions.items():
            data[version_key] = {
                "version": version.version,
                "dataset_id": version.dataset_id,
                "timestamp": version.timestamp.isoformat(),
                "author": version.author,
                "message": version.message,
                "checksum": version.checksum,
                "file_path": version.file_path,
                "parent_version": version.parent_version,
                "record_count": version.record_count,
                "schema_version": version.schema_version,
                "tags": version.tags,
                "metadata": version.metadata
            }
        
        with open(self.versions_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_changes(self) -> Dict[str, DataChange]:
        """加载变更记录"""
        if not self.changes_file.exists():
            return {}
        
        try:
            with open(self.changes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            changes = {}
            for change_key, change_data in data.items():
                change = DataChange(
                    change_id=change_data["change_id"],
                    change_type=ChangeType(change_data["change_type"]),
                    dataset_id=change_data["dataset_id"],
                    timestamp=datetime.fromisoformat(change_data["timestamp"]),
                    author=change_data["author"],
                    message=change_data["message"],
                    previous_version=change_data.get("previous_version"),
                    new_version=change_data.get("new_version"),
                    affected_records=change_data.get("affected_records", 0),
                    checksum=change_data.get("checksum"),
                    metadata=change_data.get("metadata", {})
                )
                changes[change_key] = change
            
            return changes
        except Exception as e:
            self.logger.error(f"Failed to load changes: {e}")
            return {}
    
    def _save_changes(self) -> None:
        """保存变更记录"""
        data = {}
        for change_key, change in self._changes.items():
            data[change_key] = {
                "change_id": change.change_id,
                "change_type": change.change_type.value,
                "dataset_id": change.dataset_id,
                "timestamp": change.timestamp.isoformat(),
                "author": change.author,
                "message": change.message,
                "previous_version": change.previous_version,
                "new_version": change.new_version,
                "affected_records": change.affected_records,
                "checksum": change.checksum,
                "metadata": change.metadata
            }
        
        with open(self.changes_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_branches(self) -> Dict[str, Branch]:
        """加载分支信息"""
        if not self.branches_file.exists():
            return {}
        
        try:
            with open(self.branches_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            branches = {}
            for branch_key, branch_data in data.items():
                branch = Branch(
                    name=branch_data["name"],
                    dataset_id=branch_data["dataset_id"],
                    head_version=branch_data["head_version"],
                    created_at=datetime.fromisoformat(branch_data["created_at"]),
                    created_by=branch_data["created_by"],
                    description=branch_data.get("description", ""),
                    is_protected=branch_data.get("is_protected", False),
                    parent_branch=branch_data.get("parent_branch")
                )
                branches[branch_key] = branch
            
            return branches
        except Exception as e:
            self.logger.error(f"Failed to load branches: {e}")
            return {}
    
    def _save_branches(self) -> None:
        """保存分支信息"""
        data = {}
        for branch_key, branch in self._branches.items():
            data[branch_key] = {
                "name": branch.name,
                "dataset_id": branch.dataset_id,
                "head_version": branch.head_version,
                "created_at": branch.created_at.isoformat(),
                "created_by": branch.created_by,
                "description": branch.description,
                "is_protected": branch.is_protected,
                "parent_branch": branch.parent_branch
            }
        
        with open(self.branches_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# 全局实例
_version_control: Optional[DataVersionControl] = None


def get_version_control(repository_path: str = "data_versions") -> DataVersionControl:
    """获取数据版本控制实例"""
    global _version_control
    if _version_control is None:
        _version_control = DataVersionControl(repository_path)
    return _version_control


__all__ = [
    "ChangeType",
    "DataChange",
    "DataVersion",
    "Branch",
    "DataVersionControl",
    "get_version_control"
]