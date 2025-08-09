import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request, HTTPException
from app.gitee import verify_signature  # Placeholder for actual implementation
from app.config import Settings
from app.db import Database
from app.notion import NotionClient
from prometheus_client import Counter, Histogram, make_wsgi_app
from starlette.responses import StreamingResponse

# 配置日志
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    "logs/app.log",
    maxBytes=5*1024*1024,
    backupCount=7
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Initialize FastAPI app
app = FastAPI()

# Load settings
settings = Settings()  # Assuming pydantic model for configuration

db = Database(settings.sqlite_path)
notion_client = NotionClient(settings.notion_token)

# Define Prometheus metrics
WEBHOOK_REQUESTS = Counter(
    'webhook_requests_total',
    'Total webhook requests',
    ['status']
)

NOTION_API_LATENCY = Histogram(
    'notion_api_latency_seconds',
    'Notion API latency',
    buckets=[0.1, 0.5, 1, 2, 5]
)

# Prometheus /metrics endpoint using WSGI app, wrapped for ASGI
@app.get("/metrics")
async def metrics():
    wsgi_app = make_wsgi_app()
    def start_response(status, headers):
        return None
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/metrics",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "wsgi.input": b"",
    }
    data_iter = wsgi_app(environ, start_response)
    return StreamingResponse(data_iter, media_type="text/plain")

@app.post("/gitee_webhook")
async def gitee_webhook(request: Request):
    try:
        x_gitee_token = request.headers.get("X-Gitee-Token")
        body_bytes = await request.body()

        if not verify_signature(x_gitee_token, body_bytes, settings.gitee_webhook_secret):
            logger.warning("Invalid signature for Gitee webhook event.")
            WEBHOOK_REQUESTS.labels("fail").inc()
            raise HTTPException(status_code=403, detail="Invalid signature")

        payload = await request.json()
        event = request.headers.get("X-Gitee-Event")
        logger.info(f"Gitee event received: {event}")

        # with NOTION_API_LATENCY.time():
        #     notion_client.sync_to_notion(payload)

        WEBHOOK_REQUESTS.labels("success").inc()
        return {"message": "Webhook received"}

    except Exception as e:
        logger.exception("process failed")
        WEBHOOK_REQUESTS.labels("fail").inc()
        raise HTTPException(500, "internal error")
