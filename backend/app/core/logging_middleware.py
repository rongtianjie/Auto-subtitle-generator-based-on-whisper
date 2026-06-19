"""
日志中间件 - FastAPI 集成

自动记录：
1. HTTP 请求和响应
2. 请求上下文 (request_id, user_id)
3. 执行时间和性能指标
4. 错误和异常
"""

import time
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.structured_logging import log_context, logger, perf_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    日志记录中间件

    功能：
    - 生成请求 ID
    - 记录请求/响应信息
    - 追踪执行时间
    - 捕获错误信息
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求 ID
        request_id = str(uuid.uuid4())

        # 提取用户信息（如果已认证）
        user_id = None
        if hasattr(request.state, "user"):
            user_id = str(request.state.user.id)

        # 设置日志上下文
        log_context.set_request(request_id, user_id)

        # 记录请求开始
        start_time = time.time()
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_string=str(request.url.query),
            client_ip=request.client[0] if request.client else "unknown",
            user_id=user_id,
        )

        try:
            # 处理请求
            response = await call_next(request)

            # 计算执行时间
            duration_ms = (time.time() - start_time) * 1000

            # 记录性能指标
            perf_logger.log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
            )

            # 记录响应
            logger.info(
                "request_completed",
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # 添加请求 ID 到响应头
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # 计算执行时间
            duration_ms = (time.time() - start_time) * 1000

            # 记录错误
            logger.exception(
                "request_error",
                request_id=request_id,
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )

            raise

        finally:
            # 清除上下文
            log_context.clear()


class ContextLoggingMiddleware:
    """
    应用级上下文日志中间件

    自动为所有操作添加上下文信息
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # 为每个 HTTP 请求生成请求 ID
            request_id = str(uuid.uuid4())
            scope["request_id"] = request_id

        await self.app(scope, receive, send)
