"""数据库数据准备和清理模块"""
import sqlite3
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime
import threading
import uuid

try:
    import sqlalchemy
    from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, Boolean, DateTime, Text, inspect
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.sql import text
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    sqlalchemy = None
    Base = None

from . import TestDataset
from ..observability.logger import get_logger
from ..observability.tracer import get_tracer


@dataclass
class DatabaseConnection:
    """数据库连接配置"""
    name: str
    connection_string: str
    driver: str = "sqlite"  # sqlite, mysql, postgresql, oracle
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableSetup:
    """表设置配置"""
    table_name: str
    schema: Dict[str, Any]
    data: List[Dict[str, Any]] = field(default_factory=list)
    primary_key: str = "id"
    foreign_keys: Dict[str, str] = field(default_factory=dict)
    indexes: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


@dataclass
class DataSetupPlan:
    """数据设置计划"""
    name: str
    description: str
    connections: List[DatabaseConnection]
    tables: List[TableSetup]
    setup_order: List[str] = field(default_factory=list)
    cleanup_order: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.logger = get_logger("phoenixframe.data.database")
        self.tracer = get_tracer("phoenixframe.data.database")
        self._connections: Dict[str, Any] = {}
        self._sessions: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def add_connection(self, connection: DatabaseConnection) -> None:
        """添加数据库连接"""
        with self._lock:
            if not SQLALCHEMY_AVAILABLE and connection.driver != "sqlite":
                raise ImportError("SQLAlchemy required for non-SQLite databases. Install with: pip install sqlalchemy")
            
            try:
                if connection.driver == "sqlite":
                    # SQLite连接
                    engine = create_engine(
                        connection.connection_string,
                        echo=False,
                        **connection.options
                    ) if SQLALCHEMY_AVAILABLE else None
                    
                    # 原生SQLite连接作为备选
                    native_conn = sqlite3.connect(connection.connection_string.replace("sqlite:///", ""))
                    
                    self._connections[connection.name] = {
                        "engine": engine,
                        "native": native_conn,
                        "config": connection
                    }
                else:
                    # 其他数据库需要SQLAlchemy
                    if not SQLALCHEMY_AVAILABLE:
                        raise ImportError(f"SQLAlchemy required for {connection.driver}")
                    
                    engine = create_engine(
                        connection.connection_string,
                        echo=False,
                        **connection.options
                    )
                    
                    self._connections[connection.name] = {
                        "engine": engine,
                        "native": None,
                        "config": connection
                    }
                
                # 创建session工厂
                if SQLALCHEMY_AVAILABLE and self._connections[connection.name]["engine"]:
                    session_factory = sessionmaker(bind=self._connections[connection.name]["engine"])
                    self._sessions[connection.name] = session_factory
                
                self.logger.info(f"Added database connection: {connection.name}")
                
            except Exception as e:
                self.logger.error(f"Failed to add connection {connection.name}: {e}")
                raise
    
    @contextmanager
    def get_session(self, connection_name: str):
        """获取数据库会话"""
        if connection_name not in self._connections:
            raise ValueError(f"Connection {connection_name} not found")
        
        if SQLALCHEMY_AVAILABLE and connection_name in self._sessions:
            session = self._sessions[connection_name]()
            try:
                yield session
                session.commit()
            except Exception as e:
                session.rollback()
                self.logger.error(f"Database session error: {e}")
                raise
            finally:
                session.close()
        else:
            # 使用原生连接
            conn = self._connections[connection_name]["native"]
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Database connection error: {e}")
                raise
    
    @contextmanager
    def get_connection(self, connection_name: str):
        """获取原始数据库连接"""
        if connection_name not in self._connections:
            raise ValueError(f"Connection {connection_name} not found")
        
        conn_info = self._connections[connection_name]
        
        if SQLALCHEMY_AVAILABLE and conn_info["engine"]:
            with conn_info["engine"].connect() as conn:
                yield conn
        elif conn_info["native"]:
            yield conn_info["native"]
        else:
            raise RuntimeError(f"No available connection for {connection_name}")
    
    def execute_sql(self, connection_name: str, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """执行SQL语句"""
        with self.tracer.trace_test_case(f"execute_sql_{connection_name}", "", "running"):
            try:
                with self.get_connection(connection_name) as conn:
                    if SQLALCHEMY_AVAILABLE and hasattr(conn, 'execute'):
                        # SQLAlchemy连接
                        if params:
                            result = conn.execute(text(sql), params)
                        else:
                            result = conn.execute(text(sql))
                        
                        # 尝试获取结果
                        try:
                            return result.fetchall()
                        except:
                            return result.rowcount
                    else:
                        # 原生SQLite连接
                        cursor = conn.cursor()
                        if params:
                            cursor.execute(sql, params)
                        else:
                            cursor.execute(sql)
                        
                        try:
                            return cursor.fetchall()
                        except:
                            return cursor.rowcount
                        
            except Exception as e:
                self.logger.error(f"SQL execution failed: {e}")
                raise
    
    def create_table(self, connection_name: str, table_setup: TableSetup) -> None:
        """创建表"""
        with self.tracer.trace_test_case(f"create_table_{table_setup.table_name}", "", "running"):
            try:
                # 生成CREATE TABLE语句
                create_sql = self._generate_create_table_sql(table_setup)
                
                self.logger.info(f"Creating table {table_setup.table_name}")
                self.execute_sql(connection_name, create_sql)
                
                # 创建索引
                for index_column in table_setup.indexes:
                    index_sql = f"CREATE INDEX idx_{table_setup.table_name}_{index_column} ON {table_setup.table_name} ({index_column})"
                    self.execute_sql(connection_name, index_sql)
                
                self.logger.info(f"Table {table_setup.table_name} created successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to create table {table_setup.table_name}: {e}")
                raise
    
    def insert_data(self, connection_name: str, table_name: str, data: List[Dict[str, Any]]) -> int:
        """插入数据"""
        if not data:
            return 0
        
        with self.tracer.trace_test_case(f"insert_data_{table_name}", "", "running"):
            try:
                # 生成INSERT语句
                columns = list(data[0].keys())
                placeholders = ", ".join([f":{col}" for col in columns])
                insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                
                inserted_count = 0
                
                with self.get_session(connection_name) as session:
                    for record in data:
                        if SQLALCHEMY_AVAILABLE and hasattr(session, 'execute'):
                            session.execute(text(insert_sql), record)
                        else:
                            # 原生SQLite
                            placeholders_native = ", ".join(["?" for _ in columns])
                            insert_sql_native = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders_native})"
                            values = [record.get(col) for col in columns]
                            session.execute(insert_sql_native, values)
                        
                        inserted_count += 1
                
                self.logger.info(f"Inserted {inserted_count} records into {table_name}")
                return inserted_count
                
            except Exception as e:
                self.logger.error(f"Failed to insert data into {table_name}: {e}")
                raise
    
    def clear_table(self, connection_name: str, table_name: str) -> int:
        """清空表数据"""
        with self.tracer.trace_test_case(f"clear_table_{table_name}", "", "running"):
            try:
                delete_sql = f"DELETE FROM {table_name}"
                result = self.execute_sql(connection_name, delete_sql)
                
                deleted_count = result if isinstance(result, int) else 0
                self.logger.info(f"Cleared {deleted_count} records from {table_name}")
                return deleted_count
                
            except Exception as e:
                self.logger.error(f"Failed to clear table {table_name}: {e}")
                raise
    
    def drop_table(self, connection_name: str, table_name: str) -> None:
        """删除表"""
        with self.tracer.trace_test_case(f"drop_table_{table_name}", "", "running"):
            try:
                drop_sql = f"DROP TABLE IF EXISTS {table_name}"
                self.execute_sql(connection_name, drop_sql)
                
                self.logger.info(f"Dropped table {table_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to drop table {table_name}: {e}")
                raise
    
    def table_exists(self, connection_name: str, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            if connection_name not in self._connections:
                return False
            
            conn_info = self._connections[connection_name]
            
            if SQLALCHEMY_AVAILABLE and conn_info["engine"]:
                inspector = inspect(conn_info["engine"])
                return table_name in inspector.get_table_names()
            else:
                # SQLite原生检查
                check_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
                with self.get_connection(connection_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute(check_sql, (table_name,))
                    return cursor.fetchone() is not None
                    
        except Exception as e:
            self.logger.error(f"Failed to check if table {table_name} exists: {e}")
            return False
    
    def _generate_create_table_sql(self, table_setup: TableSetup) -> str:
        """生成CREATE TABLE SQL语句"""
        columns = []
        
        for column_name, column_info in table_setup.schema.items():
            column_type = self._map_type_to_sql(column_info.get("type", "string"))
            column_def = f"{column_name} {column_type}"
            
            # 主键
            if column_name == table_setup.primary_key:
                column_def += " PRIMARY KEY"
            
            # 非空约束
            if column_info.get("required", False):
                column_def += " NOT NULL"
            
            # 默认值
            if "default" in column_info:
                default_value = column_info["default"]
                if isinstance(default_value, str):
                    column_def += f" DEFAULT '{default_value}'"
                else:
                    column_def += f" DEFAULT {default_value}"
            
            columns.append(column_def)
        
        # 外键约束
        for fk_column, ref_table in table_setup.foreign_keys.items():
            columns.append(f"FOREIGN KEY ({fk_column}) REFERENCES {ref_table}(id)")
        
        # 使用三引号构建多行SQL，避免反斜杠转义问题
        create_sql = (
            "CREATE TABLE IF NOT EXISTS "
            f"{table_setup.table_name} (\n  " + ",\n  ".join(columns) + "\n)"
        )
        return create_sql
    
    def _map_type_to_sql(self, data_type: str) -> str:
        """映射数据类型到SQL类型"""
        type_mapping = {
            "string": "TEXT",
            "integer": "INTEGER", 
            "float": "REAL",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "datetime": "DATETIME",
            "uuid": "TEXT",
            "json": "TEXT"
        }
        return type_mapping.get(data_type, "TEXT")
    
    def close_all_connections(self) -> None:
        """关闭所有连接"""
        with self._lock:
            for name, conn_info in self._connections.items():
                try:
                    if conn_info["native"]:
                        conn_info["native"].close()
                    if SQLALCHEMY_AVAILABLE and conn_info["engine"]:
                        conn_info["engine"].dispose()
                    self.logger.info(f"Closed connection: {name}")
                except Exception as e:
                    self.logger.error(f"Error closing connection {name}: {e}")
            
            self._connections.clear()
            self._sessions.clear()


class DataSetupManager:
    """数据设置管理器"""
    
    def __init__(self):
        self.logger = get_logger("phoenixframe.data.setup")
        self.tracer = get_tracer("phoenixframe.data.setup")
        self.db_manager = DatabaseManager()
        self._setup_plans: Dict[str, DataSetupPlan] = {}
    
    def load_setup_plan(self, plan_file: str) -> DataSetupPlan:
        """从文件加载设置计划"""
        plan_path = Path(plan_file)
        
        if not plan_path.exists():
            raise FileNotFoundError(f"Setup plan file not found: {plan_file}")
        
        try:
            with open(plan_path, 'r', encoding='utf-8') as f:
                if plan_path.suffix.lower() == '.yaml' or plan_path.suffix.lower() == '.yml':
                    plan_data = yaml.safe_load(f)
                else:
                    plan_data = json.load(f)
            
            # 解析连接配置
            connections = []
            for conn_data in plan_data.get("connections", []):
                connection = DatabaseConnection(**conn_data)
                connections.append(connection)
            
            # 解析表配置
            tables = []
            for table_data in plan_data.get("tables", []):
                table_setup = TableSetup(**table_data)
                tables.append(table_setup)
            
            plan = DataSetupPlan(
                name=plan_data["name"],
                description=plan_data.get("description", ""),
                connections=connections,
                tables=tables,
                setup_order=plan_data.get("setup_order", []),
                cleanup_order=plan_data.get("cleanup_order", []),
                dependencies=plan_data.get("dependencies", {})
            )
            
            self._setup_plans[plan.name] = plan
            self.logger.info(f"Loaded setup plan: {plan.name}")
            return plan
            
        except Exception as e:
            self.logger.error(f"Failed to load setup plan {plan_file}: {e}")
            raise
    
    def execute_setup_plan(self, plan_name: str) -> None:
        """执行设置计划"""
        if plan_name not in self._setup_plans:
            raise ValueError(f"Setup plan {plan_name} not found")
        
        plan = self._setup_plans[plan_name]
        
        with self.tracer.trace_test_case(f"execute_setup_plan_{plan_name}", "", "running"):
            try:
                self.logger.info(f"Executing setup plan: {plan_name}")
                
                # 添加数据库连接
                for connection in plan.connections:
                    self.db_manager.add_connection(connection)
                
                # 按依赖顺序设置表
                setup_order = plan.setup_order if plan.setup_order else [table.table_name for table in plan.tables]
                
                for table_name in setup_order:
                    table_setup = next((t for t in plan.tables if t.table_name == table_name), None)
                    if not table_setup:
                        self.logger.warning(f"Table setup not found for: {table_name}")
                        continue
                    
                    # 使用第一个连接作为默认连接
                    connection_name = plan.connections[0].name if plan.connections else "default"
                    
                    # 创建表
                    self.db_manager.create_table(connection_name, table_setup)
                    
                    # 插入数据
                    if table_setup.data:
                        self.db_manager.insert_data(connection_name, table_setup.table_name, table_setup.data)
                
                self.logger.info(f"Setup plan {plan_name} executed successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to execute setup plan {plan_name}: {e}")
                raise
    
    def cleanup_setup_plan(self, plan_name: str) -> None:
        """清理设置计划"""
        if plan_name not in self._setup_plans:
            raise ValueError(f"Setup plan {plan_name} not found")
        
        plan = self._setup_plans[plan_name]
        
        with self.tracer.trace_test_case(f"cleanup_setup_plan_{plan_name}", "", "running"):
            try:
                self.logger.info(f"Cleaning up setup plan: {plan_name}")
                
                # 按清理顺序清理表（通常与设置顺序相反）
                cleanup_order = plan.cleanup_order if plan.cleanup_order else list(reversed([table.table_name for table in plan.tables]))
                connection_name = plan.connections[0].name if plan.connections else "default"
                
                for table_name in cleanup_order:
                    try:
                        self.db_manager.clear_table(connection_name, table_name)
                    except Exception as e:
                        self.logger.warning(f"Failed to clear table {table_name}: {e}")
                
                self.logger.info(f"Setup plan {plan_name} cleaned up successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to cleanup setup plan {plan_name}: {e}")
                raise
    
    def create_setup_plan_template(self, output_file: str) -> None:
        """创建设置计划模板"""
        template = {
            "name": "sample_data_setup",
            "description": "Sample data setup plan",
            "connections": [
                {
                    "name": "test_db",
                    "connection_string": "sqlite:///test_data.db",
                    "driver": "sqlite"
                }
            ],
            "tables": [
                {
                    "table_name": "users",
                    "schema": {
                        "id": {"type": "uuid", "required": True},
                        "username": {"type": "string", "required": True},
                        "email": {"type": "string", "required": True},
                        "created_at": {"type": "datetime", "default": "CURRENT_TIMESTAMP"}
                    },
                    "data": [
                        {
                            "id": "user-1",
                            "username": "testuser1",
                            "email": "test1@example.com"
                        }
                    ],
                    "primary_key": "id",
                    "indexes": ["username", "email"]
                },
                {
                    "table_name": "products", 
                    "schema": {
                        "id": {"type": "uuid", "required": True},
                        "name": {"type": "string", "required": True},
                        "price": {"type": "float", "required": True},
                        "stock": {"type": "integer", "default": 0}
                    },
                    "data": [],
                    "primary_key": "id"
                }
            ],
            "setup_order": ["users", "products"],
            "cleanup_order": ["products", "users"],
            "dependencies": {
                "products": ["users"]
            }
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if output_path.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(template, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(template, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Created setup plan template: {output_file}")


# 全局实例
_database_manager: Optional[DatabaseManager] = None
_setup_manager: Optional[DataSetupManager] = None


def get_database_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager


def get_setup_manager() -> DataSetupManager:
    """获取数据设置管理器实例"""
    global _setup_manager
    if _setup_manager is None:
        _setup_manager = DataSetupManager()
    return _setup_manager


__all__ = [
    "DatabaseConnection",
    "TableSetup",
    "DataSetupPlan",
    "DatabaseManager",
    "DataSetupManager",
    "get_database_manager",
    "get_setup_manager",
    "SQLALCHEMY_AVAILABLE"
]