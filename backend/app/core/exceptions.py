"""
标准异常定义和错误响应格式

统一所有 API 错误响应:
{
  "error_code": "CODE",
  "message": "Human-readable message",
  "timestamp": "2026-06-18T10:30:00Z",
  "details": {...}  # 可选
}
"""

from enum import Enum
from fastapi import HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Any, Optional


class ErrorCode(str, Enum):
    """标准错误代码"""

    # 认证和授权
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # 参数验证
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_URL = "INVALID_URL"

    # 资源
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # 业务规则
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"

    # 服务相关
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"

    # 特定业务错误
    TASK_NOT_QUEUED = "TASK_NOT_QUEUED"
    INVALID_MODEL = "INVALID_MODEL"
    MODEL_NOT_DOWNLOADED = "MODEL_NOT_DOWNLOADED"
    INSUFFICIENT_STORAGE = "INSUFFICIENT_STORAGE"


class ErrorResponse(BaseModel):
    """标准错误响应格式"""

    error_code: str
    message: str
    timestamp: str
    details: Optional[dict[str, Any]] = None

    def dict(self, **kwargs):
        """覆盖 dict 方法以保留字段顺序"""
        return self.model_dump(**kwargs)


class AppException(Exception):
    """应用异常基类"""

    def __init__(
        self,
        error_code: ErrorCode | str = ErrorCode.INTERNAL_ERROR,
        message: str = "An error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_response(self) -> ErrorResponse:
        """转换为标准错误响应"""
        error_code = self.error_code.value if isinstance(self.error_code, ErrorCode) else str(self.error_code)
        return ErrorResponse(
            error_code=error_code,
            message=self.message,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            details=self.details if self.details else None,
        )


# 认证异常


class AuthException(AppException):
    """认证异常基类"""

    pass


class InvalidCredentialsException(AuthException):
    """无效凭证"""

    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(
            error_code=ErrorCode.INVALID_CREDENTIALS,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class TokenExpiredException(AuthException):
    """Token 已过期"""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            error_code=ErrorCode.TOKEN_EXPIRED,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class UnauthorizedException(AuthException):
    """未授权"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            error_code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(AppException):
    """禁止访问"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            error_code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


# 参数验证异常


class ValidationException(AppException):
    """参数验证异常"""

    def __init__(
        self,
        message: str = "Validation failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            error_code=ErrorCode.INVALID_REQUEST,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class InvalidFileTypeException(ValidationException):
    """无效文件类型"""

    def __init__(self, message: str = "File type not supported"):
        super().__init__(
            error_code=ErrorCode.INVALID_FILE_TYPE,
            message=message,
        )


class FileTooLargeException(ValidationException):
    """文件太大"""

    def __init__(self, max_size_mb: int):
        super().__init__(
            error_code=ErrorCode.FILE_TOO_LARGE,
            message=f"File exceeds maximum size of {max_size_mb}MB",
            details={"max_size_mb": max_size_mb},
        )


class InvalidURLException(ValidationException):
    """无效 URL"""

    def __init__(self, url: str):
        super().__init__(
            error_code=ErrorCode.INVALID_URL,
            message="Invalid or unsupported URL",
            details={"url": url},
        )


# 资源异常


class NotFoundException(AppException):
    """资源不存在"""

    def __init__(self, resource: str = "Resource", identifier: str | None = None):
        msg = f"{resource} not found"
        if identifier:
            msg += f": {identifier}"
        super().__init__(
            error_code=ErrorCode.NOT_FOUND,
            message=msg,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier},
        )


class AlreadyExistsException(AppException):
    """资源已存在"""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str | None = None,
        message: str | None = None,
    ):
        msg = message or f"{resource} already exists"
        if identifier:
            if message is None:
                msg += f": {identifier}"
        super().__init__(
            error_code=ErrorCode.ALREADY_EXISTS,
            message=msg,
            status_code=status.HTTP_409_CONFLICT,
            details={"resource": resource, "identifier": identifier},
        )


class ConflictException(AppException):
    """冲突"""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            error_code=ErrorCode.CONFLICT,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )


# 业务规则异常


class QuotaExceededException(AppException):
    """超过配额"""

    def __init__(self, message: str = "Quota exceeded"):
        super().__init__(
            error_code=ErrorCode.QUOTA_EXCEEDED,
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class TooManyRequestsException(AppException):
    """请求过于频繁"""

    def __init__(self, message: str = "Too many requests", retry_after: int | None = None):
        super().__init__(
            error_code=ErrorCode.TOO_MANY_REQUESTS,
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after} if retry_after else {},
        )


class OperationNotAllowedException(AppException):
    """操作不被允许"""

    def __init__(self, message: str = "Operation not allowed"):
        super().__init__(
            error_code=ErrorCode.OPERATION_NOT_ALLOWED,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


# 服务异常


class ServiceUnavailableException(AppException):
    """服务不可用"""

    def __init__(self, service: str = "Service", message: str | None = None):
        msg = message or f"{service} is currently unavailable"
        super().__init__(
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            message=msg,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service},
        )


class TimeoutException(AppException):
    """请求超时"""

    def __init__(self, operation: str = "Operation"):
        super().__init__(
            error_code=ErrorCode.TIMEOUT,
            message=f"{operation} timed out",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details={"operation": operation},
        )


class InternalException(AppException):
    """内部错误"""

    def __init__(self, message: str = "Internal server error", original_error: Exception | None = None):
        super().__init__(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"error": str(original_error)} if original_error else {},
        )


# 特定业务异常


class TaskNotQueuedException(OperationNotAllowedException):
    """任务未入队"""

    def __init__(self):
        super().__init__("Task is not in queued or processing state")


class InvalidModelException(ValidationException):
    """无效模型"""

    def __init__(self, model: str):
        super().__init__(
            error_code=ErrorCode.INVALID_MODEL,
            message=f"Model not supported: {model}",
            details={"model": model},
        )


class ModelNotDownloadedException(AppException):
    """模型未下载"""

    def __init__(self, model: str):
        super().__init__(
            error_code=ErrorCode.MODEL_NOT_DOWNLOADED,
            message=f"Model not downloaded: {model}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"model": model},
        )


class InsufficientStorageException(AppException):
    """存储空间不足"""

    def __init__(self, message: str = "Insufficient storage space"):
        super().__init__(
            error_code=ErrorCode.INSUFFICIENT_STORAGE,
            message=message,
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
        )
