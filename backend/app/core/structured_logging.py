"""
结构化日志系统 - structlog 配置

提供以下功能：
1. 结构化日志输出 (JSON 格式)
2. 上下文追踪 (request_id, user_id, task_id)
3. 本地和远程日志聚合
4. 性能指标记录
5. 错误堆栈跟踪增强
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from structlog.processors import (
    TimeStamper,
    add_log_level,
    format_exc_info,
    JSONRenderer,
    CallsiteParameterAdder,
)
from structlog.contextvars import bind_contextvars, clear_contextvars
from pythonjsonlogger import jsonlogger


# 日志目录
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "storage",
    "logs",
)


# 上下文变量（自动包含在所有日志中）
class LogContext:
    """日志上下文管理"""

    def __init__(self):
        self.request_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.task_id: Optional[str] = None
        self.session_id: Optional[str] = None

    def set_request(self, request_id: str, user_id: Optional[str] = None):
        """设置请求上下文"""
        self.request_id = request_id
        if user_id:
            self.user_id = user_id
        bind_contextvars(request_id=request_id, user_id=user_id or "anonymous")

    def set_task(self, task_id: str):
        """设置任务上下文"""
        self.task_id = task_id
        bind_contextvars(task_id=task_id)

    def clear(self):
        """清除上下文"""
        clear_contextvars()
        self.request_id = None
        self.user_id = None
        self.task_id = None
        self.session_id = None


log_context = LogContext()


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """自定义 JSON 格式化器"""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # 添加自定义字段
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["logger_name"] = record.name
        log_record["level"] = record.levelname.upper()

        # 添加上下文信息
        if log_context.request_id:
            log_record["request_id"] = log_context.request_id
        if log_context.user_id:
            log_record["user_id"] = log_context.user_id
        if log_context.task_id:
            log_record["task_id"] = log_context.task_id

        # 添加异常信息
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


def setup_structlog():
    """初始化 structlog 结构化日志系统"""
    os.makedirs(LOG_DIR, exist_ok=True)

    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG,
    )

    # 配置 structlog 处理器
    structlog.configure(
        processors=[
            # 添加日志级别
            add_log_level,
            # 添加时间戳
            TimeStamper(fmt="iso"),
            # 添加调用位置信息
            CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            ),
            # 异常处理
            format_exc_info,
            # JSON 输出
            JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 获取 structlog logger
    return structlog.get_logger()


def configure_file_handlers():
    """配置文件日志处理器"""
    logger = logging.getLogger()

    # 清除现有的处理器
    logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        )
    )
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    # 应用日志文件处理器 (JSON 格式)
    app_log_path = os.path.join(LOG_DIR, "app.log")
    app_handler = logging.FileHandler(app_log_path, encoding="utf-8")
    app_handler.setFormatter(CustomJSONFormatter('{"time": "%(timestamp)s"}'))
    app_handler.setLevel(logging.DEBUG)
    logger.addHandler(app_handler)

    # 错误日志文件处理器 (JSON 格式)
    error_log_path = os.path.join(LOG_DIR, "error.log")
    error_handler = logging.FileHandler(error_log_path, encoding="utf-8")
    error_handler.setFormatter(CustomJSONFormatter('{"time": "%(timestamp)s"}'))
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)

    # 性能日志文件处理器 (JSON 格式)
    perf_log_path = os.path.join(LOG_DIR, "performance.log")
    perf_handler = logging.FileHandler(perf_log_path, encoding="utf-8")
    perf_handler.setFormatter(CustomJSONFormatter('{"time": "%(timestamp)s"}'))
    perf_handler.setLevel(logging.INFO)
    logger.addHandler(perf_handler)

    logger.setLevel(logging.DEBUG)


class PerformanceLogger:
    """性能日志记录器"""

    def __init__(self, logger):
        self.logger = logger

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
    ):
        """记录 HTTP 请求性能"""
        self.logger.info(
            "http_request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            slow=duration_ms > 1000,  # 标记超过 1 秒的请求
        )

    def log_database_query(
        self,
        query: str,
        duration_ms: float,
        rows_affected: int = 0,
    ):
        """记录数据库查询性能"""
        self.logger.info(
            "db_query",
            query=query[:100],  # 截断长查询
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            slow=duration_ms > 100,  # 标记超过 100ms 的查询
        )

    def log_task_progress(
        self,
        task_id: str,
        operation: str,
        progress: float,
        duration_ms: float,
    ):
        """记录任务进度和性能"""
        self.logger.info(
            "task_progress",
            task_id=task_id,
            operation=operation,
            progress=progress,
            duration_ms=duration_ms,
        )

    def log_cache_hit(
        self,
        cache_key: str,
        hit: bool,
        duration_ms: float,
    ):
        """记录缓存命中情况"""
        self.logger.info(
            "cache_hit",
            cache_key=cache_key,
            hit=hit,
            duration_ms=duration_ms,
        )


class AuditLogger:
    """审计日志记录器 - 记录敏感操作"""

    def __init__(self, logger):
        self.logger = logger

    def log_auth(self, username: str, success: bool, ip: str = ""):
        """记录认证事件"""
        self.logger.info(
            "auth_event",
            username=username,
            success=success,
            ip=ip,
            event="login_attempt",
        )

    def log_task_created(self, task_id: str, user_id: str, title: str):
        """记录任务创建"""
        self.logger.info(
            "task_created",
            task_id=task_id,
            user_id=user_id,
            title=title,
            event="task_created",
        )

    def log_task_deleted(self, task_id: str, user_id: str):
        """记录任务删除"""
        self.logger.warning(
            "task_deleted",
            task_id=task_id,
            user_id=user_id,
            event="task_deleted",
        )

    def log_file_uploaded(self, filename: str, size: int, user_id: Optional[str] = None):
        """记录文件上传"""
        self.logger.info(
            "file_uploaded",
            filename=filename,
            size=size,
            user_id=user_id,
            event="file_uploaded",
        )

    def log_permission_denied(self, user_id: str, resource: str, action: str):
        """记录权限拒绝事件"""
        self.logger.warning(
            "permission_denied",
            user_id=user_id,
            resource=resource,
            action=action,
            event="permission_denied",
        )


# 初始化日志系统
logger = setup_structlog()
configure_file_handlers()

# 创建专用日志记录器
perf_logger = PerformanceLogger(logger)
audit_logger = AuditLogger(logger)
