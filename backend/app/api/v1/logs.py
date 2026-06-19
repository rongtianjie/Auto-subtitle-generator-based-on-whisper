"""
日志查询 API 端点 (仅管理员)

支持：
1. 获取最近日志
2. 按级别过滤
3. 按关键词搜索
4. 按时间范围过滤
5. 日志统计
"""

from datetime import datetime, timedelta
from typing import List, Optional
import json
import os

from fastapi import APIRouter, Query, Path, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.user import User
from app.config import settings


router = APIRouter(prefix="/logs", tags=["日志管理"])


class LogEntry(BaseModel):
    """日志条目"""
    timestamp: str
    level: str
    message: str
    logger: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    task_id: Optional[str] = None
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None


class LogStatsResponse(BaseModel):
    """日志统计"""
    total_entries: int
    by_level: dict  # {level: count}
    by_logger: dict  # {logger: count}
    errors_last_hour: int
    warnings_last_hour: int


def _check_admin(current_user: User = Depends(get_current_user)):
    """检查是否为管理员"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    return current_user


def _read_log_file(filepath: str, limit: int = 1000) -> List[dict]:
    """读取并解析日志文件"""
    if not os.path.exists(filepath):
        return []

    entries = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # 从文件末尾读取最近的日志
            lines = f.readlines()
            for line in reversed(lines[-limit:]):
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"读取日志文件失败: {e}")

    return list(reversed(entries))  # 保持顺序


def _get_log_files():
    """获取日志文件路径"""
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "storage",
        "logs",
    )
    return {
        "app": os.path.join(log_dir, "app.log"),
        "error": os.path.join(log_dir, "error.log"),
        "performance": os.path.join(log_dir, "performance.log"),
    }


@router.get("/recent", response_model=List[LogEntry])
async def get_recent_logs(
    level: Optional[str] = Query(None, description="日志级别: DEBUG/INFO/WARNING/ERROR"),
    limit: int = Query(100, description="返回条数"),
    _: User = Depends(_check_admin),
):
    """获取最近的日志"""
    log_files = _get_log_files()
    entries = []

    for log_file in log_files.values():
        entries.extend(_read_log_file(log_file, limit=limit * 2))

    # 按时间戳排序
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # 过滤级别
    if level:
        entries = [e for e in entries if e.get("level") == level.upper()]

    # 限制数量
    return entries[:limit]


@router.get("/search")
async def search_logs(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(100, description="返回条数"),
    _: User = Depends(_check_admin),
):
    """按关键词搜索日志"""
    log_files = _get_log_files()
    entries = []

    for log_file in log_files.values():
        for entry in _read_log_file(log_file, limit=limit * 5):
            message = entry.get("message", "").lower()
            if keyword.lower() in message:
                entries.append(entry)

    # 按时间排序
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return entries[:limit]


@router.get("/request/{request_id}", response_model=List[LogEntry])
async def get_request_logs(
    request_id: str = Path(..., description="请求 ID"),
    limit: int = Query(50, description="返回条数"),
    _: User = Depends(_check_admin),
):
    """获取特定请求的日志"""
    log_files = _get_log_files()
    entries = []

    for log_file in log_files.values():
        for entry in _read_log_file(log_file, limit=limit * 2):
            if entry.get("request_id") == request_id:
                entries.append(entry)

    # 按时间排序
    entries.sort(key=lambda x: x.get("timestamp", ""))
    return entries[:limit]


@router.get("/task/{task_id}", response_model=List[LogEntry])
async def get_task_logs(
    task_id: str = Path(..., description="任务 ID"),
    limit: int = Query(50, description="返回条数"),
    _: User = Depends(_check_admin),
):
    """获取特定任务的日志"""
    log_files = _get_log_files()
    entries = []

    for log_file in log_files.values():
        for entry in _read_log_file(log_file, limit=limit * 2):
            if entry.get("task_id") == task_id:
                entries.append(entry)

    # 按时间排序
    entries.sort(key=lambda x: x.get("timestamp", ""))
    return entries[:limit]


@router.get("/errors", response_model=List[LogEntry])
async def get_error_logs(
    hours: int = Query(24, description="查询最近 N 小时的错误"),
    limit: int = Query(100, description="返回条数"),
    _: User = Depends(_check_admin),
):
    """获取错误日志"""
    log_files = _get_log_files()
    entries = []
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    for log_file in log_files.values():
        for entry in _read_log_file(log_file, limit=limit * 2):
            if entry.get("level") == "ERROR":
                try:
                    ts = datetime.fromisoformat(entry.get("timestamp", ""))
                    if ts >= cutoff_time:
                        entries.append(entry)
                except:
                    entries.append(entry)

    # 按时间倒序排列
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return entries[:limit]


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(
    hours: int = Query(24, description="查询最近 N 小时的统计"),
    _: User = Depends(_check_admin),
):
    """获取日志统计"""
    log_files = _get_log_files()
    all_entries = []
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    for log_file in log_files.values():
        all_entries.extend(_read_log_file(log_file, limit=10000))

    # 统计
    by_level = {}
    by_logger = {}
    errors_last_hour = 0
    warnings_last_hour = 0
    hour_cutoff = datetime.utcnow() - timedelta(hours=1)

    for entry in all_entries:
        level = entry.get("level", "UNKNOWN")
        logger_name = entry.get("logger_name", "unknown")
        by_level[level] = by_level.get(level, 0) + 1
        by_logger[logger_name] = by_logger.get(logger_name, 0) + 1

        try:
            ts = datetime.fromisoformat(entry.get("timestamp", ""))
            if ts >= hour_cutoff:
                if level == "ERROR":
                    errors_last_hour += 1
                elif level == "WARNING":
                    warnings_last_hour += 1
        except:
            pass

    return LogStatsResponse(
        total_entries=len(all_entries),
        by_level=by_level,
        by_logger=by_logger,
        errors_last_hour=errors_last_hour,
        warnings_last_hour=warnings_last_hour,
    )
