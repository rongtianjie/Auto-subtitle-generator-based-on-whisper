"""
错误处理装饰器和工具

提供统一的错误处理、重试、超时机制
"""

import asyncio
import functools
from typing import Callable, Any, Type, Tuple
from loguru import logger


def handle_task_error(
    max_retries: int = 3,
    backoff_base: float = 2.0,
    backoff_max: float = 60.0,
):
    """
    任务错误处理装饰器

    处理不同类型的异常：
    - asyncio.CancelledError: 优雅关闭
    - MemoryError / OutOfMemoryError: 清理缓存后重试
    - 数据库错误: 指数退避重试
    - 其他错误: 记录并标记任务失败

    Args:
        max_retries: 最大重试次数
        backoff_base: 指数退避基数
        backoff_max: 最大等待时间（秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            task = args[0] if args else None
            task_id = getattr(task, 'id', 'unknown')

            for attempt in range(1, max_retries + 1):
                try:
                    logger.debug(f"Task {task_id}: executing attempt {attempt}/{max_retries}")
                    return await func(self, *args, **kwargs)

                except asyncio.CancelledError:
                    # 优雅关闭信号
                    logger.info(f"Task {task_id}: cancelled by system")
                    raise

                except (MemoryError, Exception) as e:
                    if isinstance(e, (MemoryError, )):
                        logger.warning(f"Task {task_id}: memory error, clearing caches")
                        # 这里可以清理缓存
                        # cache_manager.clear_old()

                    if attempt < max_retries:
                        # 计算退避时间（指数退避）
                        backoff = min(backoff_base ** (attempt - 1), backoff_max)
                        logger.warning(
                            f"Task {task_id}: error on attempt {attempt}, "
                            f"retrying in {backoff:.1f}s: {type(e).__name__}: {e}"
                        )
                        await asyncio.sleep(backoff)
                    else:
                        logger.error(
                            f"Task {task_id}: failed after {max_retries} attempts: "
                            f"{type(e).__name__}: {e}",
                            exc_info=True
                        )
                        raise

        return wrapper
    return decorator


def with_timeout(seconds: float):
    """
    超时装饰器

    如果函数执行超过指定时间，抛出 asyncio.TimeoutError
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"{func.__name__} timed out after {seconds}s")
                raise

        return wrapper
    return decorator


class ExponentialBackoff:
    """指数退避重试策略"""

    def __init__(self, base: float = 1.0, max_wait: float = 60.0, jitter: bool = True):
        """
        Args:
            base: 基础等待时间（秒）
            max_wait: 最大等待时间（秒）
            jitter: 是否添加随机偏差（防止雷鸣羊群）
        """
        self.base = base
        self.max_wait = max_wait
        self.jitter = jitter
        self.attempt = 0

    def next_delay(self) -> float:
        """计算下一次重试的延迟时间"""
        self.attempt += 1
        delay = min(self.base * (2 ** (self.attempt - 1)), self.max_wait)

        if self.jitter:
            import random
            # 添加 ±10% 的随机偏差
            jitter_amount = delay * 0.1
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)  # 确保不会是负数

    def reset(self):
        """重置尝试计数"""
        self.attempt = 0


async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    backoff: ExponentialBackoff | None = None,
    **kwargs
) -> Any:
    """
    带指数退避的重试函数

    Args:
        func: 要执行的异步函数
        max_retries: 最大重试次数
        backoff: 退避策略（若不提供则创建默认的）

    Returns:
        函数执行结果

    Raises:
        最后一次尝试的异常
    """
    if backoff is None:
        backoff = ExponentialBackoff()

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                delay = backoff.next_delay()
                logger.warning(
                    f"Attempt {attempt} failed, retrying in {delay:.1f}s: {type(e).__name__}"
                )
                await asyncio.sleep(delay)

    if last_error:
        logger.error(f"All {max_retries} attempts failed: {last_error}")
        raise last_error

    raise RuntimeError("Retry loop failed unexpectedly")
