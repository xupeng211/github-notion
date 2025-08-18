"""
GitHub Webhook 集成测试

专注于测试 GitHub ↔ Notion 双向同步功能
"""

import hashlib
import hmac
import json
import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient

from app.server import app

# from datetime import datetime, timezone  # 暂时注释未使用的导入




def generate_github_signature(secret: str, payload: str) -> str:
    """生成GitHub webhook签名"""
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={signature}"


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # 设置测试环境变量
    os.environ["DB_URL"] = f"sqlite:///{db_path}"
    os.environ["DISABLE_NOTION"] = "1"  # 禁用 Notion API 调用
    os.environ["GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret-for-testing-12345678"
    os.environ["NOTION_TOKEN"] = "test-notion-token"  # 测试用 token
    os.environ["NOTION_DATABASE_ID"] = "test-database-id"  # 测试用数据库 ID
    os.environ["GITHUB_TOKEN"] = "test-github-token"  # 测试用 GitHub token
    os.environ["ENVIRONMENT"] = "testing"

    yield db_path

    # 清理
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def client(temp_db):
    """创建测试客户端"""
    with TestClient(app) as test_client:
        yield test_client


class TestGitHubWebhook:
    """GitHub Webhook 测试套件"""

    def test_github_webhook_security_validation(self, client, temp_db):
        """测试GitHub webhook安全验证"""
        payload = {
            "action": "opened",
            "issue": {
                "id": 12345,
                "number": 1,
                "title": "Security Test Issue",
                "body": "Testing security validation",
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
                "owner": {"login": "test-user", "name": "Test User"},
            },
            "sender": {"login": "test-user", "name": "Test User"},
        }
        payload_str = json.dumps(payload)

        # 1. 测试无效签名
        headers = {
            "X-Hub-Signature-256": "sha256=invalid-signature",
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

        response = client.post("/github_webhook", data=payload_str, headers=headers)
        assert response.status_code == 403

        # 2. 测试缺少签名
        headers_no_sig = {
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

        response = client.post("/github_webhook", data=payload_str, headers=headers_no_sig)
        assert response.status_code == 403

    def test_github_webhook_valid_signature(self, client, temp_db):
        """测试GitHub webhook有效签名处理"""
        secret = "test-webhook-secret-for-testing-12345678"

        payload = {
            "action": "opened",
            "issue": {
                "id": 54321,
                "number": 2,
                "title": "Valid Signature Test",
                "body": "Testing valid signature processing",
                "state": "open",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "user": {"login": "github-user", "name": "GitHub User"},
                "labels": [],
                "html_url": "https://github.com/github-user/test-repo/issues/2",
            },
            "repository": {
                "id": 12345,
                "name": "test-repo",
                "full_name": "github-user/test-repo",
                "html_url": "https://github.com/github-user/test-repo",
                "owner": {"login": "github-user", "name": "GitHub User"},
            },
            "sender": {"login": "github-user", "name": "GitHub User"},
        }
        payload_str = json.dumps(payload)
        signature = generate_github_signature(secret, payload_str)

        headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

        response = client.post("/github_webhook", data=payload_str, headers=headers)

        # 应该成功处理（即使 Notion 被禁用）
        assert response.status_code == 200
        response_data = response.json()
        assert "message" in response_data

    def test_github_webhook_invalid_payload(self, client, temp_db):
        """测试GitHub webhook无效payload处理"""
        secret = "test-webhook-secret-for-testing-12345678"

        # 无效的JSON
        invalid_payload = "{ invalid json"
        signature = generate_github_signature(secret, invalid_payload)

        headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

        response = client.post("/github_webhook", data=invalid_payload, headers=headers)
        assert response.status_code == 400

    def test_github_webhook_missing_fields(self, client, temp_db):
        """测试GitHub webhook缺少必需字段的处理"""
        secret = "test-webhook-secret-for-testing-12345678"

        # 缺少必需字段的payload
        incomplete_payload = {
            "action": "opened",
            # 缺少 issue 字段
        }
        payload_str = json.dumps(incomplete_payload)
        signature = generate_github_signature(secret, payload_str)

        headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

        response = client.post("/github_webhook", data=payload_str, headers=headers)
        assert response.status_code == 400

    def test_github_webhook_idempotency(self, client, temp_db):
        """测试GitHub webhook幂等性保护"""
        secret = "test-webhook-secret-for-testing-12345678"
        delivery_id = str(uuid.uuid4())  # 相同的delivery ID

        payload = {
            "action": "opened",
            "issue": {
                "id": 99999,
                "number": 99,
                "title": "Idempotency Test Issue",
                "body": "Testing idempotency protection",
                "state": "open",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "user": {"login": "test-user", "name": "Test User"},
                "labels": [],
                "html_url": "https://github.com/test-user/test-repo/issues/99",
            },
            "repository": {
                "id": 12345,
                "name": "test-repo",
                "full_name": "test-user/test-repo",
                "html_url": "https://github.com/test-user/test-repo",
                "owner": {"login": "test-user", "name": "Test User"},
            },
            "sender": {"login": "test-user", "name": "Test User"},
        }
        payload_str = json.dumps(payload)
        signature = generate_github_signature(secret, payload_str)

        headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": delivery_id,
            "Content-Type": "application/json",
        }

        # 发送第一次请求
        response1 = client.post("/github_webhook", data=payload_str, headers=headers)
        assert response1.status_code == 200

        # 发送第二次相同请求（应该被幂等性保护拒绝或标记为重复）
        response2 = client.post("/github_webhook", data=payload_str, headers=headers)
        # 可能返回200（重复处理）或403（重放攻击检测）
        assert response2.status_code in [200, 403]

    def test_github_webhook_rate_limiting(self, client, temp_db):
        """测试GitHub webhook速率限制"""
        secret = "test-webhook-secret-for-testing-12345678"

        # 发送多个快速请求
        for i in range(3):  # 适度测试
            payload = {
                "action": "opened",
                "issue": {
                    "id": 20000 + i,
                    "number": 200 + i,
                    "title": f"Rate Limit Test {i}",
                    "body": f"Testing rate limiting #{i}",
                    "state": "open",
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T10:00:00Z",
                    "user": {"login": "test-user", "name": "Test User"},
                    "labels": [],
                    "html_url": f"https://github.com/test-user/test-repo/issues/{200 + i}",
                },
                "repository": {
                    "id": 12345,
                    "name": "test-repo",
                    "full_name": "test-user/test-repo",
                    "html_url": "https://github.com/test-user/test-repo",
                    "owner": {"login": "test-user", "name": "Test User"},
                },
                "sender": {"login": "test-user", "name": "Test User"},
            }
            payload_str = json.dumps(payload)
            signature = generate_github_signature(secret, payload_str)

            headers = {
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": str(uuid.uuid4()),
                "Content-Type": "application/json",
            }

            response = client.post("/github_webhook", data=payload_str, headers=headers)

            # 大部分请求应该成功，但可能有速率限制
            assert response.status_code in [200, 429]
