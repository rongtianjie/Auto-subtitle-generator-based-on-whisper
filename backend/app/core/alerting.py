"""
告警规则配置

支持：
1. Prometheus 告警规则
2. 自定义告警处理
3. 告警通知
"""

from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from app.core.metrics import registry, get_metrics_text
from app.core.structured_logging import logger


class AlertRule(BaseModel):
    """告警规则"""
    name: str
    metric: str
    condition: str  # ">", "<", "==", etc
    threshold: float
    duration: str  # "1m", "5m", "15m", etc
    severity: str  # "info", "warning", "critical"
    description: str
    enabled: bool = True


class Alert(BaseModel):
    """告警实例"""
    rule_name: str
    metric_name: str
    value: float
    threshold: float
    severity: str
    timestamp: datetime
    message: str


# 预定义告警规则
ALERT_RULES = [
    # HTTP 性能告警
    AlertRule(
        name="HighHTTPErrorRate",
        metric="http_requests_total",
        condition=">",
        threshold=5,  # 每分钟超过 5 个 500 错误
        duration="5m",
        severity="critical",
        description="HTTP 错误率过高",
    ),
    AlertRule(
        name="HighHTTPLatency",
        metric="http_request_duration_seconds",
        condition=">",
        threshold=5.0,  # 95% 延迟超过 5 秒
        duration="5m",
        severity="warning",
        description="HTTP 请求延迟过高",
    ),

    # 数据库告警
    AlertRule(
        name="HighDBQueryTime",
        metric="db_query_duration_seconds",
        condition=">",
        threshold=1.0,  # 平均查询时间超过 1 秒
        duration="5m",
        severity="warning",
        description="数据库查询时间过长",
    ),
    AlertRule(
        name="HighDBSlowQueries",
        metric="db_slow_queries_total",
        condition=">",
        threshold=100,  # 5 分钟内超过 100 条慢查询
        duration="5m",
        severity="critical",
        description="数据库慢查询过多",
    ),
    AlertRule(
        name="DBConnectionPoolExhausted",
        metric="db_connection_pool_checked_out",
        condition=">",
        threshold=40,  # 超过 40 个连接（总共 50）
        duration="2m",
        severity="critical",
        description="数据库连接池即将耗尽",
    ),
    AlertRule(
        name="HighDBTransactionTime",
        metric="db_transaction_duration_seconds",
        condition=">",
        threshold=5.0,
        duration="5m",
        severity="warning",
        description="数据库事务耗时过长",
    ),

    # 任务处理告警
    AlertRule(
        name="LowTaskSuccessRate",
        metric="task_success_rate",
        condition="<",
        threshold=95.0,  # 成功率低于 95%
        duration="10m",
        severity="warning",
        description="任务成功率下降",
    ),
    AlertRule(
        name="HighTaskQueueSize",
        metric="task_queue_size",
        condition=">",
        threshold=100,  # 队列中超过 100 个待处理任务
        duration="5m",
        severity="warning",
        description="任务队列堆积",
    ),
    AlertRule(
        name="LongTaskProcessingTime",
        metric="task_average_duration_minutes",
        condition=">",
        threshold=30.0,  # 平均处理时间超过 30 分钟
        duration="10m",
        severity="warning",
        description="任务处理时间过长",
    ),

    # 文件上传告警
    AlertRule(
        name="HighFileUploadFailureRate",
        metric="file_upload_errors_total",
        condition=">",
        threshold=10,
        duration="5m",
        severity="warning",
        description="文件上传失败率高",
    ),
    AlertRule(
        name="DiskSpaceRunningOut",
        metric="system_disk_usage_bytes",
        condition=">",
        threshold=9e11,  # 900GB（假设总共 1TB）
        duration="5m",
        severity="critical",
        description="磁盘空间即将用尽",
    ),

    # SSE 连接告警
    AlertRule(
        name="HighSSEConnectionCount",
        metric="sse_connections_active",
        condition=">",
        threshold=500,
        duration="5m",
        severity="warning",
        description="SSE 活跃连接过多",
    ),

    # 缓存告警
    AlertRule(
        name="LowCacheHitRate",
        metric="cache_hits_total",
        condition="<",
        threshold=80.0,  # 命中率低于 80%
        duration="10m",
        severity="info",
        description="缓存命中率低",
    ),

    # 系统资源告警
    AlertRule(
        name="HighMemoryUsage",
        metric="system_memory_usage_bytes",
        condition=">",
        threshold=8e9,  # 8GB（假设总共 16GB）
        duration="5m",
        severity="warning",
        description="内存使用率过高",
    ),
    AlertRule(
        name="HighCPUUsage",
        metric="system_cpu_usage_percent",
        condition=">",
        threshold=80.0,  # CPU 使用率超过 80%
        duration="5m",
        severity="warning",
        description="CPU 使用率过高",
    ),
]


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []

    def check_alert_rules(self) -> List[Alert]:
        """检查所有告警规则"""
        new_alerts = []

        # 获取 Prometheus 指标
        metrics_text = get_metrics_text()

        for rule in ALERT_RULES:
            if not rule.enabled:
                continue

            # 这里应该实现真实的指标评估逻辑
            # 现在只是示例框架
            alert = self._evaluate_rule(rule, metrics_text)
            if alert:
                new_alerts.append(alert)

        # 更新活跃告警
        self.active_alerts = new_alerts
        self.alert_history.extend(new_alerts)

        return new_alerts

    def _evaluate_rule(self, rule: AlertRule, metrics_text: str) -> Optional[Alert]:
        """评估单个规则"""
        # 这是一个简化的实现
        # 实际应该从指标中提取值并进行比较
        return None

    def send_alert(self, alert: Alert):
        """发送告警通知"""
        message = f"""
告警: {alert.rule_name}
严重级别: {alert.severity}
指标: {alert.metric_name}
当前值: {alert.value}
阈值: {alert.threshold}
描述: {alert.message}
时间: {alert.timestamp}
"""

        logger.warning("alert_triggered", alert=alert.dict())

        # 这里可以集成通知服务
        # - 邮件通知
        # - Slack 通知
        # - 钉钉通知
        # - PagerDuty 集成

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return self.active_alerts

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """获取告警历史"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [a for a in self.alert_history if a.timestamp >= cutoff]

    def resolve_alert(self, rule_name: str):
        """解除告警"""
        self.active_alerts = [a for a in self.active_alerts if a.rule_name != rule_name]


# 全局告警管理器
alert_manager = AlertManager()


# Prometheus 告警规则文件格式 (YAML)
PROMETHEUS_RULES_YAML = """
groups:
  - name: application_alerts
    interval: 30s
    rules:
      # HTTP 性能告警
      - alert: HighHTTPErrorRate
        expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "HTTP 错误率过高"
          description: "{{ $labels.endpoint }} 在最近 5 分钟内的错误率超过 1 req/s"

      - alert: HighHTTPLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "HTTP 请求延迟过高"
          description: "{{ $labels.endpoint }} 的 95% 延迟超过 5 秒"

      # 数据库告警
      - alert: HighDBQueryTime
        expr: avg(rate(db_query_duration_seconds_sum[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "数据库查询时间过长"
          description: "平均查询时间: {{ $value | humanizeDuration }}"

      - alert: HighDBSlowQueries
        expr: rate(db_slow_queries_total[5m]) > 0.33
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "数据库慢查询过多"
          description: "{{ $labels.query_type }} 慢查询率: {{ $value | humanizePercentage }}"

      - alert: DBConnectionPoolExhausted
        expr: db_connection_pool_checked_out > 40
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "数据库连接池即将耗尽"
          description: "已检出 {{ $value }} / 50 个连接"

      # 任务处理告警
      - alert: LowTaskSuccessRate
        expr: task_success_rate < 95
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "任务成功率下降"
          description: "当前成功率: {{ $value | humanizePercentage }}"

      - alert: HighTaskQueueSize
        expr: task_queue_size > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "任务队列堆积"
          description: "{{ $labels.status }} 状态任务数: {{ $value }}"

      - alert: LongTaskProcessingTime
        expr: task_average_duration_minutes > 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "任务处理时间过长"
          description: "平均处理时间: {{ $value | humanizeDuration }}m"

      # 系统资源告警
      - alert: HighMemoryUsage
        expr: system_memory_usage_bytes > 8e9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高"
          description: "已使用: {{ $value | humanize }}B"

      - alert: HighCPUUsage
        expr: system_cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率过高"
          description: "当前 CPU 使用率: {{ $value | humanizePercentage }}"

      - alert: DiskSpaceRunningOut
        expr: system_disk_usage_bytes > 9e11
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "磁盘空间即将用尽"
          description: "已使用: {{ $value | humanize }}B / 总计: 1TB"
"""
