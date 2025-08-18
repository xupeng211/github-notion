"""测试环境配置和Webhook处理"""

import hashlib
import hmac
import json
import os

from fastapi.testclient import TestClient

# 设置测试环境变量，必须在导入app之前
os.environ.setdefault("DB_URL", "sqlite:///data/test.db")
os.environ["DEADLETTER_REPLAY_TOKEN"] = "test-deadletter-replay-token-123456789"

# Import app modules after environment setup
from app.models import init_db  # noqa
from app.server import app  # noqa

client = TestClient(app)
init_db()


def sign(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    response_data = r.json()
    # 健康状态可能是 healthy 或 degraded（如果没有配置 Notion token）
    assert response_data.get("status") in ["healthy", "degraded"]
    # 确保包含必要的检查信息
    assert "checks" in response_data
    assert "database" in response_data["checks"]


def test_github_signature_validation():
    """测试GitHub webhook签名验证"""
    import hashlib
    import hmac

    secret = "test-secret"
    payload = json.dumps(
        {
            "action": "opened",
            "issue": {
                "id": 1,
                "number": 1,
                "title": "test-github-webhook",
                "body": "test",
                "state": "open",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "user": {"login": "test-user", "name": "Test User"},
                "labels": [],
                "html_url": "https://github.com/test-user/test-repo/issues/1",
            },
            "repository": {
                "id": 12345,
                "name": "test-repo",
                "full_name": "test-user/test-repo",
                "html_url": "https://github.com/test-user/test-repo",
            },
            "sender": {"login": "test-user", "name": "Test User"},
        }
    ).encode()

    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    # Test without proper environment setup - should fail
    r = client.post(
        "/github_webhook",
        data=payload,
        headers={"X-Hub-Signature-256": f"sha256={sig}", "Content-Type": "application/json"},
    )
    # service expects env GITHUB_WEBHOOK_SECRET; here it's empty, so invalid
    assert r.status_code == 403

    # test_duplicate_idempotency removed - Gitee functionality no longer supported
    # GitHub idempotency is tested in test_github_webhook.py

    # test_retry_deadletter and test_conflict_strategy removed - Gitee functionality no longer supported
    # Dead letter queue functionality is tested in test_error_handling.py

    payload1 = json.dumps({"issue": {"number": 4, "title": "Z"}}).encode()
    sig1 = sign("test-webhook-secret-for-testing-12345678", payload1)
    r1 = client.post(
        "/gitee_webhook",
        data=payload1,
        headers={"X-Gitee-Token": sig1, "Content-Type": "application/json"},
    )
    assert r1.status_code == 200

    payload2 = json.dumps({"issue": {"number": 4, "title": "Z2"}}).encode()
    sig2 = sign("test-webhook-secret-for-testing-12345678", payload2)
    r2 = client.post(
        "/gitee_webhook",
        data=payload2,
        headers={"X-Gitee-Token": sig2, "Content-Type": "application/json"},
    )
    assert r2.status_code == 200


def test_replay_script_imports():
    # Ensure replay script imports without error
    import importlib

    importlib.import_module("scripts.replay_deadletter")
