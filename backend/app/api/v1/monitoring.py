"""
监控和指标 API 端点

支持：
1. Prometheus 指标导出
2. 告警查询
3. 系统健康状态
4. 性能统计
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional

from app.dependencies import get_current_user
from app.models.user import User
from app.core.metrics import (
    get_metrics_text,
    http_requests_total,
    db_connection_pool_checked_out,
    task_current_active,
    sse_connections_active,
    system_memory_usage_bytes,
)
from app.core.alerting import alert_manager, PROMETHEUS_RULES_YAML


router = APIRouter(prefix="/monitoring", tags=["监控"])


class AlertResponse(BaseModel):
    """告警响应"""
    rule_name: str
    metric_name: str
    value: float
    threshold: float
    severity: str
    timestamp: str
    message: str


class HealthStatus(BaseModel):
    """健康状态"""
    status: str  # healthy, degraded, unhealthy
    timestamp: str
    components: dict


class SystemStats(BaseModel):
    """系统统计"""
    uptime_seconds: int
    memory_usage_mb: int
    memory_limit_mb: int
    cpu_usage_percent: float
    disk_usage_percent: float
    http_requests_per_minute: float
    db_connections_active: int
    db_connections_total: int
    active_tasks: int
    sse_connections: int


def _check_admin(current_user: User = Depends(get_current_user)):
    """检查是否为管理员"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    return current_user


@router.get("/metrics")
async def get_prometheus_metrics(_: User = Depends(_check_admin)):
    """
    获取 Prometheus 格式的指标

    用于 Prometheus scrape
    """
    return Response(
        content=get_metrics_text(),
        media_type="text/plain; charset=utf-8"
    )


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    severity: Optional[str] = None,
    _: User = Depends(_check_admin),
):
    """获取活跃告警"""
    alerts = alert_manager.get_active_alerts()

    if severity:
        alerts = [a for a in alerts if a.severity == severity]

    return [
        AlertResponse(
            rule_name=a.rule_name,
            metric_name=a.metric_name,
            value=a.value,
            threshold=a.threshold,
            severity=a.severity,
            timestamp=a.timestamp.isoformat(),
            message=a.message,
        )
        for a in alerts
    ]


@router.get("/alerts/history")
async def get_alerts_history(
    hours: int = 24,
    _: User = Depends(_check_admin),
):
    """获取告警历史"""
    alerts = alert_manager.get_alert_history(hours=hours)
    return {
        "period_hours": hours,
        "total_alerts": len(alerts),
        "alerts": [
            {
                "rule_name": a.rule_name,
                "severity": a.severity,
                "timestamp": a.timestamp.isoformat(),
                "message": a.message,
            }
            for a in alerts
        ]
    }


@router.post("/alerts/{rule_name}/resolve")
async def resolve_alert(
    rule_name: str,
    _: User = Depends(_check_admin),
):
    """解除特定告警"""
    alert_manager.resolve_alert(rule_name)
    return {"status": "resolved", "rule_name": rule_name}


@router.get("/alerts/check")
async def check_alerts(_: User = Depends(_check_admin)):
    """主动检查一次告警规则"""
    alerts = alert_manager.check_alert_rules()
    return {
        "checked_at": datetime.utcnow().isoformat(),
        "alert_count": len(alerts),
        "alerts": [a.dict() for a in alerts]
    }


@router.get("/rules/prometheus")
async def get_prometheus_rules(_: User = Depends(_check_admin)):
    """获取 Prometheus 告警规则配置"""
    return Response(
        content=PROMETHEUS_RULES_YAML,
        media_type="text/yaml"
    )


@router.get("/health", response_model=HealthStatus)
async def get_health_status():
    """获取系统健康状态"""
    from datetime import datetime
    import os
    import psutil

    status = "healthy"
    components = {}

    # 检查数据库连接
    try:
        # 这里应该实际检查数据库连接
        components["database"] = {"status": "healthy"}
    except:
        components["database"] = {"status": "unhealthy"}
        status = "degraded"

    # 检查内存
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > 90:
        components["memory"] = {"status": "unhealthy", "percent": memory_percent}
        status = "degraded"
    else:
        components["memory"] = {"status": "healthy", "percent": memory_percent}

    # 检查磁盘
    disk_percent = psutil.disk_usage("/").percent
    if disk_percent > 95:
        components["disk"] = {"status": "unhealthy", "percent": disk_percent}
        status = "unhealthy"
    else:
        components["disk"] = {"status": "healthy", "percent": disk_percent}

    return HealthStatus(
        status=status,
        timestamp=datetime.utcnow().isoformat(),
        components=components
    )


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(_: User = Depends(_check_admin)):
    """获取系统统计信息"""
    import psutil
    from datetime import datetime, timedelta

    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1)
    disk = psutil.disk_usage("/")

    # 计算一些基本统计
    # 注：这些是简化的实现，实际应该从 Prometheus 中查询
    try:
        http_rate = 0  # 应该从指标中计算
        db_connections = int(db_connection_pool_checked_out._value.get() or 0)
        active_tasks = int(task_current_active._value.get() or 0)
        sse_conns = int(sse_connections_active._value.get() or 0)
    except:
        http_rate = 0
        db_connections = 0
        active_tasks = 0
        sse_conns = 0

    return SystemStats(
        uptime_seconds=int(datetime.utcnow().timestamp()),
        memory_usage_mb=int(memory.used / 1024 / 1024),
        memory_limit_mb=int(memory.total / 1024 / 1024),
        cpu_usage_percent=float(cpu_percent),
        disk_usage_percent=float(disk.percent),
        http_requests_per_minute=http_rate,
        db_connections_active=db_connections,
        db_connections_total=50,  # 根据配置
        active_tasks=active_tasks,
        sse_connections=sse_conns,
    )


@router.get("/dashboard/data")
async def get_dashboard_data(_: User = Depends(_check_admin)):
    """获取仪表板数据（用于实时更新）"""
    from datetime import datetime

    # 收集关键指标
    try:
        stats = await get_system_stats(_)
        health = await get_health_status()
        alerts = alert_manager.get_active_alerts()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": stats.dict(),
            "health": health.dict(),
            "alerts": {
                "active": len(alerts),
                "by_severity": {
                    "critical": len([a for a in alerts if a.severity == "critical"]),
                    "warning": len([a for a in alerts if a.severity == "warning"]),
                    "info": len([a for a in alerts if a.severity == "info"]),
                }
            }
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


# 导入 datetime 用于类型提示
from datetime import datetime
