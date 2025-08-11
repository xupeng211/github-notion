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

from app.models import init_db
from app.service import process_gitee_event, start_deadletter_scheduler, replay_deadletters_once

app = FastAPI()

# JSON structured logging
logger = logging.getLogger("app")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
logHandler.setFormatter(formatter)
# start background scheduler
start_deadletter_scheduler()

logger.addHandler(logHandler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

init_db()

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
    return {"status": "ok"}

# metrics via separate ASGI
app.mount("/metrics", make_asgi_app())

# webhook
@app.post("/gitee_webhook")
async def gitee_webhook(request: Request):
    secret = os.getenv("GITEE_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-Gitee-Token")
    event_type = request.headers.get("X-Gitee-Event", "")
    body = await request.body()
    issue_id = ""
    try:
        import json as _json
        issue = (_json.loads(body.decode("utf-8")) or {}).get("issue") or {}
        issue_id = str(issue.get("number") or issue.get("id") or "")
    except Exception:
        pass
    # Run blocking processing in a thread to avoid blocking the event loop
    ok, message = await asyncio.to_thread(
        process_gitee_event, body, secret, signature, event_type
    )
    if not ok:
        logger.warning(
            "process_failed",
            extra={
                "request_id": getattr(request.state, "request_id", ""),
                "op": "gitee_webhook",
                "issue_id": issue_id,
                "status": 400,
            },
        )
        raise HTTPException(status_code=400, detail=message)
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

