"""数据依赖关系管理模块"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading

from . import TestDataset, DataRepository
from ..observability.logger import get_logger
from ..observability.tracer import get_tracer


class DependencyType(Enum):
    """依赖类型"""
    REQUIRED = "required"  # 必需依赖
    OPTIONAL = "optional"  # 可选依赖
    REFERENCE = "reference"  # 引用依赖
    PARENT_CHILD = "parent_child"  # 父子关系
    SEQUENTIAL = "sequential"  # 顺序依赖


@dataclass
class DataDependency:
    """数据依赖关系"""
    source_dataset: str  # 源数据集
    target_dataset: str  # 目标数据集
    dependency_type: DependencyType
    description: str = ""
    constraint: Optional[str] = None  # 约束条件
    mapping: Dict[str, str] = field(default_factory=dict)  # 字段映射
    validation_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DependencyGraph:
    """依赖关系图"""
    nodes: Set[str] = field(default_factory=set)  # 数据集节点
    edges: List[DataDependency] = field(default_factory=list)  # 依赖边
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetInfo:
    """数据集信息"""
    name: str
    version: str
    record_count: int
    schema: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    status: str = "available"  # available, building, error
    last_updated: datetime = field(default_factory=datetime.now)


class CircularDependencyError(Exception):
    """循环依赖错误"""
    pass


class DependencyValidator:
    """依赖关系验证器"""
    
    def __init__(self):
        self.logger = get_logger("phoenixframe.data.dependency.validator")
    
    def validate_dependency(self, dependency: DataDependency, 
                          source_data: TestDataset, 
                          target_data: TestDataset) -> List[str]:
        """验证数据依赖关系"""
        errors = []
        
        try:
            # 基本验证
            if not source_data.data:
                errors.append(f"Source dataset {dependency.source_dataset} is empty")
            
            if not target_data.data:
                errors.append(f"Target dataset {dependency.target_dataset} is empty")
            
            # 字段映射验证
            if dependency.mapping:
                errors.extend(self._validate_field_mapping(dependency, source_data, target_data))
            
            # 引用完整性验证
            if dependency.dependency_type == DependencyType.REFERENCE:
                errors.extend(self._validate_reference_integrity(dependency, source_data, target_data))
            
            # 父子关系验证
            if dependency.dependency_type == DependencyType.PARENT_CHILD:
                errors.extend(self._validate_parent_child_relationship(dependency, source_data, target_data))
            
            # 自定义验证规则
            for rule in dependency.validation_rules:
                rule_errors = self._validate_custom_rule(rule, source_data, target_data)
                errors.extend(rule_errors)
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return errors
    
    def _validate_field_mapping(self, dependency: DataDependency, 
                               source_data: TestDataset, 
                               target_data: TestDataset) -> List[str]:
        """验证字段映射"""
        errors = []
        
        source_fields = set()
        target_fields = set()
        
        if source_data.data:
            source_fields = set(source_data.data[0].keys())
        
        if target_data.data:
            target_fields = set(target_data.data[0].keys())
        
        for source_field, target_field in dependency.mapping.items():
            if source_field not in source_fields:
                errors.append(f"Source field '{source_field}' not found in {dependency.source_dataset}")
            
            if target_field not in target_fields:
                errors.append(f"Target field '{target_field}' not found in {dependency.target_dataset}")
        
        return errors
    
    def _validate_reference_integrity(self, dependency: DataDependency,
                                    source_data: TestDataset,
                                    target_data: TestDataset) -> List[str]:
        """验证引用完整性"""
        errors = []
        
        # 简化的引用完整性检查
        if "id" in dependency.mapping:
            source_id_field = dependency.mapping["id"]
            
            # 获取源数据集的所有ID
            source_ids = set()
            for record in source_data.data:
                if source_id_field in record:
                    source_ids.add(record[source_id_field])
            
            # 检查目标数据集中的引用
            missing_refs = []
            for record in target_data.data:
                for field, ref_field in dependency.mapping.items():
                    if ref_field in record:
                        ref_value = record[ref_field]
                        if ref_value not in source_ids:
                            missing_refs.append(f"Reference {ref_value} in field {ref_field} not found")
            
            if missing_refs:
                errors.extend(missing_refs[:10])  # 限制错误数量
                if len(missing_refs) > 10:
                    errors.append(f"... and {len(missing_refs) - 10} more reference errors")
        
        return errors
    
    def _validate_parent_child_relationship(self, dependency: DataDependency,
                                          source_data: TestDataset,
                                          target_data: TestDataset) -> List[str]:
        """验证父子关系"""
        errors = []
        
        # 检查父记录是否存在对应的子记录
        parent_id_field = dependency.mapping.get("parent_id", "id")
        child_parent_field = dependency.mapping.get("child_parent_id", "parent_id")
        
        parent_ids = set()
        for record in source_data.data:
            if parent_id_field in record:
                parent_ids.add(record[parent_id_field])
        
        # 检查孤儿记录
        orphaned_children = []
        for record in target_data.data:
            if child_parent_field in record:
                parent_ref = record[child_parent_field]
                if parent_ref and parent_ref not in parent_ids:
                    orphaned_children.append(parent_ref)
        
        if orphaned_children:
            errors.append(f"Found {len(orphaned_children)} orphaned child records")
        
        return errors
    
    def _validate_custom_rule(self, rule: str, source_data: TestDataset, 
                            target_data: TestDataset) -> List[str]:
        """验证自定义规则"""
        errors = []
        
        try:
            # 简化的规则解析器
            if rule.startswith("count_ratio"):
                # 例如: count_ratio:1:5 表示源数据集与目标数据集的记录比例应为1:5
                parts = rule.split(":")
                if len(parts) == 3:
                    expected_source_ratio = int(parts[1])
                    expected_target_ratio = int(parts[2])
                    
                    actual_source_count = len(source_data.data)
                    actual_target_count = len(target_data.data)
                    
                    if actual_source_count > 0:
                        actual_ratio = actual_target_count / actual_source_count
                        expected_ratio = expected_target_ratio / expected_source_ratio
                        
                        # 允许10%的误差
                        if abs(actual_ratio - expected_ratio) > expected_ratio * 0.1:
                            errors.append(f"Count ratio violation: expected {expected_ratio:.2f}, actual {actual_ratio:.2f}")
            
            elif rule.startswith("field_exists"):
                # 例如: field_exists:target:user_id 表示目标数据集必须有user_id字段
                parts = rule.split(":")
                if len(parts) == 3:
                    dataset_type, field_name = parts[1], parts[2]
                    
                    if dataset_type == "source" and source_data.data:
                        if field_name not in source_data.data[0]:
                            errors.append(f"Required field '{field_name}' missing in source dataset")
                    
                    elif dataset_type == "target" and target_data.data:
                        if field_name not in target_data.data[0]:
                            errors.append(f"Required field '{field_name}' missing in target dataset")
            
        except Exception as e:
            errors.append(f"Custom rule validation error: {str(e)}")
        
        return errors


class DependencyManager:
    """数据依赖关系管理器"""
    
    def __init__(self, dependency_file: str = "data_dependencies.json"):
        self.dependency_file = Path(dependency_file)
        self.logger = get_logger("phoenixframe.data.dependency")
        self.tracer = get_tracer("phoenixframe.data.dependency")
        self.validator = DependencyValidator()
        
        # 依赖关系图
        self._graph = self._load_dependency_graph()
        self._dataset_info: Dict[str, DatasetInfo] = {}
        
        # 线程锁
        self._lock = threading.Lock()
    
    def add_dependency(self, dependency: DataDependency) -> None:
        """添加依赖关系"""
        with self._lock:
            # 检查循环依赖
            if self._would_create_cycle(dependency):
                raise CircularDependencyError(
                    f"Adding dependency from {dependency.source_dataset} to {dependency.target_dataset} would create a cycle"
                )
            
            # 添加节点
            self._graph.nodes.add(dependency.source_dataset)
            self._graph.nodes.add(dependency.target_dataset)
            
            # 添加边（检查是否已存在）
            existing = next(
                (edge for edge in self._graph.edges 
                 if edge.source_dataset == dependency.source_dataset 
                 and edge.target_dataset == dependency.target_dataset), 
                None
            )
            
            if existing:
                # 更新现有依赖
                self._graph.edges.remove(existing)
            
            self._graph.edges.append(dependency)
            
            # 保存依赖图
            self._save_dependency_graph()
            
            self.logger.info(f"Added dependency: {dependency.source_dataset} -> {dependency.target_dataset}")
    
    def remove_dependency(self, source_dataset: str, target_dataset: str) -> bool:
        """删除依赖关系"""
        with self._lock:
            for edge in self._graph.edges:
                if edge.source_dataset == source_dataset and edge.target_dataset == target_dataset:
                    self._graph.edges.remove(edge)
                    self._save_dependency_graph()
                    
                    self.logger.info(f"Removed dependency: {source_dataset} -> {target_dataset}")
                    return True
            
            return False
    
    def get_dependencies(self, dataset_name: str) -> List[DataDependency]:
        """获取数据集的依赖关系"""
        dependencies = []
        
        for edge in self._graph.edges:
            if edge.target_dataset == dataset_name:
                dependencies.append(edge)
        
        return dependencies
    
    def get_dependents(self, dataset_name: str) -> List[DataDependency]:
        """获取依赖于该数据集的其他数据集"""
        dependents = []
        
        for edge in self._graph.edges:
            if edge.source_dataset == dataset_name:
                dependents.append(edge)
        
        return dependents
    
    def get_build_order(self, target_datasets: List[str] = None) -> List[str]:
        """获取数据集构建顺序（拓扑排序）"""
        if target_datasets is None:
            target_datasets = list(self._graph.nodes)
        
        # 构建邻接表
        graph = {node: [] for node in self._graph.nodes}
        in_degree = {node: 0 for node in self._graph.nodes}
        
        for edge in self._graph.edges:
            if edge.dependency_type in [DependencyType.REQUIRED, DependencyType.PARENT_CHILD]:
                graph[edge.source_dataset].append(edge.target_dataset)
                in_degree[edge.target_dataset] += 1
        
        # 拓扑排序（Kahn算法）
        queue = [node for node in target_datasets if in_degree[node] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0 and neighbor in target_datasets:
                    queue.append(neighbor)
        
        # 检查是否有循环依赖
        if len(result) != len(target_datasets):
            remaining = set(target_datasets) - set(result)
            raise CircularDependencyError(f"Circular dependency detected involving: {remaining}")
        
        return result
    
    def validate_dependencies(self, repository: DataRepository) -> Dict[str, List[str]]:
        """验证所有依赖关系"""
        validation_results = {}
        
        with self.tracer.trace_test_case("validate_all_dependencies", "", "running"):
            for edge in self._graph.edges:
                try:
                    # 加载数据集
                    source_dataset = repository.load_dataset(edge.source_dataset)
                    target_dataset = repository.load_dataset(edge.target_dataset)
                    
                    # 验证依赖关系
                    errors = self.validator.validate_dependency(edge, source_dataset, target_dataset)
                    
                    if errors:
                        validation_results[f"{edge.source_dataset} -> {edge.target_dataset}"] = errors
                    
                except Exception as e:
                    validation_results[f"{edge.source_dataset} -> {edge.target_dataset}"] = [str(e)]
        
        return validation_results
    
    def get_dependency_tree(self, dataset_name: str, max_depth: int = 5) -> Dict[str, Any]:
        """获取依赖树"""
        def build_tree(node: str, depth: int) -> Dict[str, Any]:
            if depth >= max_depth:
                return {"name": node, "dependencies": [], "truncated": True}
            
            dependencies = []
            for edge in self._graph.edges:
                if edge.target_dataset == node:
                    dep_tree = build_tree(edge.source_dataset, depth + 1)
                    dep_tree["dependency_type"] = edge.dependency_type.value
                    dep_tree["description"] = edge.description
                    dependencies.append(dep_tree)
            
            return {
                "name": node,
                "dependencies": dependencies,
                "depth": depth
            }
        
        return build_tree(dataset_name, 0)
    
    def get_impact_analysis(self, dataset_name: str) -> Dict[str, Any]:
        """获取影响分析"""
        direct_dependents = self.get_dependents(dataset_name)
        
        # 递归获取所有受影响的数据集
        affected_datasets = set()
        
        def collect_affected(node: str, visited: Set[str]):
            if node in visited:
                return
            
            visited.add(node)
            affected_datasets.add(node)
            
            for edge in self._graph.edges:
                if edge.source_dataset == node:
                    collect_affected(edge.target_dataset, visited)
        
        for edge in direct_dependents:
            collect_affected(edge.target_dataset, set())
        
        affected_datasets.discard(dataset_name)  # 移除自身
        
        return {
            "dataset": dataset_name,
            "direct_dependents": len(direct_dependents),
            "total_affected": len(affected_datasets),
            "affected_datasets": list(affected_datasets),
            "impact_level": self._calculate_impact_level(len(affected_datasets))
        }
    
    def create_subset_graph(self, dataset_names: List[str]) -> DependencyGraph:
        """创建子图"""
        subset_nodes = set(dataset_names)
        subset_edges = [
            edge for edge in self._graph.edges
            if edge.source_dataset in subset_nodes and edge.target_dataset in subset_nodes
        ]
        
        return DependencyGraph(
            nodes=subset_nodes,
            edges=subset_edges,
            metadata={"type": "subset", "parent_graph": "main"}
        )
    
    def export_graph(self, output_file: str, format: str = "json") -> None:
        """导出依赖图"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "json":
            graph_data = {
                "nodes": list(self._graph.nodes),
                "edges": [
                    {
                        "source": edge.source_dataset,
                        "target": edge.target_dataset,
                        "type": edge.dependency_type.value,
                        "description": edge.description,
                        "constraint": edge.constraint,
                        "mapping": edge.mapping,
                        "validation_rules": edge.validation_rules,
                        "metadata": edge.metadata,
                        "created_at": edge.created_at.isoformat()
                    }
                    for edge in self._graph.edges
                ],
                "metadata": self._graph.metadata
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
        elif format.lower() == "dot":
            # Graphviz DOT格式
            dot_content = ["digraph DataDependencies {"]
            dot_content.append("  rankdir=TB;")
            dot_content.append("  node [shape=box];")
            
            for node in self._graph.nodes:
                dot_content.append(f'  "{node}";')
            
            for edge in self._graph.edges:
                style = self._get_edge_style(edge.dependency_type)
                dot_content.append(f'  "{edge.source_dataset}" -> "{edge.target_dataset}" [label="{edge.dependency_type.value}" {style}];')
            
            dot_content.append("}")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(dot_content))
        
        self.logger.info(f"Exported dependency graph to {output_file}")
    
    def _would_create_cycle(self, new_dependency: DataDependency) -> bool:
        """检查添加新依赖是否会创建循环"""
        # 临时添加新边
        temp_edges = self._graph.edges + [new_dependency]
        
        # 构建图
        graph = {}
        for edge in temp_edges:
            if edge.source_dataset not in graph:
                graph[edge.source_dataset] = []
            graph[edge.source_dataset].append(edge.target_dataset)
        
        # DFS检测循环
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    return True
        
        return False
    
    def _calculate_impact_level(self, affected_count: int) -> str:
        """计算影响级别"""
        if affected_count == 0:
            return "none"
        elif affected_count <= 2:
            return "low"
        elif affected_count <= 5:
            return "medium"
        elif affected_count <= 10:
            return "high"
        else:
            return "critical"
    
    def _get_edge_style(self, dependency_type: DependencyType) -> str:
        """获取边的样式"""
        styles = {
            DependencyType.REQUIRED: 'style=solid, color=red',
            DependencyType.OPTIONAL: 'style=dashed, color=blue',
            DependencyType.REFERENCE: 'style=dotted, color=green',
            DependencyType.PARENT_CHILD: 'style=bold, color=purple',
            DependencyType.SEQUENTIAL: 'style=solid, color=orange'
        }
        return styles.get(dependency_type, 'style=solid, color=black')
    
    def _load_dependency_graph(self) -> DependencyGraph:
        """加载依赖图"""
        if not self.dependency_file.exists():
            return DependencyGraph()
        
        try:
            with open(self.dependency_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            nodes = set(data.get("nodes", []))
            edges = []
            
            for edge_data in data.get("edges", []):
                edge = DataDependency(
                    source_dataset=edge_data["source"],
                    target_dataset=edge_data["target"],
                    dependency_type=DependencyType(edge_data["type"]),
                    description=edge_data.get("description", ""),
                    constraint=edge_data.get("constraint"),
                    mapping=edge_data.get("mapping", {}),
                    validation_rules=edge_data.get("validation_rules", []),
                    metadata=edge_data.get("metadata", {}),
                    created_at=datetime.fromisoformat(edge_data["created_at"]) if "created_at" in edge_data else datetime.now()
                )
                edges.append(edge)
            
            return DependencyGraph(
                nodes=nodes,
                edges=edges,
                metadata=data.get("metadata", {})
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load dependency graph: {e}")
            return DependencyGraph()
    
    def _save_dependency_graph(self) -> None:
        """保存依赖图"""
        graph_data = {
            "nodes": list(self._graph.nodes),
            "edges": [
                {
                    "source": edge.source_dataset,
                    "target": edge.target_dataset,
                    "type": edge.dependency_type.value,
                    "description": edge.description,
                    "constraint": edge.constraint,
                    "mapping": edge.mapping,
                    "validation_rules": edge.validation_rules,
                    "metadata": edge.metadata,
                    "created_at": edge.created_at.isoformat()
                }
                for edge in self._graph.edges
            ],
            "metadata": self._graph.metadata
        }
        
        # 确保目标目录存在
        self.dependency_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.dependency_file, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)


# 全局实例
_dependency_manager: Optional[DependencyManager] = None


def get_dependency_manager(dependency_file: str = "data_dependencies.json") -> DependencyManager:
    """获取依赖关系管理器实例"""
    global _dependency_manager
    if _dependency_manager is None:
        _dependency_manager = DependencyManager(dependency_file)
    return _dependency_manager


__all__ = [
    "DependencyType",
    "DataDependency",
    "DependencyGraph",
    "DatasetInfo",
    "CircularDependencyError",
    "DependencyValidator",
    "DependencyManager",
    "get_dependency_manager"
]