"""
Webhook安全验证模块
提供签名验证、重放攻击保护等安全功能
"""

import hashlib
import hmac
import logging
import os
import time
from typing import Optional, Tuple

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# 重放攻击保护窗口（秒）
MAX_TIMESTAMP_SKEW = int(os.getenv("WEBHOOK_TIMESTAMP_SKEW", "300"))  # 5分钟

# 内存存储已处理的请求ID（生产环境应使用Redis）
_processed_requests = set()
_last_cleanup = time.time()
CLEANUP_INTERVAL = 600  # 10分钟清理一次


def cleanup_processed_requests():
    """清理过期的请求记录"""
    global _last_cleanup, _processed_requests
    now = time.time()
    if now - _last_cleanup > CLEANUP_INTERVAL:
        # 简单清理：保留最近的1000个请求
        if len(_processed_requests) > 1000:
            _processed_requests = set(list(_processed_requests)[-500:])
        _last_cleanup = now


class WebhookSecurityValidator:
    """Webhook安全验证器"""

    def __init__(self, secret: str, provider: str = "generic"):
        self.secret = secret
        self.provider = provider.lower()

    def verify_signature(self, body: bytes, signature: str, timestamp: Optional[str] = None) -> bool:
        """
        验证webhook签名

        Args:
            body: 请求体字节
            signature: 签名字符串
            timestamp: 时间戳（可选，用于重放保护）

        Returns:
            bool: 签名是否有效
        """
        if not self.secret or not signature:
            logger.warning(f"{self.provider}_webhook_no_secret_or_signature")
            return False

        try:
            if self.provider == "github":
                return self._verify_github_signature(body, signature)
            elif self.provider == "gitee":
                return self._verify_gitee_signature(body, signature, timestamp)
            elif self.provider == "notion":
                return self._verify_notion_signature(body, signature, timestamp)
            else:
                return self._verify_generic_signature(body, signature, timestamp)

        except Exception as e:
            logger.error(f"{self.provider}_signature_verification_error", extra={"error": str(e)})
            return False

    def _verify_github_signature(self, body: bytes, signature: str) -> bool:
        """GitHub签名验证（SHA256-HMAC）"""
        if not signature.startswith("sha256="):
            return False

        expected_sig = signature[7:]  # 移除 "sha256=" 前缀
        computed_sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()

        return hmac.compare_digest(expected_sig, computed_sig)

    def _verify_gitee_signature(self, body: bytes, signature: str, timestamp: Optional[str] = None) -> bool:
        """Gitee签名验证"""
        # Gitee使用标准的HMAC-SHA256验证
        computed_sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()

        return hmac.compare_digest(signature, computed_sig)

    def _verify_notion_signature(self, body: bytes, signature: str, timestamp: str) -> bool:
        """Notion签名验证"""
        if not timestamp:
            return False

        # Notion风格：timestamp.body的SHA256-HMAC
        payload_to_sign = f"{timestamp}.{body.decode('utf-8', errors='ignore')}"
        computed_sig = hmac.new(self.secret.encode(), payload_to_sign.encode(), hashlib.sha256).hexdigest()

        return hmac.compare_digest(signature, f"sha256={computed_sig}")

    def _verify_generic_signature(self, body: bytes, signature: str, timestamp: Optional[str] = None) -> bool:
        """通用签名验证"""
        if timestamp:
            payload = f"{timestamp}.{body.decode('utf-8', errors='ignore')}"
        else:
            payload = body.decode("utf-8", errors="ignore")

        computed_sig = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

        # 支持多种签名格式
        expected_signatures = [signature, f"sha256={computed_sig}", computed_sig]

        return any(hmac.compare_digest(sig, computed_sig) for sig in expected_signatures)

    def check_replay_protection(self, request_id: str, timestamp: Optional[str] = None) -> bool:
        """
        检查重放攻击保护

        Args:
            request_id: 唯一请求ID（如delivery_id）
            timestamp: 请求时间戳

        Returns:
            bool: 是否通过重放保护检查
        """
        cleanup_processed_requests()

        # 检查时间戳（如果提供）
        if timestamp:
            try:
                ts = int(timestamp)
                current_time = int(time.time())

                if abs(current_time - ts) > MAX_TIMESTAMP_SKEW:
                    logger.warning(
                        f"{self.provider}_timestamp_skew_too_large",
                        extra={"skew": abs(current_time - ts)},
                    )
                    return False
            except (ValueError, TypeError):
                logger.warning(f"{self.provider}_invalid_timestamp", extra={"timestamp": timestamp})
                return False

        # 检查请求ID去重
        if request_id in _processed_requests:
            logger.warning(f"{self.provider}_duplicate_request", extra={"request_id": request_id})
            return False

        _processed_requests.add(request_id)
        return True


def validate_webhook_security(
    body: bytes,
    signature: str,
    secret: str,
    provider: str,
    request_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    完整的webhook安全验证

    Args:
        body: 请求体字节
        signature: 签名
        secret: 密钥
        provider: 提供商（github/gitee/notion）
        request_id: 请求ID（用于重放保护）
        timestamp: 时间戳

    Returns:
        Tuple[bool, str]: (是否通过验证, 错误信息)
    """
    if not secret:
        return False, f"{provider}_webhook_secret_not_configured"

    validator = WebhookSecurityValidator(secret, provider)

    # 1. 签名验证
    if not validator.verify_signature(body, signature, timestamp):
        return False, f"{provider}_invalid_signature"

    # 2. 重放保护（如果提供了请求ID）
    if request_id and not validator.check_replay_protection(request_id, timestamp):
        return False, f"{provider}_replay_attack_detected"

    return True, "validation_passed"


def secure_webhook_decorator(provider: str):
    """
    Webhook安全验证装饰器

    使用示例:
    @secure_webhook_decorator("github")
    async def github_webhook(request: Request):
        # webhook处理逻辑
    """

    def decorator(func):
        async def wrapper(request, *args, **kwargs):
            body = await request.body()

            # 根据提供商获取相应的头部和密钥
            if provider == "github":
                signature = request.headers.get("X-Hub-Signature-256", "")
                secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
                request_id = request.headers.get("X-GitHub-Delivery")
                timestamp = None
            elif provider == "gitee":
                signature = request.headers.get("X-Gitee-Token", "")
                secret = os.getenv("GITEE_WEBHOOK_SECRET", "")
                request_id = request.headers.get("X-Gitee-Delivery")
                timestamp = request.headers.get("X-Gitee-Timestamp")
            elif provider == "notion":
                signature = request.headers.get("Notion-Signature", "")
                secret = os.getenv("NOTION_WEBHOOK_SECRET", "")
                request_id = request.headers.get("Notion-Request-Id")
                timestamp = request.headers.get("Notion-Timestamp")
            else:
                raise HTTPException(status_code=400, detail="unsupported_webhook_provider")

            # 安全验证
            is_valid, error_msg = validate_webhook_security(body, signature, secret, provider, request_id, timestamp)

            if not is_valid:
                logger.warning(
                    "webhook_security_failed",
                    extra={
                        "provider": provider,
                        "error": error_msg,
                        "request_id": request_id,
                    },
                )
                raise HTTPException(status_code=403, detail=error_msg)

            # 通过验证，继续处理
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
