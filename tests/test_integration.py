import os
import pytest
#!/usr/bin/env python3

import json


pytestmark = pytest.mark.skipif(os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="Set RUN_INTEGRATION_TESTS=1 to enable integration tests")
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Dict

import requests

# 测试配置
TEST_CONFIG = {
    "base_url": os.getenv("TEST_BASE_URL", "http://localhost:8787"),
    "gitee_webhook_secret": os.getenv("TEST_GITEE_WEBHOOK_SECRET", "test-secret"),
    "notion_api_token": os.getenv("TEST_NOTION_API_TOKEN"),
    "notion_database_id": os.getenv("TEST_NOTION_DATABASE_ID")
}

class TestGiteeNotionSync:
    @pytest.fixture
    def headers(self) -> Dict[str, str]:
        """生成基本请求头"""
        return {
            "Content-Type": "application/json"
        }

    @pytest.fixture
    def gitee_issue_payload(self) -> Dict[str, Any]:
        """生成测试用的 Gitee Issue payload"""
        return {
            "action": "open",
            "issue": {
                "number": f"test_{int(datetime.now().timestamp())}",
                "title": f"Test Issue {datetime.now(timezone.utc).isoformat()}",
                "body": "This is a test issue for integration testing.",
                "state": "open",
                "labels": [
                    {"name": "test"},
                    {"name": "integration"}
                ],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "user": {
                    "name": "test_user"
                }
            }
        }

    def calculate_gitee_signature(self, payload: str) -> str:
        """计算 Gitee webhook 签名"""
        return hmac.new(
            TEST_CONFIG["gitee_webhook_secret"].encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def test_health_check(self):
        """测试健康检查端点"""
        response = requests.get(f"{TEST_CONFIG['base_url']}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "notion_api" in data
        assert "app_info" in data
        assert "app" in data["app_info"]

    def test_metrics_endpoint(self):
        """测试指标收集端点"""
        response = requests.get(f"{TEST_CONFIG['base_url']}/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text
        assert "http_request_duration_seconds" in response.text

    def test_gitee_webhook_without_signature(self, headers, gitee_issue_payload):
        """测试没有签名的 Gitee webhook 请求"""
        response = requests.post(
            f"{TEST_CONFIG['base_url']}/gitee_webhook",
            headers=headers,
            json=gitee_issue_payload
        )
        assert response.status_code == 403

    def test_gitee_webhook_with_invalid_signature(self, headers, gitee_issue_payload):
        """测试无效签名的 Gitee webhook 请求"""
        headers["X-Gitee-Token"] = "invalid-signature"
        response = requests.post(
            f"{TEST_CONFIG['base_url']}/gitee_webhook",
            headers=headers,
            json=gitee_issue_payload
        )
        assert response.status_code == 403

    def test_gitee_webhook_with_valid_signature(self, headers, gitee_issue_payload):
        """测试有效签名的 Gitee webhook 请求"""
        payload_str = json.dumps(gitee_issue_payload)
        headers["X-Gitee-Token"] = self.calculate_gitee_signature(payload_str)
        headers["X-Gitee-Event"] = "Issue Hook"

        response = requests.post(
            f"{TEST_CONFIG['base_url']}/gitee_webhook",
            headers=headers,
            data=payload_str
        )
        assert response.status_code == 200

        # 验证 Notion 数据库中是否创建了对应的页面
        if TEST_CONFIG["notion_api_token"] and TEST_CONFIG["notion_database_id"]:
            notion_headers = {
                "Authorization": f"Bearer {TEST_CONFIG['notion_api_token']}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }

            response = requests.post(
                "https://api.notion.com/v1/databases/{TEST_CONFIG['notion_database_id']}/query",
                headers=notion_headers,
                json={
                    "filter": {
                        "property": "Title",
                        "title": {
                            "equals": gitee_issue_payload["issue"]["title"]
                        }
                    }
                }
            )
            assert response.status_code == 200
            results = response.json()["results"]
            assert len(results) == 1

    def test_rate_limiting(self, headers, gitee_issue_payload):
        """测试速率限制"""
        payload_str = json.dumps(gitee_issue_payload)
        headers["X-Gitee-Token"] = self.calculate_gitee_signature(payload_str)
        headers["X-Gitee-Event"] = "Issue Hook"

        # 发送多个请求触发速率限制
        for _ in range(10):
            response = requests.post(
                f"{TEST_CONFIG['base_url']}/gitee_webhook",
                headers=headers,
                data=payload_str
            )
            if response.status_code == 429:
                break
        assert response.status_code == 429

    def test_error_handling(self, headers):
        """测试错误处理"""
        # 测试无效的 JSON
        response = requests.post(
            f"{TEST_CONFIG['base_url']}/gitee_webhook",
            headers=headers,
            data="invalid json"
        )
        assert response.status_code == 400

        # 测试缺少必要字段
        response = requests.post(
            f"{TEST_CONFIG['base_url']}/gitee_webhook",
            headers=headers,
            json={"action": "open"}  # 缺少 issue 字段
        )
        assert response.status_code == 400

    def test_concurrent_requests(self, headers, gitee_issue_payload):
        """测试并发请求处理"""
        import concurrent.futures

        payload_str = json.dumps(gitee_issue_payload)
        headers["X-Gitee-Token"] = self.calculate_gitee_signature(payload_str)
        headers["X-Gitee-Event"] = "Issue Hook"

        def send_request():
            return requests.post(
                f"{TEST_CONFIG['base_url']}/gitee_webhook",
                headers=headers,
                data=payload_str
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_request) for _ in range(5)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 验证所有请求都被正确处理
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count > 0

    @pytest.mark.skip(reason="需要在生产环境中运行")
    def test_end_to_end_sync(self, headers, gitee_issue_payload):
        """完整的端到端同步测试"""
        # 1. 创建 Gitee Issue
        payload_str = json.dumps(gitee_issue_payload)
        headers["X-Gitee-Token"] = self.calculate_gitee_signature(payload_str)
        headers["X-Gitee-Event"] = "Issue Hook"

        response = requests.post(
            f"{TEST_CONFIG['base_url']}/gitee_webhook",
            headers=headers,
            data=payload_str
        )
        assert response.status_code == 200

        # 2. 验证 Notion 页面创建
        if TEST_CONFIG["notion_api_token"] and TEST_CONFIG["notion_database_id"]:
            notion_headers = {
                "Authorization": f"Bearer {TEST_CONFIG['notion_api_token']}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }

            # 等待同步完成
            import time
            time.sleep(5)

            response = requests.post(
                "https://api.notion.com/v1/databases/{TEST_CONFIG['notion_database_id']}/query",
                headers=notion_headers,
                json={
                    "filter": {
                        "property": "Title",
                        "title": {
                            "equals": gitee_issue_payload["issue"]["title"]
                        }
                    }
                }
            )
            assert response.status_code == 200
            results = response.json()["results"]
            assert len(results) == 1

            # 3. 更新 Notion 页面
            page_id = results[0]["id"]
            response = requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=notion_headers,
                json={
                    "properties": {
                        "Status": {
                            "select": {
                                "name": "In Progress"
                            }
                        }
                    }
                }
            )
            assert response.status_code == 200

            # 4. 验证 Gitee Issue 更新
            # 等待同步完成
            time.sleep(5)

            # TODO: 实现 Gitee API 调用验证 Issue 状态更新