"""
SSE (Server-Sent Events) 连接管理

追踪、清理、监控所有活跃的 SSE 连接
"""

import time
from typing import Dict, List
from threading import Lock
from dataclasses import dataclass
from datetime import datetime

from loguru import logger


@dataclass
class SSEConnection:
    """SSE 连接信息"""
    connection_id: str
    task_id: str
    created_at: float
    last_activity: float

    @property
    def lifetime_seconds(self) -> float:
        """连接存活时间（秒）"""
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        """空闲时间（秒）"""
        return time.time() - self.last_activity


class SSEConnectionManager:
    """
    SSE 连接管理器

    管理所有活跃的 SSE 连接，包括:
    - 追踪连接生命周期
    - 检测和清理僵尸连接
    - 提供监控指标
    """

    def __init__(self, idle_timeout_seconds: int = 30, cleanup_interval_seconds: int = 60):
        """
        Args:
            idle_timeout_seconds: 连接最多空闲多久（秒）后认为已死亡
            cleanup_interval_seconds: 多久执行一次清理（秒）
        """
        self.idle_timeout = idle_timeout_seconds
        self.cleanup_interval = cleanup_interval_seconds
        self._connections: Dict[str, SSEConnection] = {}
        self._lock = Lock()
        self._cleanup_time = time.time()
        self._total_created = 0

    def register(self, connection_id: str, task_id: str) -> SSEConnection:
        """注册新的 SSE 连接"""
        with self._lock:
            conn = SSEConnection(
                connection_id=connection_id,
                task_id=task_id,
                created_at=time.time(),
                last_activity=time.time(),
            )
            self._connections[connection_id] = conn
            self._total_created += 1

            logger.debug(
                f"SSE connection registered | {connection_id} | task: {task_id}",
                extra={"total_connections": len(self._connections)},
            )
            return conn

    def update_activity(self, connection_id: str) -> None:
        """更新连接的活动时间"""
        with self._lock:
            if connection_id in self._connections:
                self._connections[connection_id].last_activity = time.time()

    def unregister(self, connection_id: str) -> None:
        """注销 SSE 连接"""
        with self._lock:
            if connection_id in self._connections:
                conn = self._connections[connection_id]
                lifetime = conn.lifetime_seconds

                del self._connections[connection_id]

                logger.debug(
                    f"SSE connection unregistered | {connection_id} | lifetime: {lifetime:.1f}s",
                    extra={"remaining_connections": len(self._connections)},
                )

    def cleanup_idle(self) -> int:
        """
        清理空闲超时的连接

        Returns:
            清理的连接数
        """
        with self._lock:
            now = time.time()
            idle_connections = [
                conn_id for conn_id, conn in self._connections.items()
                if now - conn.last_activity > self.idle_timeout
            ]

            for conn_id in idle_connections:
                conn = self._connections[conn_id]
                del self._connections[conn_id]

                logger.warning(
                    f"SSE connection timed out | {conn_id} | idle: {now - conn.last_activity:.1f}s",
                    extra={"remaining_connections": len(self._connections)},
                )

            return len(idle_connections)

    def should_cleanup(self) -> bool:
        """检查是否应该执行清理"""
        return time.time() - self._cleanup_time > self.cleanup_interval

    def mark_cleanup(self) -> None:
        """标记已执行清理"""
        self._cleanup_time = time.time()

    def get_active_count(self) -> int:
        """获取活跃连接数"""
        with self._lock:
            return len(self._connections)

    def get_connection_by_task(self, task_id: str) -> List[SSEConnection]:
        """获取某个任务的所有连接"""
        with self._lock:
            return [
                conn for conn in self._connections.values()
                if conn.task_id == task_id
            ]

    def get_stats(self) -> dict:
        """获取连接统计信息"""
        with self._lock:
            now = time.time()
            active = list(self._connections.values())
            avg_lifetime = (
                sum(now - conn.created_at for conn in active) / len(active)
                if active else 0
            )

            return {
                "active_connections": len(active),
                "total_created": self._total_created,
                "avg_lifetime_seconds": round(avg_lifetime, 1),
                "connections": [
                    {
                        "connection_id": conn.connection_id,
                        "task_id": conn.task_id,
                        "lifetime_seconds": round(conn.lifetime_seconds, 1),
                        "idle_seconds": round(conn.idle_seconds, 1),
                    }
                    for conn in active
                ],
            }


# 全局 SSE 连接管理器
sse_manager = SSEConnectionManager(
    idle_timeout_seconds=30,  # 30 秒无数据则认为连接死亡
    cleanup_interval_seconds=60,  # 每 60 秒清理一次
)
