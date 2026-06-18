"""
全局异常处理中间件和异常处理器

提供统一的错误捕获和响应格式
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.exceptions import AppException, ErrorResponse, InternalException


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理应用异常"""
    error_response = exc.to_response()

    # 日志记录
    if exc.status_code >= 500:
        logger.error(
            f"Server error: {exc.error_code} | {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "details": exc.details,
            },
        )
    else:
        logger.warning(
            f"Client error: {exc.error_code} | {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "path": request.url.path,
            },
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict(exclude_none=True),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未预期的异常"""
    logger.exception(
        f"Unhandled exception: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
    )

    # 包装为 InternalException 并返回统一格式
    internal_exc = InternalException(original_error=exc)
    error_response = internal_exc.to_response()

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict(exclude_none=True),
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理 Pydantic 验证异常"""
    logger.warning(
        f"Validation error: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )

    # 提取验证错误信息
    errors = []
    if hasattr(exc, "errors"):
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"][1:]),
                "message": error["msg"],
                "type": error["type"],
            })

    error_response = ErrorResponse(
        error_code="INVALID_REQUEST",
        message="Validation failed",
        timestamp=__import__("datetime").datetime.utcnow().isoformat() + "Z",
        details={"validation_errors": errors} if errors else {},
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.dict(exclude_none=True),
    )
