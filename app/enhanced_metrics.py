"""
增强监控指标模块
提供详细的业务和技术指标，支持 Prometheus 导出
"""

import logging
import os
import time
from contextlib import contextmanager
from typing import Dict, Optional

from prometheus_client import CollectorRegistry, Counter, Enum, Gauge, Histogram, Info, start_http_server

logger = logging.getLogger(__name__)

# 检查是否禁用指标收集
DISABLE_METRICS = os.getenv("DISABLE_METRICS", "").lower() in ("1", "true", "yes")

# 创建自定义注册表（可选，用于隔离指标）
if not DISABLE_METRICS:
    METRICS_REGISTRY = CollectorRegistry()
else:
    METRICS_REGISTRY = None


def _noop(*args, **kwargs):
    """空操作函数，用于禁用指标时的占位符"""


class _NoopMetric:
    """空操作指标类，用于禁用指标时的占位符"""

    def inc(self, *args, **kwargs):
        pass

    def observe(self, *args, **kwargs):
        pass

    def labels(self, *args, **kwargs):
        return self

    def set(self, *args, **kwargs):
        pass


# Webhook 请求指标
WEBHOOK_REQUESTS_TOTAL = (
    Counter(
        "webhook_requests_total",
        "Total number of webhook requests received",
        ["provider", "event_type", "status"],  # provider: github/gitee/notion
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

WEBHOOK_REQUEST_DURATION = (
    Histogram(
        "webhook_request_duration_seconds",
        "Time spent processing webhook requests",
        ["provider", "event_type"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

# 同步事件统计
SYNC_EVENTS_TOTAL = (
    Counter(
        "sync_events_total",
        "Total number of sync events processed",
        ["source_platform", "target_platform", "entity_type", "action", "status"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

SYNC_EVENT_DURATION = (
    Histogram(
        "sync_event_duration_seconds",
        "Time spent processing sync events",
        ["source_platform", "target_platform", "entity_type"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

# 幂等性统计
IDEMPOTENCY_CHECKS_TOTAL = (
    Counter(
        "idempotency_checks_total",
        "Total number of idempotency checks performed",
        ["provider", "result"],  # result: duplicate/unique/error
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

DUPLICATE_EVENTS_TOTAL = (
    Counter(
        "duplicate_events_total",
        "Total number of duplicate events detected",
        ["provider", "duplicate_type"],  # duplicate_type: event_id/content_hash
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

# === 外部 API 指标 ===

# GitHub API 调用
GITHUB_API_CALLS_TOTAL = (
    Counter(
        "github_api_calls_total",
        "Total number of GitHub API calls",
        ["method", "endpoint", "status_code"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

GITHUB_API_DURATION = (
    Histogram(
        "github_api_duration_seconds",
        "Time spent on GitHub API calls",
        ["method", "endpoint"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

GITHUB_API_RATE_LIMIT = (
    Gauge("github_api_rate_limit_remaining", "GitHub API rate limit remaining", registry=METRICS_REGISTRY)
    if not DISABLE_METRICS
    else _NoopMetric()
)

# Notion API 调用
NOTION_API_CALLS_TOTAL = (
    Counter(
        "notion_api_calls_total",
        "Total number of Notion API calls",
        ["method", "endpoint", "status_code"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

NOTION_API_DURATION = (
    Histogram(
        "notion_api_duration_seconds",
        "Time spent on Notion API calls",
        ["method", "endpoint"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

NOTION_API_RATE_LIMIT = (
    Gauge("notion_api_rate_limit_remaining", "Notion API rate limit remaining (estimated)", registry=METRICS_REGISTRY)
    if not DISABLE_METRICS
    else _NoopMetric()
)

# === 系统指标 ===

# 死信队列
DEADLETTER_QUEUE_SIZE = (
    Gauge("deadletter_queue_size", "Current size of dead letter queue", registry=METRICS_REGISTRY)
    if not DISABLE_METRICS
    else _NoopMetric()
)

DEADLETTER_REPLAYS_TOTAL = (
    Counter(
        "deadletter_replays_total",
        "Total number of dead letter replays",
        ["status"],  # status: success/failure
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

# 数据库操作
DB_OPERATIONS_TOTAL = (
    Counter(
        "db_operations_total",
        "Total number of database operations",
        ["operation", "table", "status"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

DB_OPERATION_DURATION = (
    Histogram(
        "db_operation_duration_seconds",
        "Time spent on database operations",
        ["operation", "table"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

# 安全相关
SECURITY_EVENTS_TOTAL = (
    Counter(
        "security_events_total",
        "Total number of security events",
        ["event_type", "provider", "result"],  # event_type: signature_check/replay_check
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

# 应用健康状态
APP_HEALTH_STATUS = (
    Enum(
        "app_health_status",
        "Application health status",
        states=["healthy", "degraded", "unhealthy"],
        registry=METRICS_REGISTRY,
    )
    if not DISABLE_METRICS
    else _NoopMetric()
)

# 应用信息
APP_INFO = (
    Info("app_info", "Application information", registry=METRICS_REGISTRY) if not DISABLE_METRICS else _NoopMetric()
)

# === 监控辅助功能 ===


@contextmanager
def track_duration(metric, labels: Optional[Dict[str, str]] = None):
    """
    跟踪操作耗时的上下文管理器

    使用示例:
    with track_duration(WEBHOOK_REQUEST_DURATION, {"provider": "github"}):
        # 处理webhook
        pass
    """
    if DISABLE_METRICS:
        yield
        return

    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        if labels:
            metric.labels(**labels).observe(duration)
        else:
            metric.observe(duration)


def record_webhook_request(provider: str, event_type: str, status: str, duration: float):
    """记录 webhook 请求指标"""
    if DISABLE_METRICS:
        return

    WEBHOOK_REQUESTS_TOTAL.labels(provider=provider, event_type=event_type, status=status).inc()

    WEBHOOK_REQUEST_DURATION.labels(provider=provider, event_type=event_type).observe(duration)


def record_sync_event(source: str, target: str, entity_type: str, action: str, status: str, duration: float):
    """记录同步事件指标"""
    if DISABLE_METRICS:
        return

    SYNC_EVENTS_TOTAL.labels(
        source_platform=source, target_platform=target, entity_type=entity_type, action=action, status=status
    ).inc()

    SYNC_EVENT_DURATION.labels(source_platform=source, target_platform=target, entity_type=entity_type).observe(
        duration
    )


def record_api_call(
    api_type: str,
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
    rate_limit_remaining: Optional[int] = None,
):
    """记录外部 API 调用指标"""
    if DISABLE_METRICS:
        return

    if api_type == "github":
        GITHUB_API_CALLS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()

        GITHUB_API_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        if rate_limit_remaining is not None:
            GITHUB_API_RATE_LIMIT.set(rate_limit_remaining)

    elif api_type == "notion":
        NOTION_API_CALLS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()

        NOTION_API_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        if rate_limit_remaining is not None:
            NOTION_API_RATE_LIMIT.set(rate_limit_remaining)


def record_idempotency_check(provider: str, result: str, duplicate_type: Optional[str] = None):
    """记录幂等性检查指标"""
    if DISABLE_METRICS:
        return

    IDEMPOTENCY_CHECKS_TOTAL.labels(provider=provider, result=result).inc()

    if result == "duplicate" and duplicate_type:
        DUPLICATE_EVENTS_TOTAL.labels(provider=provider, duplicate_type=duplicate_type).inc()


def record_security_event(event_type: str, provider: str, result: str):
    """记录安全事件指标"""
    if DISABLE_METRICS:
        return

    SECURITY_EVENTS_TOTAL.labels(event_type=event_type, provider=provider, result=result).inc()


# 已移至下方新版本，支持provider和event_type标签


def record_deadletter_replay(status: str):
    """记录死信重放"""
    if DISABLE_METRICS:
        return
    DEADLETTER_REPLAYS_TOTAL.labels(status=status).inc()


def record_db_operation(operation: str, table: str, status: str, duration: float):
    """记录数据库操作"""
    if DISABLE_METRICS:
        return

    DB_OPERATIONS_TOTAL.labels(operation=operation, table=table, status=status).inc()

    DB_OPERATION_DURATION.labels(operation=operation, table=table).observe(duration)


def update_app_health(status: str):
    """更新应用健康状态"""
    if DISABLE_METRICS:
        return
    APP_HEALTH_STATUS.state(status)


def set_app_info(version: str, environment: str, python_version: str):
    """设置应用基本信息指标"""
    if DISABLE_METRICS:
        return

    APP_INFO.info({"version": version, "environment": environment, "python_version": python_version})


# === 初始化函数 ===


def initialize_metrics():
    """初始化指标系统"""
    if DISABLE_METRICS:
        logger.info("metrics_disabled")
        return

    # 设置应用信息
    import sys

    set_app_info(
        version=os.getenv("APP_VERSION", "1.0.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )

    # 设置初始健康状态
    update_app_health("healthy")

    logger.info("enhanced_metrics_initialized")


def start_metrics_server(port: int = 9090):
    """启动指标服务器（可选）"""
    if DISABLE_METRICS:
        return

    try:
        start_http_server(port, registry=METRICS_REGISTRY)
        logger.info("metrics_server_started", extra={"port": port})
    except Exception as e:
        logger.error("metrics_server_start_failed", extra={"error": str(e)})


# 新增的关键指标

# 成功率和失败率指标
WEBHOOK_SUCCESS_RATE = (
    Gauge("webhook_success_rate_percent", "Webhook处理成功率（百分比）", ["provider"], registry=METRICS_REGISTRY)
    if METRICS_REGISTRY
    else None
)

WEBHOOK_FAILURE_RATE = (
    Gauge("webhook_failure_rate_percent", "Webhook处理失败率（百分比）", ["provider"], registry=METRICS_REGISTRY)
    if METRICS_REGISTRY
    else None
)

# 处理时延指标
WEBHOOK_PROCESSING_DURATION = (
    Histogram(
        "webhook_processing_duration_seconds",
        "Webhook处理时延分布",
        ["provider", "event_type", "status"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float("inf")],
        registry=METRICS_REGISTRY,
    )
    if METRICS_REGISTRY
    else None
)

# API调用失败率
API_CALL_FAILURES = (
    Counter(
        "api_call_failures_total",
        "外部API调用失败次数",
        ["service", "operation", "error_type"],
        registry=METRICS_REGISTRY,
    )
    if METRICS_REGISTRY
    else None
)

API_CALL_DURATION = (
    Histogram(
        "api_call_duration_seconds",
        "外部API调用时延",
        ["service", "operation"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float("inf")],
        registry=METRICS_REGISTRY,
    )
    if METRICS_REGISTRY
    else None
)

# 死信队列指标
DEADLETTER_QUEUE_SIZE = (
    Gauge("deadletter_queue_size", "死信队列当前大小", ["provider", "event_type"], registry=METRICS_REGISTRY)
    if METRICS_REGISTRY
    else None
)

DEADLETTER_EVENTS_TOTAL = (
    Counter(
        "deadletter_events_total",
        "进入死信队列的事件总数",
        ["provider", "event_type", "error_type"],
        registry=METRICS_REGISTRY,
    )
    if METRICS_REGISTRY
    else None
)

# 幂等性指标增强
IDEMPOTENCY_CACHE_HITS = (
    Counter("idempotency_cache_hits_total", "幂等性缓存命中次数", ["provider"], registry=METRICS_REGISTRY)
    if METRICS_REGISTRY
    else None
)

IDEMPOTENCY_CACHE_SIZE = (
    Gauge("idempotency_cache_size", "幂等性缓存当前大小", registry=METRICS_REGISTRY) if METRICS_REGISTRY else None
)

# 业务指标
SYNC_SUCCESS_RATE = (
    Gauge("sync_success_rate_percent", "同步成功率（百分比）", ["provider", "entity_type"], registry=METRICS_REGISTRY)
    if METRICS_REGISTRY
    else None
)

ENTITY_PROCESSING_TIME = (
    Histogram(
        "entity_processing_time_seconds",
        "实体处理时间分布",
        ["entity_type", "action"],
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")],
        registry=METRICS_REGISTRY,
    )
    if METRICS_REGISTRY
    else None
)


def record_webhook_processing_duration(provider: str, event_type: str, status: str, duration: float):
    """记录webhook处理时延"""
    if WEBHOOK_PROCESSING_DURATION:
        WEBHOOK_PROCESSING_DURATION.labels(provider=provider, event_type=event_type, status=status).observe(duration)


def record_api_call_metrics(service: str, operation: str, duration: float, success: bool, error_type: str = None):
    """记录API调用指标"""
    if API_CALL_DURATION:
        API_CALL_DURATION.labels(service=service, operation=operation).observe(duration)

    if not success and API_CALL_FAILURES:
        API_CALL_FAILURES.labels(service=service, operation=operation, error_type=error_type or "unknown").inc()


def record_deadletter_event(provider: str, event_type: str, error_type: str):
    """记录死信队列事件"""
    if DEADLETTER_EVENTS_TOTAL:
        DEADLETTER_EVENTS_TOTAL.labels(provider=provider, event_type=event_type, error_type=error_type).inc()


def update_deadletter_queue_size(provider: str, event_type: str, size: int):
    """更新死信队列大小"""
    if DEADLETTER_QUEUE_SIZE:
        DEADLETTER_QUEUE_SIZE.labels(provider=provider, event_type=event_type).set(size)


def record_idempotency_cache_hit(provider: str):
    """记录幂等性缓存命中"""
    if IDEMPOTENCY_CACHE_HITS:
        IDEMPOTENCY_CACHE_HITS.labels(provider=provider).inc()


def update_idempotency_cache_size(size: int):
    """更新幂等性缓存大小"""
    if IDEMPOTENCY_CACHE_SIZE:
        IDEMPOTENCY_CACHE_SIZE.set(size)


def record_entity_processing_time(entity_type: str, action: str, duration: float):
    """记录实体处理时间"""
    if ENTITY_PROCESSING_TIME:
        ENTITY_PROCESSING_TIME.labels(entity_type=entity_type, action=action).observe(duration)


def update_success_rates():
    """更新成功率指标"""
    if not METRICS_REGISTRY:
        return

    try:
        from datetime import datetime, timedelta

        from app.models import SessionLocal, SyncEvent

        # 计算最近1小时的成功率
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        with SessionLocal() as db:
            for provider in ["github", "gitee", "notion"]:
                # 查询最近1小时的事件
                recent_events = (
                    db.query(SyncEvent)
                    .filter(SyncEvent.provider == provider, SyncEvent.created_at >= one_hour_ago)
                    .all()
                )

                if recent_events:
                    total_count = len(recent_events)
                    success_count = sum(1 for event in recent_events if event.processed and not event.error_message)

                    success_rate = (success_count / total_count) * 100
                    failure_rate = 100 - success_rate

                    if WEBHOOK_SUCCESS_RATE:
                        WEBHOOK_SUCCESS_RATE.labels(provider=provider).set(success_rate)
                    if WEBHOOK_FAILURE_RATE:
                        WEBHOOK_FAILURE_RATE.labels(provider=provider).set(failure_rate)

    except Exception as e:
        logger.error("Failed to update success rates", extra={"error": str(e)})


# 新增的导出列表
ENHANCED_METRICS_EXPORTS = [
    "record_webhook_processing_duration",
    "record_api_call_metrics",
    "record_deadletter_event",
    "update_deadletter_queue_size",
    "record_idempotency_cache_hit",
    "update_idempotency_cache_size",
    "record_entity_processing_time",
    "update_success_rates",
]
