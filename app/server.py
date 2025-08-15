from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import make_asgi_app
from app.enhanced_metrics import (
    METRICS_REGISTRY, initialize_metrics,
    record_webhook_request, record_idempotency_check, record_security_event
)
from pydantic import ValidationError
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from app.middleware import PrometheusMiddleware
from app.models import SessionLocal, deadletter_count
from app.schemas import GiteeWebhookPayload
from app.service import RATE_LIMIT_HITS_TOTAL, process_gitee_event, replay_deadletters_once, start_deadletter_scheduler
from app.webhook_security import validate_webhook_security
from app.idempotency import IdempotencyManager

# 新增导入
from app.schemas import GitHubWebhookPayload, NotionWebhookPayload
from app.service import process_notion_event, async_process_github_event
import json


# Simple in-memory rate limiter (token bucket-like) per process


class SimpleRateLimiter:
    def __init__(self, max_per_minute: int | None):
        self.max_per_minute = max_per_minute
        self.timestamps = deque()  # store request timestamps (seconds)

    def allow(self) -> bool:
        if not self.max_per_minute or self.max_per_minute <= 0:
            return True
        now = time.time()
        window_start = now - 60
        while self.timestamps and self.timestamps[0] < window_start:
            self.timestamps.popleft()
        if len(self.timestamps) < self.max_per_minute:
            self.timestamps.append(now)
            return True
        return False


rate_limiter = SimpleRateLimiter(max_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "0") or 0))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # startup
    # 注意：数据库初始化现在通过 alembic 管理，不再使用 init_db()
    # 部署时请运行: alembic upgrade head
    scheduler = start_deadletter_scheduler()
    try:
        yield
    finally:
        # shutdown
        try:
            if scheduler:
                scheduler.shutdown(wait=False)
        except Exception:
            pass

app = FastAPI(
    title="Gitee-Notion 同步服务",
    description="自动同步 Gitee issues 到 Notion 数据库",
    version="1.0.0",
    lifespan=lifespan
)

# 添加安全和限制中间件

# 添加 Prometheus 监控中间件
app.add_middleware(PrometheusMiddleware)

# 添加请求大小限制
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "1048576"))  # 1MB 默认


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """请求大小限制中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查 Content-Length 头
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE:
            return Response(
                content=f"Request too large. Maximum size: {MAX_REQUEST_SIZE} bytes",
                status_code=413,
                headers={"content-type": "text/plain"}
            )

        return await call_next(request)


# 添加请求大小限制中间件
app.add_middleware(RequestSizeLimitMiddleware)

# JSON structured logging
logger = logging.getLogger("app")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Simple request id middleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.time()
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "op": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


app.add_middleware(RequestIDMiddleware)

# 全局异常处理器


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """处理 Pydantic 验证错误"""
    request_id = getattr(request.state, "request_id", "unknown")

    # 记录详细的验证错误
    logger.warning(
        "validation_error",
        extra={
            "request_id": request_id,
            "url": str(request.url),
            "method": request.method,
            "error": str(exc),
            "error_count": len(exc.errors()) if hasattr(exc, 'errors') else 1
        }
    )

    return {
        "error": "validation_error",
        "message": "请求数据验证失败",
        "details": str(exc),
        "request_id": request_id
    }


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """处理值错误"""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        "value_error",
        extra={
            "request_id": request_id,
            "url": str(request.url),
            "method": request.method,
            "error": str(exc)
        }
    )

    return {
        "error": "value_error",
        "message": "请求参数错误",
        "details": str(exc),
        "request_id": request_id
    }


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    """处理内部服务器错误"""
    request_id = getattr(request.state, "request_id", "unknown")

    # 记录详细错误信息，包括堆栈跟踪
    import traceback
    logger.error(
        "internal_server_error",
        extra={
            "request_id": request_id,
            "url": str(request.url),
            "method": request.method,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    )

    return {
        "error": "internal_server_error",
        "message": "内部服务器错误，请稍后重试",
        "request_id": request_id
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，捕获所有未处理的异常"""
    request_id = getattr(request.state, "request_id", "unknown")

    # 记录详细错误信息
    import traceback
    logger.error(
        "unhandled_exception",
        extra={
            "request_id": request_id,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "url": str(request.url),
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )

    # 根据异常类型返回适当的响应
    if isinstance(exc, HTTPException):
        # HTTPException 应该由 FastAPI 自动处理，但这里提供备用
        raise exc

    return {
        "error": "unexpected_error",
        "message": "发生了意外错误，请联系管理员",
        "request_id": request_id
    }

# health


@app.get("/health",
         summary="健康检查",
         description="检查服务健康状态，包括数据库连接、Notion API 状态、磁盘空间等",
         response_description="健康检查结果，包含详细的系统状态信息")
async def health():
    """Enhanced health check with deep monitoring"""
    import requests

    # 基础信息
    health_data = {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": os.getenv("ENVIRONMENT", os.getenv("PY_ENV", "development")),
        "app_info": {
            "app": "fastapi",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "version": "1.0.0"
        },
        "checks": {}
    }

    # 检查数据库连接
    try:
        from sqlalchemy import text
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        health_data["checks"]["database"] = {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        health_data["checks"]["database"] = {"status": "error", "message": f"Database error: {str(e)}"}
        health_data["status"] = "degraded"

    # 检查 Notion API 连接
    notion_token = os.getenv("NOTION_TOKEN")
    notion_database_id = os.getenv("NOTION_DATABASE_ID")

    if notion_token:
        try:
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }

            # 检查用户认证
            user_response = requests.get("https://api.notion.com/v1/users/me", headers=headers, timeout=5)
            user_response.raise_for_status()

            # 检查数据库访问权限（如果配置了数据库ID）
            db_accessible = True
            if notion_database_id:
                try:
                    db_response = requests.get(
                        f"https://api.notion.com/v1/databases/{notion_database_id}",
                        headers=headers, timeout=5
                    )
                    db_response.raise_for_status()
                except requests.RequestException:
                    db_accessible = False

            health_data["checks"]["notion_api"] = {
                "status": "ok" if db_accessible else "warning",
                "message": "Notion API connection successful" if db_accessible else "API连接成功但数据库访问受限",
                "version": "2022-06-28",
                "database_accessible": db_accessible,
                "database_id": notion_database_id[:8] + "..." if notion_database_id else None
            }

            if not db_accessible and notion_database_id:
                health_data["status"] = "degraded"

        except requests.RequestException as e:
            health_data["checks"]["notion_api"] = {
                "status": "error",
                "message": f"Notion API error: {str(e)}",
                "version": "2022-06-28"
            }
            health_data["status"] = "degraded"
    else:
        health_data["checks"]["notion_api"] = {
            "status": "warning",
            "message": "Notion API token not configured",
            "version": "2022-06-28"
        }

    # 检查 GitHub API 连接
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        try:
            headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }

            # 检查用户认证和 API 限制
            user_response = requests.get("https://api.github.com/user", headers=headers, timeout=5)
            user_response.raise_for_status()

            # 获取 API 限制信息
            rate_limit_response = requests.get("https://api.github.com/rate_limit", headers=headers, timeout=5)
            rate_limit_data = rate_limit_response.json() if rate_limit_response.status_code == 200 else {}

            remaining = rate_limit_data.get("rate", {}).get("remaining", "unknown")
            limit = rate_limit_data.get("rate", {}).get("limit", "unknown")

            health_data["checks"]["github_api"] = {
                "status": "ok",
                "message": "GitHub API connection successful",
                "rate_limit": {
                    "remaining": remaining,
                    "limit": limit
                }
            }

            # 如果 API 剩余请求数很低，标记为警告
            if isinstance(remaining, int) and remaining < 100:
                health_data["checks"]["github_api"]["status"] = "warning"
                health_data["checks"]["github_api"]["message"] = f"GitHub API rate limit低 ({remaining}/{limit})"

        except requests.RequestException as e:
            health_data["checks"]["github_api"] = {
                "status": "error",
                "message": f"GitHub API error: {str(e)}"
            }
            health_data["status"] = "degraded"
    else:
        health_data["checks"]["github_api"] = {
            "status": "warning",
            "message": "GitHub API token not configured"
        }

    # 检查磁盘空间
    try:
        import shutil
        disk_usage = shutil.disk_usage("/")
        free_gb = disk_usage.free / (1024**3)
        total_gb = disk_usage.total / (1024**3)
        used_gb = (disk_usage.total - disk_usage.free) / (1024**3)
        usage_percent = (used_gb / total_gb) * 100

        if free_gb < 1.0:  # 少于 1GB
            status = "error"
            message = f"磁盘空间严重不足: {free_gb:.2f}GB 可用"
            health_data["status"] = "degraded"
        elif usage_percent > 90:  # 使用超过90%
            status = "warning"
            message = f"磁盘空间不足: {usage_percent:.1f}% 已使用"
            if health_data["status"] == "healthy":
                health_data["status"] = "degraded"
        else:
            status = "ok"
            message = f"磁盘空间充足: {free_gb:.2f}GB 可用"

        health_data["checks"]["disk_space"] = {
            "status": status,
            "message": message,
            "details": {
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "usage_percent": round(usage_percent, 1)
            }
        }
    except Exception as e:
        health_data["checks"]["disk_space"] = {
            "status": "error",
            "message": f"无法检查磁盘空间: {str(e)}"
        }

    # 检查死信队列状态
    try:
        with SessionLocal() as db:
            deadletter_count_val = deadletter_count(db)
            health_data["checks"]["deadletter_queue"] = {
                "status": "warning" if deadletter_count_val > 10 else "ok",
                "message": f"死信队列: {deadletter_count_val} 条记录",
                "count": deadletter_count_val
            }
            if deadletter_count_val > 50:
                health_data["checks"]["deadletter_queue"]["status"] = "error"
                health_data["status"] = "degraded"
    except Exception as e:
        health_data["checks"]["deadletter_queue"] = {
            "status": "error",
            "message": f"无法检查死信队列: {str(e)}"
        }

    return health_data

# Initialize metrics system
initialize_metrics()

# metrics via separate ASGI with custom registry
app.mount("/metrics", make_asgi_app(registry=METRICS_REGISTRY))

# webhook


@app.post("/gitee_webhook",
          summary="Gitee Webhook 处理",
          description="处理来自 Gitee 的 webhook 事件，支持 issue 创建、更新、关闭等操作，自动同步到 Notion",
          response_description="处理结果，包含成功状态和详细信息")
async def gitee_webhook(request: Request):
    # 记录请求开始时间用于性能指标
    start_time = time.time()

    # optional simple rate limit
    if not rate_limiter.allow():
        RATE_LIMIT_HITS_TOTAL.inc()
        raise HTTPException(status_code=429, detail="too_many_requests")

    # 获取安全验证所需的头部信息
    signature = request.headers.get("X-Gitee-Token", "")
    event_type = request.headers.get("X-Gitee-Event", "")
    request_id = request.headers.get("X-Gitee-Delivery")
    timestamp = request.headers.get("X-Gitee-Timestamp")
    secret = os.getenv("GITEE_WEBHOOK_SECRET", "")

    # 获取请求体并进行安全验证
    body = await request.body()

    # Webhook安全验证（签名+重放保护）
    is_valid, error_msg = validate_webhook_security(
        body, signature, secret, "gitee", request_id, timestamp
    )
    if not is_valid:
        logger.warning("gitee_webhook_security_failed", extra={"error": error_msg, "request_id": request_id})
        # 记录安全失败的指标
        duration = time.time() - start_time
        record_webhook_request("gitee", event_type, "failed", duration)
        if "replay_attack_detected" in error_msg:
            record_security_event("replay_attack", "gitee", "detected")
            record_idempotency_check("gitee", "duplicate")
        elif "invalid_signature" in error_msg:
            record_security_event("invalid_signature", "gitee", "failed")
        raise HTTPException(status_code=403, detail=error_msg)

    # Validate request body with Pydantic; keep body for downstream processing
    issue_id = ""
    try:
        payload_obj = GiteeWebhookPayload.model_validate_json(body.decode("utf-8"))
        issue = payload_obj.issue
        issue_id = str(issue.number or issue.id or "")
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_payload")
    except Exception:
        # body decode or other errors
        raise HTTPException(status_code=400, detail="invalid_payload")

    # Run blocking processing in a thread to avoid blocking the event loop
    ok, message = await asyncio.to_thread(
        process_gitee_event, body, secret, signature, event_type
    )
    if not ok:
        status_code = 403 if message == "invalid_signature" else 400
        logger.warning(
            "process_failed",
            extra={
                "request_id": getattr(request.state, "request_id", ""),
                "op": "gitee_webhook",
                "issue_id": issue_id,
                "status": status_code,
            },
        )
        # 记录处理失败的指标
        duration = time.time() - start_time
        record_webhook_request("gitee", event_type, "error", duration)
        raise HTTPException(status_code=status_code, detail=message)
    logger.info(
        "process_success",
        extra={
            "request_id": getattr(request.state, "request_id", ""),
            "op": "gitee_webhook",
            "issue_id": issue_id,
            "status": 200,
        },
    )
    # 记录成功处理的指标
    duration = time.time() - start_time
    record_webhook_request("gitee", event_type, "success", duration)
    return {"message": message}


# 新增：GitHub Webhook 处理
@app.post("/github_webhook",
          summary="GitHub Webhook 处理",
          description="处理来自 GitHub 的 issues 事件并同步到 Notion",
          response_description="处理结果")
async def github_webhook(request: Request):
    if not rate_limiter.allow():
        RATE_LIMIT_HITS_TOTAL.inc()
        raise HTTPException(status_code=429, detail="too_many_requests")

    # 获取安全验证所需的头部信息
    signature = request.headers.get("X-Hub-Signature-256", "")
    event = request.headers.get("X-GitHub-Event", "")
    request_id = request.headers.get("X-GitHub-Delivery")
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    body = await request.body()

    # Webhook安全验证（签名+重放保护）
    is_valid, error_msg = validate_webhook_security(
        body, signature, secret, "github", request_id
    )
    if not is_valid:
        logger.warning("github_webhook_security_failed", extra={"error": error_msg, "request_id": request_id})
        raise HTTPException(status_code=403, detail=error_msg)

    # Pydantic 校验（尽量宽松，仅用于基础字段）
    try:
        payload_dict = json.loads(body.decode("utf-8"))
        _ = GitHubWebhookPayload.model_validate(payload_dict)
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_payload")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid_json")

    # 幂等性检查和事件处理
    with IdempotencyManager() as idempotency:
        # 生成事件ID
        event_id = idempotency.generate_event_id(
            provider="github",
            event_type=event,
            delivery_id=request_id,
            entity_id=str(payload_dict.get("issue", {}).get("number", ""))
        )
        content_hash = idempotency.generate_content_hash(payload_dict)

        # 检查重复
        is_duplicate, reason = idempotency.is_duplicate_event(event_id, content_hash)
        if is_duplicate:
            logger.info("github_duplicate_event_skipped", extra={
                "event_id": event_id,
                "reason": reason,
                "request_id": request_id
            })
            return {"message": f"duplicate_event_skipped:{reason}"}

        # 记录事件开始处理
        entity_id = str(payload_dict.get("issue", {}).get("number", "unknown"))
        action = payload_dict.get("action", "unknown")

        idempotency.record_event_processing(
            event_id, content_hash, "github", event, entity_id, action, payload_dict
        )

        try:
            # 处理事件
            ok, message = await async_process_github_event(body, event)

            # 标记处理结果
            idempotency.mark_event_processed(event_id, ok, message if not ok else None)

            if not ok:
                logger.warning("github_webhook_failed", extra={"event": event, "msg": message})
                raise HTTPException(status_code=400, detail=message)

            return {"message": message}

        except Exception as e:
            idempotency.mark_event_processed(event_id, False, str(e))
            raise


# 新增：Notion Webhook 处理
@app.post("/notion_webhook",
          summary="Notion Webhook 处理",
          description="处理来自 Notion 的页面变更并同步到 GitHub",
          response_description="处理结果")
async def notion_webhook(request: Request):
    if not rate_limiter.allow():
        RATE_LIMIT_HITS_TOTAL.inc()
        raise HTTPException(status_code=429, detail="too_many_requests")

    # 获取安全验证所需的头部信息
    signature = request.headers.get("Notion-Signature", "")
    request_id = request.headers.get("Notion-Request-Id")
    timestamp = request.headers.get("Notion-Timestamp")
    secret = os.getenv("NOTION_WEBHOOK_SECRET", "")

    body = await request.body()

    # Webhook安全验证（签名+重放保护）
    if secret:  # 仅在配置了密钥时进行验证
        is_valid, error_msg = validate_webhook_security(
            body, signature, secret, "notion", request_id, timestamp
        )
        if not is_valid:
            logger.warning("notion_webhook_security_failed", extra={"error": error_msg, "request_id": request_id})
            raise HTTPException(status_code=403, detail=error_msg)
    try:
        NotionWebhookPayload.model_validate_json(body.decode("utf-8"))
    except ValidationError:
        # 兼容 Notion 的 challenge 验证
        try:
            data = json.loads(body.decode("utf-8"))
            if "challenge" in data:
                return {"challenge": data["challenge"]}
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="invalid_payload")

    ok, message = await asyncio.to_thread(process_notion_event, body)
    if not ok:
        logger.warning("notion_webhook_failed", extra={"msg": message})
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

# admin: replay deadletters


@app.post("/replay-deadletters",
          summary="重放死信队列",
          description="手动触发死信队列重放，需要管理员令牌授权",
          response_description="重放结果，包含处理的死信数量")
async def replay_deadletters(request: Request):
    auth = request.headers.get("Authorization", "")
    token = os.getenv("DEADLETTER_REPLAY_TOKEN", "")
    if not token:
        raise HTTPException(status_code=403, detail="disabled")
    if not auth.startswith("Bearer ") or auth.split(" ", 1)[1] != token:
        raise HTTPException(status_code=401, detail="unauthorized")
    count = replay_deadletters_once(token)
    return {"replayed": count}
