"""
Structured JSON Logging System.

Provides a centralized, structured logging infrastructure with:
- JSON-formatted log entries for machine parsing
- Dual output (file + console) support
- Automatic log rotation by size
- Per-session isolated log files
- CodeBuddy conversation record preservation

结构化JSON日志系统。
提供集中的、结构化的日志基础设施，包括：
- JSON格式化日志条目，便于机器解析
- 双输出（文件+控制台）支持
- 按大小自动轮转日志文件
- 每次会话隔离的日志文件
- CodeBuddy对话记录保留
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs log records as structured JSON.

    Converts standard Python LogRecord objects into consistent JSON structures
    with timestamp, level, module, operation details, and optional context data.

    将日志记录输出为结构化JSON的自定义格式化器。
将标准Python LogRecord对象转换为一致的JSON结构，
包含时间戳、级别、模块、操作详情和可选上下文数据。

    Attributes:
        include_extra: Whether to include extra fields from the LogRecord.
                       是否包含LogRecord中的额外字段。
    """

    def __init__(self, include_extra: bool = True) -> None:
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format a LogRecord as a JSON string.

        将LogRecord格式化为JSON字符串。

        Args:
            record: The logging record to format.
                   要格式化的日志记录。

        Returns:
            Single-line JSON string representation.
            单行JSON字符串表示。
        """
        # Build base structure / 构建基础结构
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "module": getattr(record, "module_name", record.module),
            "operation": getattr(record, "operation", ""),
            "message": record.getMessage(),
            "duration_ms": getattr(record, "duration_ms", None),
            "success": getattr(record, "success", None),
        }

        # Include exception info if present / 如有异常信息则包含
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["error"] = self.formatException(record.exc_info)

        # Include extra fields / 包含额外字段
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in (
                    "name", "msg", "args", "created", "relativeCreated",
                    "funcName", "filename", "levelname", "levelno", "exc_info",
                    "exc_text", "stack_info", "lineno", "module", "thread",
                    "threadName", "processName", "taskName", "message",
                    "operation", "duration_ms", "success", "module_name",
                ):
                    if not key.startswith("_"):
                        log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with color support (via Rich if available).

    Produces formatted text output suitable for terminal display,
    with optional Rich library integration for colored output.

    支持颜色（通过Rich库）的可读控制台格式化器。
生成适合终端显示的格式化文本输出，
可选集成Rich库以实现彩色输出。

    Attributes:
        use_colors: Whether to apply ANSI color codes.
                   是否应用ANSI颜色代码。
    """

    # ANSI color codes / ANSI颜色代码
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan / 青色
        "INFO": "\033[32m",      # Green / 绿色
        "WARNING": "\033[33m",   # Yellow / 黄色
        "ERROR": "\033[31m",     # Red / 红色
        "CRITICAL": "\033[35m",  # Magenta / 品红
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True) -> None:
        super().__init__()
        self.use_colors = use_colors and hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format record as human-readable console text.

        将记录格式化为可读的控制台文本。

        Args:
            record: The logging record to format.
                   要格式化的日志记录。

        Returns:
            Formatted string suitable for console output.
             适合控制台输出的格式化字符串。
        """
        level_color = ""
        reset = ""

        if self.use_colors:
            level_color = self.COLORS.get(record.levelname, "")
            reset = self.RESET

        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        module = getattr(record, "module_name", record.module)
        operation = getattr(record, "operation", "")

        parts = [
            f"{level_color}[{record.levelname:>8}]{reset}",
            f"{timestamp}",
        ]

        if operation:
            parts.append(f"[{module}:{operation}]")
        else:
            parts.append(f"[{module}]")

        parts.append(record.getMessage())

        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            parts.append(f"({duration_ms:.0f}ms)")

        return " ".join(parts)


def setup_logger(
    name: str = "similar_project_rating",
    log_dir: str = "./logs",
    level: str = "INFO",
    session_id: Optional[str] = None,
    json_format: bool = True,
    max_size_mb: int = 100,
    backup_count: int = 5,
    console_output: bool = True,
) -> logging.Logger:
    """Initialize and configure a logger instance with file and optional console handlers.

    Creates a logger with dual-output capability: rotating file handler for persistent
    structured logs, and optional stream handler for real-time console feedback.

    初始化并配置具有文件和可选控制台处理程序的logger实例。
创建具有双输出能力的logger：用于持久化结构化日志的旋转文件处理程序，
以及用于实时控制台反馈的可选流处理程序。

    Args:
        name: Logger name (typically module or package name).
              Logger名称（通常是模块或包名）。
        log_dir: Directory path for storing log files.
                 存储日志文件的目录路径。
        level: Minimum log level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
               最小日志级别（'DEBUG'、'INFO'、'WARNING'、'ERROR'）。
        session_id: If provided, creates a per-session log file with this ID prefix.
                   如果提供，则使用此前缀创建每次会话的日志文件。
        json_format: Use JSON formatting for file logs (recommended).
                    文件日志使用JSON格式（推荐）。
        max_size_mb: Maximum size of each log file before rotation (MB).
                    轮转前每个日志文件的最大大小（MB）。
        backup_count: Number of rotated backup files to retain.
                     保留的轮转备份文件数量。
        console_output: Whether to also output to stderr/console.
                      是否也输出到stderr/控制台。

    Returns:
        Configured Logger instance ready for use.
         配置好的可使用的Logger实例。
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Prevent duplicate handlers / 防止重复添加handler
    if logger.handlers:
        return logger

    # Ensure log directory exists / 确保日志目录存在
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Determine filename / 确定文件名
    if session_id:
        log_filename = log_path / f"{session_id}_detailed.log"
    else:
        log_filename = log_path / "application.log"

    # File handler with rotation / 带轮转的文件处理程序
    file_handler = RotatingFileHandler(
        filename=log_filename,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    if json_format:
        file_handler.setFormatter(JSONFormatter(include_extra=True))
    else:
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    logger.addHandler(file_handler)

    # Console handler / 控制台处理程序
    if console_output:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(ConsoleFormatter(use_colors=True))
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "similar_project_rating") -> logging.Logger:
    """Retrieve an existing logger by name, or return the root logger.

    Gets a previously configured logger. Call setup_logger() first
    if no configuration has been done yet.

    按名称检索现有logger，或返回根logger。
获取先前配置的logger。如果尚未进行配置，
请先调用setup_logger()。

    Args:
        name: Logger identifier to retrieve.
              要检索的logger标识符。

    Returns:
        Logger instance (configured or basic fallback).
         Logger实例（已配置的或基本后备）。
    """
    return logging.getLogger(name)


# Module-level convenience exports / 模块级便捷导出
__all__ = [
    "setup_logger",
    "get_logger",
    "JSONFormatter",
    "ConsoleFormatter",
]
