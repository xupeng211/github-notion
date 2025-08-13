"""
审计日志模块
"""
import json
import logging
import time
from typing import Dict, Any, Optional
from fastapi import Request

# 创建专门的审计日志记录器
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# 如果没有处理器，添加一个
if not audit_logger.handlers:
    from pythonjsonlogger import jsonlogger
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)
    audit_logger.addHandler(handler)
    audit_logger.propagate = False


def log_webhook_event(
    request: Request,
    event_type: str,
    issue_id: str,
    result: str,
    message: str = "",
    duration_ms: Optional[float] = None,
    payload_size: Optional[int] = None
):
    """记录 webhook 事件的审计日志"""
    
    audit_data = {
        "event": "webhook_processed",
        "timestamp": time.time(),
        "client_ip": getattr(request.client, "host", "unknown") if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
        "event_type": event_type,
        "issue_id": issue_id,
        "result": result,  # success, skip, fail
        "message": message,
    }
    
    if duration_ms is not None:
        audit_data["duration_ms"] = duration_ms
    
    if payload_size is not None:
        audit_data["payload_size_bytes"] = payload_size
    
    # 添加请求头信息（隐藏敏感信息）
    headers = dict(request.headers)
    if "x-gitee-token" in headers:
        headers["x-gitee-token"] = "[REDACTED]"
    if "authorization" in headers:
        headers["authorization"] = "[REDACTED]"
    
    audit_data["request_headers"] = headers
    
    audit_logger.info("webhook_event", extra=audit_data)


def log_api_call(
    operation: str,
    target: str,
    result: str,
    duration_ms: Optional[float] = None,
    error: str = "",
    metadata: Optional[Dict[str, Any]] = None
):
    """记录 API 调用的审计日志"""
    
    audit_data = {
        "event": "api_call",
        "timestamp": time.time(),
        "operation": operation,  # create_page, update_page, query_database
        "target": target,  # notion, database
        "result": result,  # success, error
        "error": error,
    }
    
    if duration_ms is not None:
        audit_data["duration_ms"] = duration_ms
    
    if metadata:
        audit_data["metadata"] = metadata
    
    audit_logger.info("api_call", extra=audit_data)


def log_security_event(
    event_type: str,
    client_ip: str,
    details: str,
    severity: str = "warning"
):
    """记录安全相关事件的审计日志"""
    
    audit_data = {
        "event": "security_event",
        "timestamp": time.time(),
        "event_type": event_type,  # rate_limit_hit, invalid_signature, request_too_large
        "client_ip": client_ip,
        "details": details,
        "severity": severity,  # info, warning, error, critical
    }
    
    if severity == "error":
        audit_logger.error("security_event", extra=audit_data)
    elif severity == "warning":
        audit_logger.warning("security_event", extra=audit_data)
    else:
        audit_logger.info("security_event", extra=audit_data)


def log_system_event(
    event_type: str,
    details: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """记录系统事件的审计日志"""
    
    audit_data = {
        "event": "system_event",
        "timestamp": time.time(),
        "event_type": event_type,  # startup, shutdown, deadletter_replay
        "details": details,
    }
    
    if metadata:
        audit_data["metadata"] = metadata
    
    audit_logger.info("system_event", extra=audit_data) 