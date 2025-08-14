"""
HTTP 监控中间件
"""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.service import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Prometheus 指标收集中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.time()

        # 获取请求信息
        method = request.method
        path = request.url.path

        # 简化路径（移除动态参数）
        endpoint = self._normalize_path(path)

        try:
            # 处理请求
            response = await call_next(request)
            status = str(response.status_code)

        except Exception:
            # 处理异常
            status = "5xx"
            # 重新抛出异常
            raise

        finally:
            # 计算处理时间
            duration = time.time() - start_time

            # 记录指标
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status).inc()
            HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        return response

    def _normalize_path(self, path: str) -> str:
        """标准化路径，移除动态参数"""
        # 简单的路径标准化
        if path.startswith("/health"):
            return "/health"
        elif path.startswith("/metrics"):
            return "/metrics"
        elif path.startswith("/gitee_webhook"):
            return "/gitee_webhook"
        elif path.startswith("/github_webhook"):
            return "/github_webhook"
        elif path.startswith("/notion_webhook"):
            return "/notion_webhook"
        elif path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi.json"):
            return "/docs"
        else:
            return path
