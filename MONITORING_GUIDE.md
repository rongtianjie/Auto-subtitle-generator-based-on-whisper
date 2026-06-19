# 监控和告警系统文档

## 概述

本项目采用 Prometheus + Grafana 的监控架构，提供：

- ✓ 实时性能指标导出
- ✓ 自动告警规则
- ✓ 健康检查端点
- ✓ 系统资源监控
- ✓ 业务指标追踪

## 架构

```
应用程序
    ↓
Prometheus 客户端库 (prometheus-client)
    ↓
/metrics 端点 (Prometheus scrape)
    ↓
Prometheus 服务器 (定期抓取)
    ↓
告警管理器 (检查规则，触发告警)
    ↓
告警通知 (邮件、Slack、钉钉)
    ↓
Grafana 仪表板 (数据可视化)
```

## 指标分类

### 1. HTTP 请求指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `http_requests_total` | Counter | HTTP 请求总数（按方法、端点、状态码） |
| `http_request_duration_seconds` | Histogram | HTTP 请求延迟分布 |
| `http_requests_in_progress` | Gauge | 正在处理的请求数 |
| `http_request_size_bytes` | Summary | 请求大小统计 |
| `http_response_size_bytes` | Summary | 响应大小统计 |

**告警规则:**
- HighHTTPErrorRate: 5xx 错误率 > 1 req/s (5 分钟)
- HighHTTPLatency: p95 延迟 > 5s (5 分钟)

### 2. 数据库指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `db_connection_pool_size` | Gauge | 连接池总大小 |
| `db_connection_pool_checked_out` | Gauge | 当前检出的连接数 |
| `db_query_duration_seconds` | Histogram | 查询执行时间分布 |
| `db_query_errors_total` | Counter | 查询错误总数 |
| `db_slow_queries_total` | Counter | 超过 100ms 的查询数 |
| `db_transaction_duration_seconds` | Histogram | 事务执行时间分布 |

**告警规则:**
- HighDBQueryTime: 平均查询时间 > 1s (5 分钟)
- HighDBSlowQueries: 慢查询率 > 0.33/s (5 分钟)
- DBConnectionPoolExhausted: 检出连接 > 40 (2 分钟)
- HighDBTransactionTime: 事务时间 > 5s (5 分钟)

### 3. 任务处理指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `task_processing_total` | Counter | 已处理任务总数（按状态） |
| `task_processing_duration_seconds` | Histogram | 任务处理时间分布 |
| `task_queue_size` | Gauge | 任务队列大小（按状态） |
| `task_current_active` | Gauge | 当前活跃任务数 |
| `task_success_rate` | Gauge | 任务成功率 (%) |
| `task_average_duration_minutes` | Gauge | 平均处理时间 (分钟) |

**告警规则:**
- LowTaskSuccessRate: 成功率 < 95% (10 分钟)
- HighTaskQueueSize: 队列大小 > 100 (5 分钟)
- LongTaskProcessingTime: 平均耗时 > 30 分钟 (10 分钟)

### 4. Worker 指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `worker_status` | Enum | Worker 状态 (running/idle/error/stopped) |
| `worker_tasks_processed` | Counter | 处理的任务总数 |
| `worker_tasks_failed` | Counter | 失败的任务数 |
| `worker_uptime_seconds` | Gauge | Worker 运行时长 |

### 5. 文件上传指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `files_uploaded_total` | Counter | 上传文件总数 |
| `file_upload_size_bytes` | Summary | 文件大小统计 |
| `file_upload_duration_seconds` | Histogram | 上传时间分布 |
| `file_storage_used_bytes` | Gauge | 已用存储空间 |

**告警规则:**
- DiskSpaceRunningOut: 磁盘使用 > 900GB (5 分钟)

### 6. SSE 连接指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `sse_connections_active` | Gauge | 活跃 SSE 连接数 |
| `sse_connections_total` | Counter | 总连接数 |
| `sse_connection_duration_seconds` | Histogram | 连接时长分布 |

**告警规则:**
- HighSSEConnectionCount: 活跃连接 > 500 (5 分钟)

### 7. 系统资源指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `system_memory_usage_bytes` | Gauge | 内存使用量 |
| `system_cpu_usage_percent` | Gauge | CPU 使用率 |
| `system_disk_usage_bytes` | Gauge | 磁盘使用量 |
| `system_errors_total` | Counter | 系统错误总数 |

**告警规则:**
- HighMemoryUsage: 内存 > 8GB (5 分钟)
- HighCPUUsage: CPU > 80% (5 分钟)

## API 端点

### 获取 Prometheus 指标

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/metrics
```

用于 Prometheus scrape。

### 获取活跃告警

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/alerts
```

按严重级别过滤：

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/monitoring/alerts?severity=critical"
```

### 获取告警历史

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/monitoring/alerts/history?hours=24"
```

### 解除告警

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/alerts/HighHTTPErrorRate/resolve
```

### 检查告警规则

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/alerts/check
```

### 获取 Prometheus 规则配置

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/rules/prometheus
```

### 获取健康状态

```bash
curl http://localhost:8000/api/v1/monitoring/health
```

不需要认证。

### 获取系统统计

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/stats
```

### 获取仪表板数据

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/dashboard/data
```

## Prometheus 配置

### prometheus.yml

```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s

rule_files:
  - /etc/prometheus/rules.yml

scrape_configs:
  - job_name: 'subweaver'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/monitoring/metrics'
    bearer_token: 'your_token_here'
    scrape_interval: 15s
    scrape_timeout: 10s
```

### 告警规则

获取规则配置：

```bash
curl -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/api/v1/monitoring/rules/prometheus > rules.yml
```

将生成的 rules.yml 复制到 Prometheus 目录：

```bash
cp rules.yml /etc/prometheus/rules.yml
systemctl reload prometheus
```

## Grafana 集成

### 添加数据源

1. 登录 Grafana
2. Configuration → Data Sources → Add
3. 选择 Prometheus
4. URL: `http://prometheus:9090`
5. 点击 Save & Test

### 创建仪表板

示例查询：

```promql
# HTTP 请求速率
rate(http_requests_total[5m])

# HTTP 错误率
rate(http_requests_total{status_code=~"5.."}[5m])

# 平均响应时间
rate(http_request_duration_seconds_sum[5m]) / 
rate(http_request_duration_seconds_count[5m])

# 活跃任务数
task_current_active

# 任务成功率
task_success_rate

# 数据库连接使用率
db_connection_pool_checked_out / db_connection_pool_size * 100
```

## 告警通知

### 邮件通知

```python
# 在 alerting.py 中添加
import smtplib
from email.mime.text import MIMEText

def send_email_alert(alert: Alert):
    """发送邮件告警"""
    msg = MIMEText(alert.message)
    msg['Subject'] = f"[{alert.severity.upper()}] {alert.rule_name}"
    msg['From'] = 'alerts@example.com'
    msg['To'] = 'admin@example.com'
    
    with smtplib.SMTP('localhost') as smtp:
        smtp.send_message(msg)
```

### Slack 通知

```python
import requests

def send_slack_alert(alert: Alert):
    """发送 Slack 告警"""
    webhook_url = 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    
    color_map = {
        'critical': '#FF0000',
        'warning': '#FFA500',
        'info': '#0099FF',
    }
    
    payload = {
        'attachments': [{
            'color': color_map.get(alert.severity, '#CCCCCC'),
            'title': alert.rule_name,
            'text': alert.message,
            'fields': [
                {'title': '严重级别', 'value': alert.severity, 'short': True},
                {'title': '值', 'value': str(alert.value), 'short': True},
                {'title': '阈值', 'value': str(alert.threshold), 'short': True},
                {'title': '时间', 'value': alert.timestamp.isoformat(), 'short': False},
            ]
        }]
    }
    
    requests.post(webhook_url, json=payload)
```

### 钉钉通知

```python
def send_dingtalk_alert(alert: Alert):
    """发送钉钉告警"""
    import requests
    
    webhook_url = 'https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN'
    
    message = f"""
## 告警通知

**规则**: {alert.rule_name}
**严重级别**: {alert.severity}
**指标**: {alert.metric_name}
**当前值**: {alert.value}
**阈值**: {alert.threshold}
**时间**: {alert.timestamp.isoformat()}

{alert.message}
"""
    
    payload = {
        'msgtype': 'markdown',
        'markdown': {
            'title': f'[{alert.severity.upper()}] {alert.rule_name}',
            'text': message
        }
    }
    
    requests.post(webhook_url, json=payload)
```

## 性能调优

### 优化 Prometheus 存储

```yaml
# prometheus.yml
global:
  # 减少保留期以节省磁盘
  tsdb:
    retention_size: 5GB
    retention_time: 7d
```

### 优化查询性能

```promql
# ❌ 避免：高基数标签
http_requests_total

# ✅ 使用：限制时间范围
rate(http_requests_total[5m])

# ✅ 使用：聚合
sum by (method) (rate(http_requests_total[5m]))
```

## 故障排除

### Prometheus 连接失败

检查认证令牌和网络连接：

```bash
curl -v -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/metrics
```

### 告警规则不匹配

验证指标名称和标签：

```promql
# Prometheus 控制台
http_requests_total
```

### 高内存占用

调整 Prometheus 配置：

```yaml
global:
  # 降低采样分辨率
  scrape_interval: 60s
  evaluation_interval: 60s
```

## 监控最佳实践

1. **设置有意义的告警阈值**
   - 基于历史数据和 SLO
   - 避免过于敏感或不敏感

2. **定期审查告警**
   - 禁用已弃用的规则
   - 更新过时的阈值
   - 修复非工作告警

3. **追踪业务指标**
   - 转录时长
   - 翻译单词数
   - 用户活跃度

4. **关联应用日志和指标**
   - 使用 request_id 关联
   - 便于快速定位问题

5. **定期备份指标数据**
   - 导出历史数据
   - 保存用于分析和审计

## 参考资源

- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)
- [prometheus-client Python 文档](https://github.com/prometheus/client_python)
