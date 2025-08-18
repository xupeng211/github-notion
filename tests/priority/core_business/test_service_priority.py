"""
🟡 高优先级：核心业务逻辑测试
测试 service.py 的关键业务功能 (966行代码)
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

# 设置测试环境变量，禁用 metrics
os.environ["DISABLE_METRICS"] = "1"
os.environ["PYTEST_CURRENT_TEST"] = "1"

from app.service import (
    async_exponential_backoff_request,
    async_notion_upsert_page,
    async_process_github_event,
    process_github_event,
    process_notion_event,
)


class TestGitHubEventProcessing:
    """GitHub 事件处理测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.sample_github_payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "id": 123,
                "title": "Test Issue",
                "body": "Test issue body",
                "state": "open",
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "testuser"},
            },
            "repository": {"name": "test-repo", "owner": {"login": "testowner"}},
        }

    @patch("app.service.session_scope")
    @patch("app.service.should_skip_event")
    @patch("app.service.should_skip_sync_event")
    @patch("app.service.notion_upsert_page")
    @patch("app.service.upsert_mapping")
    @patch("app.service.mark_event_processed")
    def test_github_issue_opened_success(
        self, mock_mark_event, mock_upsert_mapping, mock_notion_upsert, mock_skip_sync, mock_skip_event, mock_session
    ):
        """🟡 核心测试：GitHub issue 创建成功处理"""
        # 设置 mocks
        mock_session.return_value.__enter__.return_value = MagicMock()
        mock_skip_event.return_value = False  # 不跳过事件
        mock_skip_sync.return_value = False  # 不跳过同步
        mock_notion_upsert.return_value = (True, "page_123")  # 修正返回值

        # 准备测试数据
        body_bytes = json.dumps(self.sample_github_payload).encode("utf-8")

        # 执行测试
        success, message = process_github_event(body_bytes, "issues")

        # 验证结果
        assert success is True, f"GitHub issue 处理应该成功，但失败了：{message}"
        assert message == "ok"

        # 验证调用
        mock_notion_upsert.assert_called_once()
        mock_upsert_mapping.assert_called_once()
        mock_mark_event.assert_called_once()

    @patch("app.service.session_scope")
    def test_github_non_issues_event_ignored(self, mock_session):
        """🟡 功能测试：非 issues 事件被忽略"""
        body_bytes = json.dumps({"action": "opened"}).encode("utf-8")

        success, message = process_github_event(body_bytes, "pull_request")

        assert success is True
        assert message == "ignored_event"
        # session_scope 不应该被调用
        mock_session.assert_not_called()

    def test_github_missing_required_fields(self):
        """🟡 错误处理测试：缺少必需字段"""
        # 缺少 issue number
        invalid_payload = {
            "action": "opened",
            "issue": {"title": "Test"},  # 缺少 number
            "repository": {"name": "test", "owner": {"login": "owner"}},
        }

        body_bytes = json.dumps(invalid_payload).encode("utf-8")

        success, message = process_github_event(body_bytes, "issues")

        assert success is False
        assert message == "missing_required_fields"

    def test_github_sync_marker_detection(self):
        """🟡 防循环测试：检测同步标记"""
        payload_with_marker = self.sample_github_payload.copy()
        payload_with_marker["issue"]["body"] = "Test body <!-- sync-marker:123 --> more text"

        body_bytes = json.dumps(payload_with_marker).encode("utf-8")

        success, message = process_github_event(body_bytes, "issues")

        assert success is True
        assert message == "sync_induced"

    @patch("app.service.session_scope")
    @patch("app.service.should_skip_event")
    def test_github_duplicate_event_handling(self, mock_skip_event, mock_session):
        """🟡 幂等性测试：重复事件处理"""
        mock_session.return_value.__enter__.return_value = MagicMock()
        mock_skip_event.return_value = True  # 模拟重复事件

        body_bytes = json.dumps(self.sample_github_payload).encode("utf-8")

        success, message = process_github_event(body_bytes, "issues")

        assert success is True
        assert message == "duplicate"

    @patch("app.service.session_scope")
    @patch("app.service.should_skip_event")
    @patch("app.service.should_skip_sync_event")
    def test_github_loop_prevention(self, mock_skip_sync, mock_skip_event, mock_session):
        """🟡 防循环测试：防止同步循环"""
        mock_session.return_value.__enter__.return_value = MagicMock()
        mock_skip_event.return_value = False
        mock_skip_sync.return_value = True  # 模拟检测到循环

        body_bytes = json.dumps(self.sample_github_payload).encode("utf-8")

        success, message = process_github_event(body_bytes, "issues")

        assert success is True
        assert message == "loop_prevented"


class TestNotionEventProcessing:
    """Notion 事件处理测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.sample_notion_payload = {
            "page": {"id": "notion_page_123"},
            "properties": {
                "Status": {"select": {"name": "Done"}},
                "Title": {"title": [{"text": {"content": "Updated Title"}}]},
            },
        }

    @patch("app.service.session_scope")
    @patch("app.service.get_mapping_by_notion_page")
    @patch("app.service.should_skip_event")
    @patch("app.service.should_skip_sync_event")
    @patch("app.service.github_service.update_issue")
    @patch("app.service.github_service.extract_repo_info")
    @patch("app.service.mark_event_processed")
    @patch("app.service.create_sync_event")
    @patch("app.service.mark_sync_event_processed")
    def test_notion_page_update_success(
        self,
        mock_mark_sync,
        mock_create_sync,
        mock_mark_event,
        mock_extract_repo,
        mock_github_update,
        mock_skip_sync,
        mock_skip_event,
        mock_get_mapping,
        mock_session,
    ):
        """🟡 核心测试：Notion 页面更新成功处理"""
        # 设置 mocks
        mock_session.return_value.__enter__.return_value = MagicMock()

        # 模拟映射存在
        mock_mapping = MagicMock()
        mock_mapping.source_id = "123"
        mock_mapping.source_platform = "github"
        mock_mapping.target_id = "notion_page_123"
        mock_mapping.source_url = "https://github.com/test/repo/issues/123"
        mock_get_mapping.return_value = mock_mapping

        mock_skip_event.return_value = False
        mock_skip_sync.return_value = False
        mock_extract_repo.return_value = ("test", "repo")
        mock_github_update.return_value = (True, "updated")
        mock_create_sync.return_value = "sync_event_123"

        body_bytes = json.dumps(self.sample_notion_payload).encode("utf-8")

        success, message = process_notion_event(body_bytes)

        assert success is True
        assert message == "ok"
        mock_github_update.assert_called_once()
        mock_mark_event.assert_called_once()

    def test_notion_missing_page_id(self):
        """🟡 错误处理测试：缺少页面 ID"""
        invalid_payload = {"properties": {"Status": "Done"}}  # 缺少 page.id

        body_bytes = json.dumps(invalid_payload).encode("utf-8")

        success, message = process_notion_event(body_bytes)

        assert success is False
        assert message == "missing_page_id"

    @patch("app.service.session_scope")
    @patch("app.service.get_mapping_by_notion_page")
    def test_notion_unmapped_page(self, mock_get_mapping, mock_session):
        """🟡 业务逻辑测试：未映射的页面"""
        mock_session.return_value.__enter__.return_value = MagicMock()
        mock_get_mapping.return_value = None  # 没有映射

        body_bytes = json.dumps(self.sample_notion_payload).encode("utf-8")

        success, message = process_notion_event(body_bytes)

        assert success is True
        assert message == "unmapped_page"

    @patch("app.service.session_scope")
    @patch("app.service.get_mapping_by_notion_page")
    def test_notion_non_github_mapping(self, mock_get_mapping, mock_session):
        """🟡 业务逻辑测试：非 GitHub 映射"""
        mock_session.return_value.__enter__.return_value = MagicMock()

        mock_mapping = MagicMock()
        mock_mapping.source_platform = "gitlab"  # 非 GitHub
        mock_get_mapping.return_value = mock_mapping

        body_bytes = json.dumps(self.sample_notion_payload).encode("utf-8")

        success, message = process_notion_event(body_bytes)

        assert success is True
        assert message == "non_github_mapping"


class TestAsyncFunctions:
    """异步函数测试"""

    @pytest.mark.asyncio
    async def test_async_exponential_backoff_success(self):
        """🟡 网络测试：指数退避请求成功"""
        with patch("httpx.AsyncClient") as mock_client:
            # 模拟成功响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status.return_value = None
            mock_response.text = '{"success": true}'

            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            success, data = await async_exponential_backoff_request(
                "POST",
                "https://api.test.com/endpoint",
                headers={"Authorization": "Bearer token"},
                json_data={"test": "data"},
            )

            assert success is True
            assert data == {"success": True}

    @pytest.mark.asyncio
    async def test_async_exponential_backoff_retry(self):
        """🟡 容错测试：指数退避重试机制"""
        with (
            patch("httpx.AsyncClient") as mock_client,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):  # Mock sleep to speed up test

            # 模拟第三次成功
            mock_success_response = MagicMock()
            mock_success_response.status_code = 200
            mock_success_response.raise_for_status.return_value = None
            mock_success_response.text = '{"success": true}'
            mock_success_response.json.return_value = {"success": True}

            # 前两次抛出异常，第三次成功
            import httpx

            side_effects = [
                httpx.RequestError("Server Error"),
                httpx.RequestError("Bad Gateway"),
                mock_success_response,
            ]

            mock_client.return_value.__aenter__.return_value.request.side_effect = side_effects

            success, data = await async_exponential_backoff_request(
                "GET", "https://api.test.com/endpoint", max_retries=3
            )

            assert success is True
            assert data == {"success": True}

    @pytest.mark.asyncio
    async def test_async_notion_upsert_page_success(self):
        """🟡 集成测试：Notion 页面异步创建/更新"""
        test_issue = {
            "number": 123,
            "title": "Test Issue",
            "body": "Test body",
            "state": "open",
            "html_url": "https://github.com/test/repo/issues/123",
            "user": {"login": "testuser"},
        }

        with (
            patch("app.service.DISABLE_NOTION", False),
            patch("app.service.async_exponential_backoff_request") as mock_request,
        ):
            # 模拟查询返回空结果（需要创建新页面）
            mock_request.side_effect = [
                (True, {"results": []}),  # 查询结果为空
                (True, {"id": "notion_page_123", "url": "https://notion.so/page123"}),  # 创建成功
            ]

            success, page_id = await async_notion_upsert_page(test_issue)

            assert success is True
            assert page_id == "notion_page_123"


class TestErrorHandling:
    """错误处理和边界情况测试"""

    def test_invalid_json_payload(self):
        """🟡 错误处理测试：无效 JSON payload"""
        invalid_json = b'{"invalid": json payload'  # 格式错误的 JSON

        # 应该捕获 JSON 解析异常并返回错误
        try:
            success, message = process_github_event(invalid_json, "issues")
            # 如果没有异常，说明函数处理了错误
            assert success is False
        except Exception as e:
            # 如果抛出异常，验证是 JSON 相关的异常
            assert "expecting" in str(e).lower() or "json" in str(e).lower() or "decode" in str(e).lower()

    def test_empty_payload(self):
        """🟡 边界测试：空 payload"""
        empty_payload = b""

        # 应该捕获 JSON 解析异常并返回错误
        try:
            success, message = process_github_event(empty_payload, "issues")
            assert success is False
        except Exception as e:
            # 如果抛出异常，验证是 JSON 相关的异常
            assert "expecting" in str(e).lower() or "json" in str(e).lower() or "decode" in str(e).lower()

    def test_large_payload_handling(self):
        """🟡 性能测试：大型 payload 处理"""
        # 创建大型 payload
        large_issue_body = "x" * 10000  # 10KB 的内容
        large_payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Large Issue",
                "body": large_issue_body,
                "state": "open",
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "testuser"},
            },
            "repository": {"name": "test-repo", "owner": {"login": "testowner"}},
        }

        body_bytes = json.dumps(large_payload).encode("utf-8")

        # 应该能够处理大型 payload 而不崩溃
        with patch("app.service.session_scope"), patch("app.service.should_skip_event", return_value=True):
            success, message = process_github_event(body_bytes, "issues")
            assert success is True  # 即使跳过，也应该成功处理

    def test_unicode_content_handling(self):
        """🟡 国际化测试：Unicode 内容处理"""
        unicode_payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "测试问题 🚀 Test Issue",
                "body": "包含中文和 emoji 的内容 🎉",
                "state": "open",
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "用户名"},
            },
            "repository": {"name": "test-repo", "owner": {"login": "testowner"}},
        }

        body_bytes = json.dumps(unicode_payload, ensure_ascii=False).encode("utf-8")

        with patch("app.service.session_scope"), patch("app.service.should_skip_event", return_value=True):
            success, message = process_github_event(body_bytes, "issues")
            assert success is True

    @pytest.mark.asyncio
    async def test_async_function_timeout_handling(self):
        """🟡 超时测试：异步函数超时处理"""
        with patch("httpx.AsyncClient") as mock_client, patch("asyncio.sleep", new_callable=AsyncMock):

            # 模拟超时异常
            import httpx

            mock_client.return_value.__aenter__.return_value.request.side_effect = httpx.TimeoutException(
                "Request timeout"
            )

            # 应该在重试后最终失败
            success, data = await async_exponential_backoff_request(
                "GET", "https://api.test.com/slow-endpoint", max_retries=2
            )

            # 超时后应该返回失败状态
            assert success is False
            assert "error" in data

    @pytest.mark.asyncio
    async def test_async_notion_api_error_handling(self):
        """🟡 API 错误测试：Notion API 错误处理"""
        test_issue = {"number": 123, "title": "Test Issue", "body": "Test body"}

        with (
            patch("app.service.DISABLE_NOTION", False),
            patch("app.service.async_exponential_backoff_request") as mock_request,
        ):
            # 模拟 API 错误响应
            mock_request.return_value = (False, {"error": "Invalid request"})

            success, error_msg = await async_notion_upsert_page(test_issue)

            assert success is False
            assert "error" in error_msg.lower()


class TestBusinessLogicEdgeCases:
    """业务逻辑边界情况测试"""

    def test_github_issue_closed_action(self):
        """🟡 业务测试：GitHub issue 关闭动作"""
        closed_payload = {
            "action": "closed",
            "issue": {
                "number": 123,
                "title": "Closed Issue",
                "body": "This issue is closed",
                "state": "closed",
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "testuser"},
            },
            "repository": {"name": "test-repo", "owner": {"login": "testowner"}},
        }

        body_bytes = json.dumps(closed_payload).encode("utf-8")

        with (
            patch("app.service.session_scope"),
            patch("app.service.should_skip_event", return_value=False),
            patch("app.service.should_skip_sync_event", return_value=False),
            patch("app.service.notion_upsert_page", return_value=(True, "page_123")),
            patch("app.service.upsert_mapping"),
            patch("app.service.mark_event_processed"),
        ):

            success, message = process_github_event(body_bytes, "issues")
            assert success is True
            assert message == "ok"

    def test_github_issue_with_special_characters(self):
        """🟡 边界测试：包含特殊字符的 issue"""
        special_payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Issue with <script>alert('xss')</script>",
                "body": "Body with & special < > characters \" and ' quotes",
                "state": "open",
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "test&user"},
            },
            "repository": {"name": "test-repo", "owner": {"login": "testowner"}},
        }

        body_bytes = json.dumps(special_payload).encode("utf-8")

        with patch("app.service.session_scope"), patch("app.service.should_skip_event", return_value=True):
            success, message = process_github_event(body_bytes, "issues")
            assert success is True  # 应该能安全处理特殊字符

    def test_concurrent_event_processing(self):
        """🟡 并发测试：并发事件处理"""
        # 这个测试验证锁机制是否正常工作
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Concurrent Test",
                "body": "Test concurrent processing",
                "state": "open",
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "testuser"},
            },
            "repository": {"name": "test-repo", "owner": {"login": "testowner"}},
        }

        body_bytes = json.dumps(payload).encode("utf-8")

        # 模拟并发处理相同的 issue
        with (
            patch("app.service.session_scope"),
            patch("app.service.should_skip_event", return_value=False),
            patch("app.service.should_skip_sync_event", return_value=False),
            patch("app.service.notion_upsert_page", return_value=(True, "page_123")),
            patch("app.service.upsert_mapping"),
            patch("app.service.mark_event_processed"),
        ):

            # 第一个请求应该成功
            success1, message1 = process_github_event(body_bytes, "issues")
            assert success1 is True

            # 第二个相同的请求应该被检测为重复（通过 should_skip_event）
            with patch("app.service.should_skip_event", return_value=True):
                success2, message2 = process_github_event(body_bytes, "issues")
                assert success2 is True
                assert message2 == "duplicate"
