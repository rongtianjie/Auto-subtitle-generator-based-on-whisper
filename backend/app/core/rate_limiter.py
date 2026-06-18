"""
速率限制器

限制上传频率，防止滥用
"""

from typing import Dict, Tuple
from datetime import datetime, timedelta
from threading import Lock
import time


class RateLimiter:
    """
    简单的内存速率限制器

    按 IP 地址限制请求频率
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        """
        Args:
            max_requests: 时间窗口内最多请求数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list[float]] = {}
        self._lock = Lock()

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """
        检查是否允许请求

        Args:
            key: 限制键（例如 IP 地址）

        Returns:
            (是否允许, 剩余请求数)
        """
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # 初始化或清理旧请求
            if key not in self._requests:
                self._requests[key] = []
            else:
                # 移除超出时间窗口的请求
                self._requests[key] = [req_time for req_time in self._requests[key] if req_time > cutoff]

            # 检查是否超过限制
            remaining = self.max_requests - len(self._requests[key])

            if remaining > 0:
                # 记录这个请求
                self._requests[key].append(now)
                return True, remaining - 1
            else:
                # 超过限制
                return False, 0

    def cleanup(self):
        """清理过期的限制记录"""
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds * 2

            # 移除完全过期的键
            expired_keys = [
                key for key, times in self._requests.items()
                if not times or all(t < cutoff for t in times)
            ]
            for key in expired_keys:
                del self._requests[key]


# 全局上传速率限制器（每 IP 每分钟最多 5 个上传请求）
upload_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
