"""
结构化日志模块
提供统一的日志格式、trace_id 跟踪和结构化输出
"""

import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger

# 上下文变量，用于跟踪请求
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
delivery_id_var: ContextVar[Optional[str]] = ContextVar("delivery_id", default=None)


class StructuredFormatter(jsonlogger.JsonFormatter):
    """结构化日志格式化器"""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """添加自定义字段到日志记录"""
        super().add_fields(log_record, record, message_dict)

        # 添加时间戳
        log_record["timestamp"] = time.time()
        log_record["timestamp_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime())

        # 添加日志级别
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        # 添加上下文信息
        log_record["trace_id"] = trace_id_var.get()
        log_record["request_id"] = request_id_var.get()
        log_record["delivery_id"] = delivery_id_var.get()

        # 添加进程信息
        log_record["pid"] = os.getpid()

        # 添加位置信息
        log_record["file"] = record.filename
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # 确保消息字段存在
        if "message" not in log_record:
            log_record["message"] = record.getMessage()


class RequestContextFilter(logging.Filter):
    """请求上下文过滤器，确保上下文信息正确传递"""

    def filter(self, record: logging.LogRecord) -> bool:
        # 注入上下文信息到record
        record.trace_id = trace_id_var.get()
        record.request_id = request_id_var.get()
        record.delivery_id = delivery_id_var.get()
        return True


def setup_structured_logging(level: str = None, format_type: str = "json", include_console: bool = True) -> None:
    """
    设置结构化日志

    Args:
        level: 日志级别
        format_type: 日志格式 (json/text)
        include_console: 是否包含控制台输出
    """
    # 确定日志级别
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()

    # 清除现有的handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 设置日志级别
    root_logger.setLevel(getattr(logging, level))

    # 创建格式化器
    if format_type == "json":
        formatter = StructuredFormatter(fmt="%(timestamp)s %(level)s %(name)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    else:
        # 文本格式，用于开发
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s [trace:%(trace_id)s]",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # 控制台处理器
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(console_handler)

    # 文件处理器（可选）
    log_file = os.getenv("LOG_FILE")
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(file_handler)

    # 禁用第三方库的详细日志
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def set_trace_id(trace_id: str = None) -> str:
    """
    设置trace_id

    Args:
        trace_id: 指定的trace_id，如果为None则生成新的

    Returns:
        设置的trace_id
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())

    trace_id_var.set(trace_id)
    return trace_id


def set_request_id(request_id: str) -> None:
    """设置request_id"""
    request_id_var.set(request_id)


def set_delivery_id(delivery_id: str) -> None:
    """设置delivery_id"""
    delivery_id_var.set(delivery_id)


def get_current_context() -> Dict[str, Any]:
    """获取当前日志上下文"""
    return {"trace_id": trace_id_var.get(), "request_id": request_id_var.get(), "delivery_id": delivery_id_var.get()}


def log_webhook_request(
    provider: str,
    event_type: str,
    delivery_id: str,
    status: str,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    记录webhook请求日志

    Args:
        provider: 提供商 (github/gitee/notion)
        event_type: 事件类型
        delivery_id: 投递ID
        status: 状态 (received/processing/success/failed/duplicate)
        duration_ms: 处理时长（毫秒）
        error: 错误信息
        extra_data: 额外数据
    """
    logger = logging.getLogger("webhook")

    log_data = {
        "event": "webhook_request",
        "provider": provider,
        "event_type": event_type,
        "delivery_id": delivery_id,
        "status": status,
        "duration_ms": duration_ms,
        "error": error,
    }

    if extra_data:
        log_data.update(extra_data)

    if status == "failed" or error:
        logger.error("webhook_request", extra=log_data)
    elif status == "duplicate":
        logger.info("webhook_request", extra=log_data)
    else:
        logger.info("webhook_request", extra=log_data)


def log_api_call(
    service: str,
    operation: str,
    status: str,
    duration_ms: Optional[float] = None,
    response_size: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """
    记录API调用日志

    Args:
        service: 服务名称 (github/notion)
        operation: 操作名称
        status: 状态 (success/failed/timeout)
        duration_ms: 调用时长（毫秒）
        response_size: 响应大小（字节）
        error: 错误信息
    """
    logger = logging.getLogger("api")

    log_data = {
        "event": "api_call",
        "service": service,
        "operation": operation,
        "status": status,
        "duration_ms": duration_ms,
        "response_size": response_size,
        "error": error,
    }

    if status == "failed" or error:
        logger.error("api_call", extra=log_data)
    else:
        logger.info("api_call", extra=log_data)


def log_business_event(
    event_type: str,
    entity_type: str,
    entity_id: str,
    action: str,
    status: str,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    记录业务事件日志

    Args:
        event_type: 事件类型 (sync/process/transform)
        entity_type: 实体类型 (issue/pr/page)
        entity_id: 实体ID
        action: 动作 (create/update/delete)
        status: 状态 (success/failed)
        extra_data: 额外数据
    """
    logger = logging.getLogger("business")

    log_data = {
        "event": "business_event",
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "status": status,
    }

    if extra_data:
        log_data.update(extra_data)

    if status == "failed":
        logger.error("business_event", extra=log_data)
    else:
        logger.info("business_event", extra=log_data)


def log_performance_metric(
    operation: str, duration_ms: float, success: bool = True, extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    记录性能指标日志

    Args:
        operation: 操作名称
        duration_ms: 执行时长（毫秒）
        success: 是否成功
        extra_data: 额外数据
    """
    logger = logging.getLogger("performance")

    log_data = {"event": "performance_metric", "operation": operation, "duration_ms": duration_ms, "success": success}

    if extra_data:
        log_data.update(extra_data)

    # 性能日志通常用INFO级别
    logger.info("performance_metric", extra=log_data)


class LoggingContextManager:
    """日志上下文管理器"""

    def __init__(self, trace_id: str = None, request_id: str = None, delivery_id: str = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.request_id = request_id
        self.delivery_id = delivery_id

        # 保存原始上下文
        self.original_trace_id = None
        self.original_request_id = None
        self.original_delivery_id = None

    def __enter__(self):
        # 保存原始上下文
        self.original_trace_id = trace_id_var.get()
        self.original_request_id = request_id_var.get()
        self.original_delivery_id = delivery_id_var.get()

        # 设置新上下文
        trace_id_var.set(self.trace_id)
        if self.request_id:
            request_id_var.set(self.request_id)
        if self.delivery_id:
            delivery_id_var.set(self.delivery_id)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始上下文
        trace_id_var.set(self.original_trace_id)
        request_id_var.set(self.original_request_id)
        delivery_id_var.set(self.original_delivery_id)


# 便捷函数
def with_logging_context(trace_id: str = None, request_id: str = None, delivery_id: str = None):
    """创建日志上下文管理器的便捷函数"""
    return LoggingContextManager(trace_id, request_id, delivery_id)


# 导出主要函数和类
__all__ = [
    "setup_structured_logging",
    "set_trace_id",
    "set_request_id",
    "set_delivery_id",
    "get_current_context",
    "log_webhook_request",
    "log_api_call",
    "log_business_event",
    "log_performance_metric",
    "LoggingContextManager",
    "with_logging_context",
]
