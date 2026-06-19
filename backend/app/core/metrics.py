"""
Prometheus 指标导出

导出以下指标：
1. HTTP 请求指标 (延迟、吞吐量、错误率)
2. 数据库指标 (查询时间、连接数、慢查询)
3. 任务指标 (处理速率、成功率、失败率)
4. 系统指标 (内存、CPU、磁盘)
5. 业务指标 (活跃任务、队列大小)
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Enum,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_client.core import CollectorRegistry
import time
from typing import Optional


# 创建自定义 registry
registry = CollectorRegistry()


# ============ HTTP 请求指标 ============

http_requests_total = Counter(
    'http_requests_total',
    'HTTP 请求总数',
    ['method', 'endpoint', 'status_code'],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP 请求延迟',
    ['method', 'endpoint'],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=registry,
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    '处理中的 HTTP 请求数',
    registry=registry,
)

http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP 请求大小 (字节)',
    registry=registry,
)

http_response_size_bytes = Summary(
    'http_response_size_bytes',
    'HTTP 响应大小 (字节)',
    registry=registry,
)


# ============ 数据库指标 ============

db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    '数据库连接池大小',
    registry=registry,
)

db_connection_pool_checked_out = Gauge(
    'db_connection_pool_checked_out',
    '当前检出的数据库连接数',
    registry=registry,
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    '数据库查询耗时',
    ['query_type'],  # SELECT, INSERT, UPDATE, DELETE
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry,
)

db_query_errors_total = Counter(
    'db_query_errors_total',
    '数据库查询错误总数',
    ['query_type', 'error_type'],
    registry=registry,
)

db_slow_queries_total = Counter(
    'db_slow_queries_total',
    '超过 100ms 的查询总数',
    ['query_type'],
    registry=registry,
)

db_transaction_duration_seconds = Histogram(
    'db_transaction_duration_seconds',
    '数据库事务耗时',
    buckets=(0.01, 0.1, 0.5, 1.0, 5.0, 10.0),
    registry=registry,
)


# ============ 任务处理指标 ============

task_processing_total = Counter(
    'task_processing_total',
    '处理的任务总数',
    ['status'],  # completed, failed, cancelled
    registry=registry,
)

task_processing_duration_seconds = Histogram(
    'task_processing_duration_seconds',
    '任务处理耗时',
    ['task_type'],  # transcribe, translate
    buckets=(10, 30, 60, 120, 300, 600, 1200, 3600),
    registry=registry,
)

task_queue_size = Gauge(
    'task_queue_size',
    '任务队列大小',
    ['status'],  # pending, processing
    registry=registry,
)

task_current_active = Gauge(
    'task_current_active',
    '当前活跃任务数',
    registry=registry,
)

task_success_rate = Gauge(
    'task_success_rate',
    '任务成功率 (百分比)',
    registry=registry,
)

task_average_duration_minutes = Gauge(
    'task_average_duration_minutes',
    '任务平均处理时间 (分钟)',
    registry=registry,
)


# ============ Worker 指标 ============

worker_status = Enum(
    'worker_status',
    'Worker 状态',
    states=['running', 'idle', 'error', 'stopped'],
    registry=registry,
)

worker_tasks_processed = Counter(
    'worker_tasks_processed',
    'Worker 处理的任务总数',
    ['worker_id'],
    registry=registry,
)

worker_tasks_failed = Counter(
    'worker_tasks_failed',
    'Worker 失败的任务数',
    ['worker_id'],
    registry=registry,
)

worker_uptime_seconds = Gauge(
    'worker_uptime_seconds',
    'Worker 运行时长 (秒)',
    ['worker_id'],
    registry=registry,
)


# ============ 文件上传指标 ============

files_uploaded_total = Counter(
    'files_uploaded_total',
    '上传文件总数',
    ['file_type'],
    registry=registry,
)

file_upload_size_bytes = Summary(
    'file_upload_size_bytes',
    '上传文件大小 (字节)',
    registry=registry,
)

file_upload_duration_seconds = Histogram(
    'file_upload_duration_seconds',
    '文件上传耗时',
    buckets=(1, 5, 10, 30, 60, 120),
    registry=registry,
)

file_storage_used_bytes = Gauge(
    'file_storage_used_bytes',
    '使用的存储空间 (字节)',
    registry=registry,
)


# ============ SSE 连接指标 ============

sse_connections_active = Gauge(
    'sse_connections_active',
    '活跃 SSE 连接数',
    registry=registry,
)

sse_connections_total = Counter(
    'sse_connections_total',
    'SSE 连接总数',
    registry=registry,
)

sse_connection_duration_seconds = Histogram(
    'sse_connection_duration_seconds',
    'SSE 连接时长',
    buckets=(1, 10, 30, 60, 300, 600, 1800),
    registry=registry,
)


# ============ 缓存指标 ============

cache_hits_total = Counter(
    'cache_hits_total',
    '缓存命中总数',
    ['cache_name'],
    registry=registry,
)

cache_misses_total = Counter(
    'cache_misses_total',
    '缓存未命中总数',
    ['cache_name'],
    registry=registry,
)

cache_evictions_total = Counter(
    'cache_evictions_total',
    '缓存驱逐总数',
    ['cache_name'],
    registry=registry,
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    '缓存大小 (字节)',
    ['cache_name'],
    registry=registry,
)


# ============ 业务指标 ============

active_users = Gauge(
    'active_users',
    '活跃用户数',
    registry=registry,
)

authenticated_users = Gauge(
    'authenticated_users',
    '已认证用户数',
    registry=registry,
)

transcription_hours_total = Counter(
    'transcription_hours_total',
    '转录的音视频总时长 (小时)',
    registry=registry,
)

translation_words_total = Counter(
    'translation_words_total',
    '翻译的单词总数',
    registry=registry,
)


# ============ 系统指标 ============

system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    '系统内存使用量 (字节)',
    registry=registry,
)

system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    '系统 CPU 使用率 (%)',
    registry=registry,
)

system_disk_usage_bytes = Gauge(
    'system_disk_usage_bytes',
    '系统磁盘使用量 (字节)',
    registry=registry,
)

system_errors_total = Counter(
    'system_errors_total',
    '系统错误总数',
    ['error_type'],
    registry=registry,
)


# ============ 辅助函数 ============

class MetricsContext:
    """用于追踪请求/任务执行时间的上下文管理器"""

    def __init__(self, histogram: Histogram, labels: Optional[dict] = None):
        self.histogram = histogram
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.labels:
            self.histogram.labels(**self.labels).observe(duration)
        else:
            self.histogram.observe(duration)


def track_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """追踪 HTTP 请求指标"""
    http_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

    if duration > 1.0:  # 记录超过 1s 的请求
        from app.core.structured_logging import logger
        logger.warning(
            "slow_http_request",
            method=method,
            endpoint=endpoint,
            duration_ms=duration * 1000
        )


def track_db_query(query_type: str, duration: float, error: Optional[str] = None):
    """追踪数据库查询指标"""
    db_query_duration_seconds.labels(query_type=query_type).observe(duration)

    if error:
        db_query_errors_total.labels(query_type=query_type, error_type=type(error).__name__).inc()

    if duration > 0.1:  # 记录超过 100ms 的查询
        db_slow_queries_total.labels(query_type=query_type).inc()
        from app.core.structured_logging import logger
        logger.warning(
            "slow_db_query",
            query_type=query_type,
            duration_ms=duration * 1000
        )


def track_task_processing(status: str, duration: float, task_type: str = "transcribe"):
    """追踪任务处理指标"""
    task_processing_total.labels(status=status).inc()
    task_processing_duration_seconds.labels(task_type=task_type).observe(duration)

    # 更新成功率
    total = (
        task_processing_total.labels(status="completed")._value.get() +
        task_processing_total.labels(status="failed")._value.get() +
        task_processing_total.labels(status="cancelled")._value.get()
    )
    if total > 0:
        completed = task_processing_total.labels(status="completed")._value.get()
        task_success_rate.set((completed / total) * 100)


def get_metrics_text() -> str:
    """获取 Prometheus 格式的指标文本"""
    return generate_latest(registry).decode('utf-8')
