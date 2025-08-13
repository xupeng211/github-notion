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
from pydantic import ValidationError
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from app.middleware import PrometheusMiddleware
from app.models import SessionLocal, init_db
from app.schemas import GiteeWebhookPayload
from app.service import RATE_LIMIT_HITS_TOTAL, process_gitee_event, replay_deadletters_once, start_deadletter_scheduler

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
    init_db()
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
    return Response(
        content=f"请求数据验证失败: {str(exc)}",
        status_code=422,
        headers={"content-type": "text/plain"}
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """处理值错误"""
    logger.error(f"Value error in {request.url.path}: {str(exc)}")
    return Response(
        content="请求参数错误",
        status_code=400,
        headers={"content-type": "text/plain"}
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    """处理内部服务器错误"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Internal server error: {str(exc)}", extra={"request_id": request_id})
    return Response(
        content=f"内部服务器错误。请求ID: {request_id}",
        status_code=500,
        headers={"content-type": "text/plain"}
    )

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
    if notion_token:
        try:
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            response = requests.get("https://api.notion.com/v1/users/me", headers=headers, timeout=5)
            if response.status_code == 200:
                health_data["checks"]["notion_api"] = {
                    "status": "ok",
                    "message": "Notion API connection successful",
                    "version": "2022-06-28"
                }
            else:
                health_data["checks"]["notion_api"] = {
                    "status": "error",
                    "message": f"Notion API error: {response.status_code}",
                    "version": "2022-06-28"
                }
                health_data["status"] = "degraded"
        except Exception as e:
            health_data["checks"]["notion_api"] = {
                "status": "error",
                "message": f"Notion API connection failed: {str(e)}",
                "version": "2022-06-28"
            }
            health_data["status"] = "degraded"
    else:
        health_data["checks"]["notion_api"] = {
            "status": "warning",
            "message": "Notion API token not configured",
            "version": "2022-06-28"
        }

    # 检查磁盘空间（简单检查）
    try:
        import shutil
        disk_usage = shutil.disk_usage("/")
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 1.0:  # 少于 1GB
            health_data["checks"]["disk_space"] = {
                "status": "warning",
                "message": f"Low disk space: {free_gb:.2f}GB free"
            }
            if health_data["status"] == "healthy":
                health_data["status"] = "degraded"
        else:
            health_data["checks"]["disk_space"] = {
                "status": "ok",
                "message": f"Disk space OK: {free_gb:.2f}GB free"
            }
    except Exception as e:
        health_data["checks"]["disk_space"] = {
            "status": "error",
            "message": f"Cannot check disk space: {str(e)}"
        }

    return health_data

# metrics via separate ASGI
app.mount("/metrics", make_asgi_app())

# webhook


@app.post("/gitee_webhook",
          summary="Gitee Webhook 处理",
          description="处理来自 Gitee 的 webhook 事件，支持 issue 创建、更新、关闭等操作，自动同步到 Notion",
          response_description="处理结果，包含成功状态和详细信息")
async def gitee_webhook(request: Request):
    # optional simple rate limit
    if not rate_limiter.allow():
        RATE_LIMIT_HITS_TOTAL.inc()
        raise HTTPException(status_code=429, detail="too_many_requests")

    secret = os.getenv("GITEE_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-Gitee-Token")
    event_type = request.headers.get("X-Gitee-Event", "")

    # Validate request body with Pydantic; keep body for downstream processing
    body = await request.body()
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
