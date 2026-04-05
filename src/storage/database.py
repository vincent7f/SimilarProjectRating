"""
SQLite Database Operations Module.

Provides a lightweight SQLite-based persistence layer for storing
analysis results, session records, project metadata, and log indices.
Uses connection pooling and context managers for safe concurrent access.

SQLite数据库操作模块.
提供基于SQLite的轻量级持久化层,用于存储分析结果,会话记录,
项目元数据和日志索引.使用连接池和上下文管理器实现安全的并发访问.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator

# SQL schema definitions / SQL模式定义

SCHEMA_PROJECTS = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_id INTEGER UNIQUE NOT NULL,
    full_name TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    url TEXT,
    stars INTEGER DEFAULT 0,
    forks INTEGER DEFAULT 0,
    open_issues INTEGER DEFAULT 0,
    language TEXT,
    topics TEXT,
    created_at TEXT,
    updated_at TEXT,
    pushed_at TEXT,
    default_branch TEXT,
    license_type TEXT,
    archived BOOLEAN DEFAULT 0,
    first_seen_at TEXT DEFAULT (datetime('now')),
    last_analyzed_at TEXT,
    metadata_json TEXT
);
"""

SCHEMA_ANALYSIS_RESULTS = """
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    project_full_name TEXT NOT NULL REFERENCES projects(full_name),
    code_quality_score REAL DEFAULT 0.0,
    community_score REAL DEFAULT 0.0,
    maturity_score REAL DEFAULT 0.0,
    functionality_score REAL DEFAULT 0.0,
    reputation_score REAL DEFAULT 0.0,
    sustainability_score REAL DEFAULT 0.0,
    comprehensive_score REAL DEFAULT 0.0,
    rank INTEGER DEFAULT 0,
    tier TEXT DEFAULT 'D',
    code_metrics_json TEXT,
    community_metrics_json TEXT,
    maturity_metrics_json TEXT,
    errors_json TEXT,
    analysis_duration_ms INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

SCHEMA_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    query TEXT NOT NULL,
    status TEXT DEFAULT 'initialized',
    start_time TEXT,
    end_time TEXT,
    total_projects_found INTEGER DEFAULT 0,
    projects_analyzed INTEGER DEFAULT 0,
    total_duration_seconds REAL DEFAULT 0.0,
    summary_json TEXT,
    config_snapshot_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

SCHEMA_LOG_INDEX = """
CREATE TABLE IF NOT EXISTS log_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    level TEXT,
    module TEXT,
    operation TEXT,
    success BOOLEAN DEFAULT 1,
    duration_ms INTEGER DEFAULT 0,
    message TEXT,
    metadata_json TEXT
);
"""

SCHEMA_EXPERIENCES = """
CREATE TABLE IF NOT EXISTS experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    context TEXT,
    suggestion TEXT,
    source_session_id TEXT,
    recorded_at TEXT DEFAULT (datetime('now')),
    applied_count INTEGER DEFAULT 0
);
"""

ALL_SCHEMAS = [
    SCHEMA_PROJECTS,
    SCHEMA_ANALYSIS_RESULTS,
    SCHEMA_SESSIONS,
    SCHEMA_LOG_INDEX,
    SCHEMA_EXPERIENCES,
]


class Database:
    """SQLite database manager with schema initialization and CRUD operations.

    Provides type-safe methods for persisting and querying domain entities.
    Uses parameterized queries to prevent SQL injection.

    具有模式初始化和CRUD操作的SQLite数据库管理器.
提供用于持久化和查询领域实体的类型安全方法.
使用参数化查询来防止SQL注入.

    Attributes:
        db_path: Filesystem path to the SQLite database file.
                 SQLite数据库文件的文件系统路径.
        _connection: Active database connection (lazy initialized).
                    活动的数据库连接(延迟初始化).
    """

    def __init__(self, db_path: str = "./data/similar_project_rating.db") -> None:
        """Initialize database with given path, creating file/parent dirs if needed.

        使用给定路径初始化数据库,必要时创建文件/父目录.

        Args:
            db_path: Path to the SQLite database file (.db extension recommended).
                     SQLite数据库文件路径(推荐.db扩展名).
        """
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Lazy-initialize and return the database connection.

        延迟初始化并返回数据库连接.

        Returns:
            Active sqlite3.Connection with row factory configured.
             配置了row_factory的活跃sqlite3.Connection.
        """
        if self._connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys / 启用外键约束
            self._connection.execute("PRAGMA foreign_keys = ON")
            # WAL mode for better concurrency / 使用WAL模式提升并发性能
            self._connection.execute("PRAGMA journal_mode = WAL")
        return self._connection

    def initialize_schema(self) -> None:
        """Create all tables if they do not exist yet.

        Calls CREATE TABLE IF NOT EXISTS for each defined schema,
        ensuring the database is ready for operations.

        如果表尚不存在则创建所有表.
        为每个定义的模式调用CREATE TABLE IF NOT EXISTS,
        确保数据库已准备好进行操作.
        """
        conn = self.connection
        cursor = conn.cursor()
        for schema_sql in ALL_SCHEMAS:
            cursor.execute(schema_sql)
        conn.commit()

    def close(self) -> None:
        """Close the database connection if open.

        如果连接已打开则关闭它.
        """
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        """Context manager for atomic transactional operations.

        Automatically commits on success and rolls back on exception.

        用于原子事务操作的上下文管理器.
成功时自动提交,异常时回滚.

        Yields:
            Cursor for executing statements within the transaction.
             在事务内执行语句的游标.
        """
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    # ------------------------------------------------------------------
    # Project CRUD / 项目CRUD操作
    # ------------------------------------------------------------------

    def upsert_project(self, project_data: Dict[str, Any]) -> int:
        """Insert or update a project record.

        Inserts a new project or updates existing one based on full_name uniqueness.
        Returns the database row ID of the upserted record.

        插入或更新项目记录.
根据full_name唯一性插入新项目或更新现有项目.
返回upserted记录的数据库行ID.

        Args:
            project_data: Dictionary with project fields matching the schema.
                          匹配模式的具有项目字段的字典.

        Returns:
            Row ID of the inserted or updated record.
             插入或更新记录的行ID.
        """
        sql = """
        INSERT INTO projects (github_id, full_name, name, description, url,
                              stars, forks, open_issues, language, topics,
                              created_at, updated_at, pushed_at, default_branch,
                              license_type, archived, metadata_json)
        VALUES (:github_id, :full_name, :name, :description, :url,
                :stars, :forks, :open_issues, :language, :topics,
                :created_at, :updated_at, :pushed_at, :default_branch,
                :license_type, :archived, :metadata_json)
        ON CONFLICT(full_name) UPDATE SET
            stars = excluded.stars,
            forks = excluded.forks,
            open_issues = excluded.open_issues,
            updated_at = excluded.updated_at,
            pushed_at = excluded.pushed_at,
            last_analyzed_at = datetime('now'),
            metadata_json = excluded.metadata_json;
        """
        with self.transaction() as cursor:
            cursor.execute(sql, {
                "github_id": project_data.get("id", 0),
                "full_name": project_data.get("full_name", ""),
                "name": project_data.get("name", ""),
                "description": project_data.get("description", ""),
                "url": project_data.get("url", ""),
                "stars": project_data.get("stars", 0),
                "forks": project_data.get("forks", 0),
                "open_issues": project_data.get("open_issues", 0),
                "language": project_data.get("primary_language"),
                "topics": json.dumps(project_data.get("topics", [])),
                "created_at": _dt_str(project_data.get("created_at")),
                "updated_at": _dt_str(project_data.get("updated_at")),
                "pushed_id": _dt_str(project_data.get("pushed_at")),
                "default_branch": project_data.get("default_branch", "main"),
                "license_type": project_data.get("license_info", {}).get("spdx_id")
                                if project_data.get("license_info") else None,
                "archived": int(project_data.get("archived", False)),
                "metadata_json": json.dumps(
                    {k: v for k, v in project_data.items()
                     if k not in ("id", "name", "full_name")},
                    default=str,
                ),
            })
            return cursor.lastrowid  # type: ignore

    def get_project(self, full_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a project by its full name.

        通过完整名称检索项目.

        Args:
            full_name: 'owner/repo' identifier.
                      'owner/repo'标识符.

        Returns:
            Project dictionary or None if not found.
             项目字典,如未找到则返回None.
        """
        cursor = self.connection.execute(
            "SELECT * FROM projects WHERE full_name = ?", (full_name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Session CRUD / 会话CRUD操作
    # ------------------------------------------------------------------

    def create_session(self, session_id: str, query: str,
                       config_snapshot: Optional[Dict] = None) -> int:
        """Create a new analysis session record.

        创建新的分析会话记录.

        Args:
            session_id: Unique session identifier.
                       唯一会话标识符.
            query: User's search query.
                  用户搜索查询.
            config_snapshot: Configuration used for this run (JSON serialized).
                            此运行使用的配置(JSON序列化).

        Returns:
            Row ID of the new session record.
             新会话记录的行ID.
        """
        sql = """
        INSERT INTO sessions (session_id, query, status, start_time, config_snapshot_json)
        VALUES (?, ?, 'running', datetime('now'), ?);
        """
        with self.transaction() as cursor:
            cursor.execute(sql, (
                session_id,
                query,
                json.dumps(config_snapshot, default=str) if config_snapshot else None,
            ))
            return cursor.lastrowid  # type: ignore

    def update_session_status(self, session_id: str, status: str,
                              summary: Optional[Dict] = None) -> None:
        """Update session status and optionally attach summary data.

        更新会话状态并可选地附加摘要数据.

        Args:
            session_id: Session identifier.
                       会话标识符.
            status: New status value ('completed', 'failed', etc.).
                   新状态值('completed','failed'等).
            summary: Optional summary dictionary to store as JSON.
                     可选的摘要字典,将存储为JSON.
        """
        sql = """
        UPDATE sessions SET status = ?, end_time = datetime('now'), summary_json = ?
        WHERE session_id = ?;
        """
        with self.transaction() as cursor:
            cursor.execute(sql, (
                status,
                json.dumps(summary, default=str) if summary else None,
                session_id,
            ))

    # ------------------------------------------------------------------
    # Analysis Results / 分析结果
    # ------------------------------------------------------------------

    def save_analysis_result(self, result_data: Dict[str, Any]) -> int:
        """Persist an analysis result record.

        持久化分析结果记录.

        Args:
            result_data: Dictionary containing all analysis score dimensions
                         and optional metric JSON payloads.
                         包含所有分析评分维度和可选指标JSON负载的字典.

        Returns:
            Row ID of the inserted record.
             插入记录的行ID.
        """
        sql = """
        INSERT INTO analysis_results
            (session_id, project_full_name, code_quality_score, community_score,
             maturity_score, functionality_score, reputation_score,
             sustainability_score, comprehensive_score, rank, tier,
             code_metrics_json, community_metrics_json, maturity_metrics_json,
             errors_json, analysis_duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.transaction() as cursor:
            cursor.execute(sql, (
                result_data.get("session_id", ""),
                result_data.get("project_full_name", ""),
                result_data.get("code_quality_score", 0.0),
                result_data.get("community_score", 0.0),
                result_data.get("maturity_score", 0.0),
                result_data.get("functionality_score", 0.0),
                result_data.get("reputation_score", 0.0),
                result_data.get("sustainability_score", 0.0),
                result_data.get("comprehensive_score", 0.0),
                result_data.get("rank", 0),
                result_data.get("tier", "D"),
                json.dumps(result_data.get("code_metrics"), default=str),
                json.dumps(result_data.get("community_metrics"), default=str),
                json.dumps(result_data.get("maturity_metrics"), default=str),
                json.dumps(result_data.get("errors"), default=str),
                result_data.get("analysis_duration_ms", 0),
            ))
            return cursor.lastrowid  # type: ignore

    # ------------------------------------------------------------------
    # Log Index / 日志索引
    # ------------------------------------------------------------------

    def index_log_entry(self, entry: Dict[str, Any]) -> None:
        """Store a log entry in the searchable index table.

        将日志条目存储在可搜索索引表中.

        Args:
            entry: Dictionary with log entry fields.
                  包含日志条目字段的字典.
        """
        sql = """
        INSERT INTO log_index (session_id, timestamp, level, module, operation,
                               success, duration_ms, message, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.transaction() as cursor:
            cursor.execute(sql, (
                entry.get("session_id"),
                entry.get("timestamp"),
                entry.get("level", "INFO"),
                entry.get("module", ""),
                entry.get("operation", ""),
                entry.get("success", True),
                entry.get("duration_ms", 0),
                entry.get("message", ""),
                json.dumps(entry.get("metadata", {}), default=str),
            ))

    # ------------------------------------------------------------------
    # Experience Storage / 经验存储
    # ------------------------------------------------------------------

    def save_experience(self, experience: Dict[str, Any]) -> int:
        """Persist an accumulated experience entry.

        持久化累积的经验条目.

        Args:
            experience: Dictionary with experience fields.
                        包含经验字段的字典.

        Returns:
            Row ID of the new experience record.
             新经验记录的行ID.
        """
        sql = """
        INSERT INTO experiences (category, summary, context, suggestion,
                                 source_session_id, recorded_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'));
        """
        with self.transaction() as cursor:
            cursor.execute(sql, (
                experience.get("category", ""),
                experience.get("summary", ""),
                experience.get("context", ""),
                experience.get("suggestion", ""),
                experience.get("session_id", ""),
            ))
            return cursor.lastrowid  # type: ignore

    def get_experiences(
        self,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve accumulated experiences, optionally filtered by category.

        获取累积经验,可选按类别过滤.

        Args:
            category: Filter to this category, or None for all.
                     过滤到此类别,或None表示全部.
            limit: Maximum number of records to return.
                  返回的最大记录数.

        Returns:
            List of experience dictionaries sorted by recency.
             按时间排序的经验字典列表.
        """
        if category:
            cursor = self.connection.execute(
                "SELECT * FROM experiences WHERE category = ? "
                "ORDER BY recorded_at DESC LIMIT ?",
                (category, limit),
            )
        else:
            cursor = self.connection.execute(
                "SELECT * FROM experiences ORDER BY recorded_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Query Helpers / 查询辅助方法
    # ------------------------------------------------------------------

    def query_sessions(
        self, limit: int = 20, status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent session records.

        检索最近的会话记录.

        Args:
            limit: Max sessions to return.
                  返回的最大会话数.
            status: Filter by status, or None for all.
                   按状态过滤,或None表示全部.

        Returns:
            List of session dictionaries ordered by creation time.
             按创建时间排序的会话字典列表.
        """
        if status:
            cursor = self.connection.execute(
                "SELECT * FROM sessions WHERE status = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = self.connection.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]


def _dt_str(value: Optional[Any]) -> Optional[str]:
    """Convert various datetime representations to ISO string.

    将各种日期时间表示转换为ISO字符串.

    Args:
        value: datetime object, string, or None.
              datetime对象,字符串或None.

    Returns:
        ISO format string or None.
         ISO格式字符串或None.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


__all__ = ["Database"]
