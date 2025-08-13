from __future__ import annotations
import os
import time
import logging
import uuid
from fastapi import FastAPI, Request, Response, HTTPException
import asyncio
from prometheus_client import make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware
from pythonjsonlogger import jsonlogger
from contextlib import asynccontextmanager
from collections import deque
from pydantic import ValidationError

from app.models import init_db
from app.service import process_gitee_event, start_deadletter_scheduler, replay_deadletters_once
from app.schemas import GiteeWebhookPayload

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

app = FastAPI(lifespan=lifespan)

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

# health
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": os.getenv("ENVIRONMENT", os.getenv("PY_ENV", "development")),
        "notion_api": {
            "connected": bool(os.getenv("NOTION_TOKEN", "")),
            "version": "2022-06-28",
        },
        "app_info": {
            "app": "fastapi",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        },
    }

# metrics via separate ASGI
app.mount("/metrics", make_asgi_app())

# webhook
@app.post("/gitee_webhook")
async def gitee_webhook(request: Request):
    # optional simple rate limit
    if not rate_limiter.allow():
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
@app.post("/replay-deadletters")
async def replay_deadletters(request: Request):
    auth = request.headers.get("Authorization", "")
    token = os.getenv("DEADLETTER_REPLAY_TOKEN", "")
    if not token:
        raise HTTPException(status_code=403, detail="disabled")
    if not auth.startswith("Bearer ") or auth.split(" ",1)[1] != token:
        raise HTTPException(status_code=401, detail="unauthorized")
    count = replay_deadletters_once(token)
    return {"replayed": count}

