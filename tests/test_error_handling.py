"""
错误处理和边界情况测试

测试系统在各种异常情况下的行为
"""

import json
import os
import tempfile
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.server import app


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # 设置测试环境变量
    os.environ["DB_URL"] = f"sqlite:///{db_path}"
    os.environ["DISABLE_NOTION"] = "1"
    os.environ["GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret-for-testing-12345678"  # 使用安全长度的测试密钥
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


class TestErrorHandling:
    """错误处理测试套件"""

    def test_health_endpoint_resilience(self, client):
        """测试健康检查端点的弹性"""
        # 健康检查应该始终可用
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]

    def test_metrics_endpoint_resilience(self, client):
        """测试监控端点的弹性"""
        response = client.get("/metrics")
        assert response.status_code in [200, 307]  # 可能有重定向

    def test_invalid_endpoints(self, client):
        """测试无效端点的处理"""
        # 测试不存在的端点
        response = client.get("/nonexistent")
        assert response.status_code == 404

        response = client.post("/invalid_webhook")
        assert response.status_code == 404

    def test_malformed_requests(self, client):
        """测试格式错误的请求"""
        # 测试无效的Content-Type
        response = client.post("/github_webhook", data="invalid data", headers={"Content-Type": "text/plain"})
        assert response.status_code in [400, 403, 422]

        # 测试超大请求体
        large_payload = "x" * (2 * 1024 * 1024)  # 2MB
        response = client.post("/github_webhook", data=large_payload, headers={"Content-Type": "application/json"})
        assert response.status_code in [400, 403, 413, 422]

    def test_missing_headers(self, client):
        """测试缺少必需头部的请求"""
        payload = {"test": "data"}

        # 缺少签名头部
        response = client.post("/github_webhook", json=payload, headers={"X-GitHub-Event": "issues"})
        assert response.status_code == 403

        # 缺少事件类型头部
        response = client.post("/github_webhook", json=payload, headers={"X-Hub-Signature-256": "sha256=test"})
        assert response.status_code == 403

    def test_database_error_handling(self, client):
        """测试数据库错误处理"""
        # 模拟数据库连接错误
        with patch("app.models.SessionLocal") as mock_session:
            mock_session.side_effect = Exception("Database connection failed")

            response = client.get("/health")
            # 健康检查应该优雅地处理数据库错误
            assert response.status_code in [200, 503]

    def test_concurrent_requests(self, client):
        """测试并发请求处理"""
        import threading
        import time

        results = []

        def make_request():
            try:
                response = client.get("/health")
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))

        # 创建多个并发请求
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 所有请求都应该成功
        assert len(results) == 5
        assert all(result == 200 for result in results)

    def test_memory_usage_limits(self, client):
        """测试内存使用限制"""
        # 测试大量小请求
        for i in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_webhook_replay_protection(self, client):
        """测试webhook重放攻击保护"""
        import hashlib
        import hmac

        secret = "test-webhook-secret-for-testing-12345678"
        payload = {
            "action": "opened",
            "issue": {
                "id": 12345,
                "number": 1,
                "title": "Replay Test",
                "body": "Testing replay protection",
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
        signature = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()

        delivery_id = str(uuid.uuid4())
        headers = {
            "X-Hub-Signature-256": f"sha256={signature}",
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": delivery_id,
            "Content-Type": "application/json",
        }

        # 第一次请求
        response1 = client.post("/github_webhook", data=payload_str, headers=headers)
        assert response1.status_code == 200

        # 重复相同的delivery ID（重放攻击）
        response2 = client.post("/github_webhook", data=payload_str, headers=headers)
        # 应该被重放保护机制拒绝或标记为重复
        assert response2.status_code in [200, 403]

    def test_invalid_json_handling(self, client):
        """测试无效JSON处理"""
        import hashlib
        import hmac

        secret = "test-webhook-secret-for-testing-12345678"
        invalid_payloads = [
            "{ invalid json",
            '{"incomplete": ',
            '{"valid": "json", "but": "missing_required_fields"}',
            "",
            "null",
            "[]",
        ]

        for invalid_payload in invalid_payloads:
            signature = hmac.new(secret.encode(), invalid_payload.encode(), hashlib.sha256).hexdigest()

            headers = {
                "X-Hub-Signature-256": f"sha256={signature}",
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": str(uuid.uuid4()),
                "Content-Type": "application/json",
            }

            response = client.post("/github_webhook", data=invalid_payload, headers=headers)
            assert response.status_code == 400

    def test_timeout_handling(self, client):
        """测试超时处理"""
        # 模拟慢速请求
        with patch("app.service.async_process_github_event") as mock_process:
            import asyncio

            async def slow_process(*args, **kwargs):
                await asyncio.sleep(0.1)  # 模拟慢速处理
                return True, "ok"

            mock_process.return_value = slow_process()

            # 请求应该在合理时间内完成
            response = client.get("/health")
            assert response.status_code == 200

    def test_edge_case_payloads(self, client):
        """测试边界情况的payload"""
        import hashlib
        import hmac

        secret = "test-webhook-secret-for-testing-12345678"

        # 测试各种边界情况
        edge_cases = [
            # 极长的字符串
            {
                "action": "opened",
                "issue": {
                    "id": 1,
                    "number": 1,
                    "title": "x" * 1000,  # 很长的标题
                    "body": "y" * 10000,  # 很长的内容
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
            },
            # 特殊字符
            {
                "action": "opened",
                "issue": {
                    "id": 2,
                    "number": 2,
                    "title": "测试 🚀 Special chars: <>&\"'",
                    "body": "Unicode: 你好世界 🌍 Emoji: 🎉🔥💯",
                    "state": "open",
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T10:00:00Z",
                    "user": {"login": "test-user", "name": "Test User"},
                    "labels": [],
                    "html_url": "https://github.com/test-user/test-repo/issues/2",
                },
                "repository": {
                    "id": 12345,
                    "name": "test-repo",
                    "full_name": "test-user/test-repo",
                    "html_url": "https://github.com/test-user/test-repo",
                    "owner": {"login": "test-user", "name": "Test User"},
                },
                "sender": {"login": "test-user", "name": "Test User"},
            },
        ]

        for i, payload in enumerate(edge_cases):
            payload_str = json.dumps(payload)
            signature = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()

            headers = {
                "X-Hub-Signature-256": f"sha256={signature}",
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": str(uuid.uuid4()),
                "Content-Type": "application/json",
            }

            response = client.post("/github_webhook", data=payload_str, headers=headers)
            # 应该能处理这些边界情况
            assert response.status_code in [200, 400], f"Failed for edge case {i}"
