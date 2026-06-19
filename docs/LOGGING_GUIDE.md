# 结构化日志系统文档

## 概述

本项目采用 `structlog` 进行结构化日志记录，提供：

- ✓ JSON 格式的日志输出
- ✓ 自动上下文追踪 (request_id, user_id, task_id)
- ✓ 性能指标记录
- ✓ 审计日志
- ✓ 本地和远程日志聚合支持

## 日志文件

```
storage/logs/
├── app.log           # 应用日志（所有级别）
├── error.log         # 错误日志（ERROR 级别）
└── performance.log   # 性能日志（性能指标）
```

每个文件以 JSON 格式存储，支持自动轮转和压缩。

## 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 调试信息 | 函数入口、参数值 |
| INFO | 一般信息 | 请求处理、任务进度 |
| WARNING | 警告信息 | 已弃用的 API、资源限制达到 |
| ERROR | 错误信息 | 异常、数据库错误 |
| CRITICAL | 严重错误 | 系统故障 |

## 使用示例

### 基础日志

```python
from app.core.structured_logging import logger

# 简单日志
logger.info("任务开始", task_id="uuid", title="My Task")

# 带异常的日志
try:
    do_something()
except Exception as e:
    logger.exception("处理失败", task_id="uuid")
```

### 性能日志

```python
from app.core.structured_logging import perf_logger

# 记录 HTTP 请求性能
perf_logger.log_request(
    method="POST",
    path="/api/tasks",
    status_code=201,
    duration_ms=125.5,
    user_id="user123"
)

# 记录数据库查询性能
perf_logger.log_database_query(
    query="SELECT * FROM tasks WHERE user_id = %s",
    duration_ms=45.2,
    rows_affected=1
)

# 记录任务进度
perf_logger.log_task_progress(
    task_id="task-uuid",
    operation="speech_recognition",
    progress=0.45,
    duration_ms=12000
)

# 记录缓存命中
perf_logger.log_cache_hit(
    cache_key="model_base",
    hit=True,
    duration_ms=2.1
)
```

### 审计日志

```python
from app.core.structured_logging import audit_logger

# 认证事件
audit_logger.log_auth(
    username="user@example.com",
    success=True,
    ip="192.168.1.1"
)

# 任务创建
audit_logger.log_task_created(
    task_id="task-uuid",
    user_id="user-uuid",
    title="Video transcription"
)

# 任务删除
audit_logger.log_task_deleted(
    task_id="task-uuid",
    user_id="user-uuid"
)

# 文件上传
audit_logger.log_file_uploaded(
    filename="video.mp4",
    size=1024000,
    user_id="user-uuid"
)

# 权限拒绝
audit_logger.log_permission_denied(
    user_id="user-uuid",
    resource="task-uuid",
    action="delete"
)
```

## 自动上下文追踪

日志中间件自动为每个请求生成 `request_id`，并追踪以下信息：

```python
from app.core.structured_logging import log_context

# 在中间件中自动设置
log_context.set_request(
    request_id="uuid",
    user_id="user123"
)

# 在处理任务时手动设置
log_context.set_task("task-uuid")

# 清除上下文
log_context.clear()
```

所有日志会自动包含以下字段（如果存在）：
- `request_id` - HTTP 请求 ID
- `user_id` - 当前用户 ID
- `task_id` - 当前任务 ID

## 日志查询 API

所有日志查询 API 需要管理员权限。

### 获取最近日志

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/logs/recent?level=ERROR&limit=50"
```

### 按关键词搜索

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/logs/search?keyword=database&limit=100"
```

### 获取特定请求的日志

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/logs/request/{request_id}"
```

### 获取特定任务的日志

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/logs/task/{task_id}"
```

### 获取错误日志

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/logs/errors?hours=24&limit=100"
```

### 获取日志统计

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/logs/stats?hours=24"
```

## JSON 日志格式

```json
{
  "timestamp": "2026-06-19T12:34:56.123Z",
  "level": "INFO",
  "message": "request_started",
  "logger_name": "app.api.tasks",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "method": "POST",
  "path": "/api/v1/tasks",
  "duration_ms": 125.5,
  "status_code": 201
}
```

## 性能指标

### HTTP 请求

记录所有 HTTP 请求的性能：
- 方法和路径
- 状态码
- 执行时间
- 用户 ID
- 标记超过 1 秒的慢请求

### 数据库查询

记录所有数据库操作：
- 查询语句（截断）
- 执行时间
- 影响行数
- 标记超过 100ms 的慢查询

### 任务进度

记录后台任务的进度：
- 任务 ID
- 操作名称
- 进度百分比
- 执行时间

### 缓存命中

记录缓存操作：
- 缓存键
- 命中/未命中
- 查询时间

## 远程日志聚合

### ELK Stack 集成

将日志发送到 Elasticsearch：

```python
# 在 structured_logging.py 中添加
handler = logging.handlers.HTTPHandler(
    host='elasticsearch:9200',
    url='/logs',
    method='POST'
)
handler.setFormatter(CustomJSONFormatter())
logger.addHandler(handler)
```

### Datadog 集成

```python
# pip install datadog
import datadog

datadog.initialize(
    api_key='your_api_key',
    app_key='your_app_key'
)

# 在日志处理器中使用 Datadog logger
```

### Splunk 集成

使用 HTTP Event Collector (HEC)：

```python
import logging
import json

hec_endpoint = 'https://splunk:8088/services/collector'
hec_token = 'your_token'

handler = logging.handlers.HTTPHandler(
    host='splunk',
    url=hec_endpoint,
    method='POST',
    secure=True
)
```

## 最佳实践

1. **使用结构化数据**
   ```python
   # ❌ 不好
   logger.info(f"任务 {task_id} 处理完成，耗时 {duration}ms")
   
   # ✅ 好
   logger.info("任务完成", task_id=task_id, duration_ms=duration)
   ```

2. **避免日志泛滥**
   - 在循环中避免过度日志记录
   - 使用采样或日志级别过滤

3. **敏感信息脱敏**
   ```python
   # ❌ 不好
   logger.info("用户登录", password=password)
   
   # ✅ 好
   logger.info("用户登录", username=username)
   ```

4. **使用适当的日志级别**
   - DEBUG: 开发调试
   - INFO: 一般流程信息
   - WARNING: 潜在问题
   - ERROR: 错误事件
   - CRITICAL: 系统故障

5. **包含上下文**
   ```python
   # 总是包含足够的信息便于追踪
   logger.info(
       "任务更新",
       task_id=task.id,
       user_id=task.user_id,
       old_status=task.status,
       new_status=new_status
   )
   ```

## 日志轮转

日志文件会自动在以下情况下轮转：

- **时间**: 每天 00:00 轮转
- **保留期**: 30 天
- **压缩**: 轮转后自动 gzip 压缩

```
app.log                    # 当前日志
app.log.2026-06-18.gz      # 前一天的日志（压缩）
app.log.2026-06-17.gz      # 更早的日志
...
```

## 故障排除

### 日志文件不存在

检查 `storage/logs` 目录是否存在和可写：

```bash
ls -la storage/logs/
chmod 755 storage/logs/
```

### 日志写入失败

检查磁盘空间和权限：

```bash
df -h storage/
ls -l storage/logs/app.log
```

### JSON 解析错误

某些日志行可能不是有效的 JSON（例如，异常堆栈跟踪）。查询 API 会跳过这些行。

## 配置

日志系统的配置在 `app/core/structured_logging.py` 中：

```python
# 修改日志文件路径
LOG_DIR = "/var/log/app"

# 修改保留期
retention="30 days"  # 改为其他值

# 修改轮转时间
rotation="00:00"  # 改为其他时间
```

## 监控告警

建议设置以下监控告警：

| 指标 | 阈值 | 告警 |
|------|------|------|
| ERROR 日志数 | > 10/分钟 | 应用故障 |
| HTTP 500 响应 | > 5% | 服务不可用 |
| 数据库查询时间 | > 1000ms | 数据库性能下降 |
| 请求处理时间 | > 5000ms | API 性能下降 |

见 [监控系统文档](OPTIMIZATION_MONITORING.md)。
