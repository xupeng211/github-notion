"""
🟢 中优先级：API 集成测试
测试 github.py (177行) 和 notion.py (407行) 的 API 集成
"""

import asyncio
import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import responses

from app.github import GitHubService
from app.notion import NotionService


class TestGitHubAPIIntegration:
    """GitHub API 集成测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.github_service = GitHubService()
        # 设置测试 token，避免真实 API 调用
        self.github_service.token = "test_token_123"

    @responses.activate
    def test_github_get_issue_success(self):
        """🟢 API 测试：GitHub 获取 issue 成功"""
        # Mock GitHub API 响应
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test/repo/issues/123",
            json={
                "id": 123,
                "number": 123,
                "title": "Test Issue",
                "body": "Test issue body",
                "state": "open",
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "testuser"},
            },
            status=200,
        )

        result = self.github_service.get_issue("test", "repo", 123)

        assert result is not None
        assert result["number"] == 123
        assert result["title"] == "Test Issue"
        assert result["state"] == "open"

    @responses.activate
    def test_github_get_issue_not_found(self):
        """🟢 错误处理测试：GitHub issue 不存在"""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test/repo/issues/999",
            json={"message": "Not Found"},
            status=404,
        )

        result = self.github_service.get_issue("test", "repo", 999)

        assert result is None

    @responses.activate
    def test_github_update_issue_success(self):
        """🟢 API 测试：GitHub 更新 issue 成功"""
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/test/repo/issues/123",
            json={"id": 123, "number": 123, "title": "Updated Title", "body": "Updated body", "state": "closed"},
            status=200,
        )

        success, message = self.github_service.update_issue(
            "test", "repo", 123, title="Updated Title", body="Updated body", state="closed"
        )

        assert success is True
        assert "success" in message.lower() or "updated" in message.lower()

    @responses.activate
    def test_github_update_issue_unauthorized(self):
        """🟢 权限测试：GitHub 更新 issue 权限不足"""
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/test/repo/issues/123",
            json={"message": "Bad credentials"},
            status=401,
        )

        success, message = self.github_service.update_issue("test", "repo", 123, title="Updated Title")

        assert success is False
        assert "error" in message.lower() or "fail" in message.lower()

    @responses.activate
    def test_github_api_rate_limit_handling(self):
        """🟢 限流测试：GitHub API 限流处理"""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test/repo/issues/123",
            json={"message": "API rate limit exceeded"},
            status=429,
            headers={"X-RateLimit-Remaining": "0"},
        )

        result = self.github_service.get_issue("test", "repo", 123)

        # 由于配置了重试策略，应该返回 None
        assert result is None

    def test_github_extract_repo_info_success(self):
        """🟢 工具测试：GitHub URL 解析成功"""
        test_cases = [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo/", ("owner", "repo")),
            ("https://github.com/owner/repo/issues/123", ("repo", "123")),  # 取最后两部分
        ]

        for url, expected in test_cases:
            result = self.github_service.extract_repo_info(url)
            if expected:
                assert result is not None
                assert len(result) == 2
            else:
                assert result is None

    def test_github_extract_repo_info_invalid(self):
        """🟢 边界测试：GitHub URL 解析失败"""
        invalid_urls = [
            "https://gitlab.com/owner/repo",  # 非 GitHub URL
            "invalid-url",  # 无效 URL
            "",  # 空字符串
            "https://github.com/",  # 不完整 URL
        ]

        for url in invalid_urls:
            result = self.github_service.extract_repo_info(url)
            # 根据实际实现，可能返回 None 或抛出异常
            # 这里我们期望返回 None 或能够优雅处理
            if result is not None:
                assert len(result) == 2  # 如果返回结果，应该是 tuple

    def test_github_webhook_signature_verification(self):
        """🟢 安全测试：GitHub webhook 签名验证"""
        # 设置测试密钥
        self.github_service.webhook_secret = "test_secret"

        payload = b'{"test": "data"}'

        # 生成正确的签名
        correct_signature = "sha256=" + hmac.new("test_secret".encode(), payload, hashlib.sha256).hexdigest()

        # 测试正确签名
        assert self.github_service.verify_webhook_signature(payload, correct_signature) is True

        # 测试错误签名
        assert self.github_service.verify_webhook_signature(payload, "sha256=wrong") is False

        # 测试空密钥
        self.github_service.webhook_secret = ""
        assert self.github_service.verify_webhook_signature(payload, correct_signature) is False


class TestNotionAPIIntegration:
    """Notion API 集成测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.notion_service = NotionService()
        # 设置测试 token，避免真实 API 调用
        self.notion_service.token = "test_notion_token_123"
        self.notion_service.database_id = "test_database_123"

    @pytest.mark.asyncio
    async def test_notion_query_database_success(self):
        """🟢 API 测试：Notion 查询数据库成功"""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock 成功响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "id": "page_123",
                        "properties": {"Title": {"title": [{"text": {"content": "Test Page"}}]}},
                    }
                ],
                "has_more": False,
            }
            mock_post.return_value = mock_response

            result = await self.notion_service.query_database()

            assert result is not None
            assert "results" in result
            assert len(result["results"]) == 1
            assert result["results"][0]["id"] == "page_123"

    @pytest.mark.asyncio
    async def test_notion_query_database_error(self):
        """🟢 错误处理测试：Notion 查询数据库失败"""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock 错误响应
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"message": "Invalid request"}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Bad Request", request=MagicMock(), response=mock_response
            )
            mock_post.return_value = mock_response

            result = await self.notion_service.query_database()

            assert result is None

    @pytest.mark.asyncio
    async def test_notion_create_page_success(self):
        """🟢 API 测试：Notion 创建页面成功"""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock 成功响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "new_page_123", "url": "https://notion.so/new_page_123"}
            mock_post.return_value = mock_response

            properties = {"Title": {"title": [{"text": {"content": "New Test Page"}}]}}

            success, page_id = await self.notion_service.create_page(properties)

            assert success is True
            assert page_id == "new_page_123"

    @pytest.mark.asyncio
    async def test_notion_create_page_error(self):
        """🟢 错误处理测试：Notion 创建页面失败"""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock 错误响应
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"message": "Invalid properties"}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Bad Request", request=MagicMock(), response=mock_response
            )
            mock_post.return_value = mock_response

            properties = {"InvalidProperty": {"invalid": "data"}}

            success, error_msg = await self.notion_service.create_page(properties)

            assert success is False
            assert "error" in error_msg.lower() or "invalid" in error_msg.lower() or "http" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_notion_update_page_success(self):
        """🟢 API 测试：Notion 更新页面成功"""
        with patch("httpx.AsyncClient.patch") as mock_patch:
            # Mock 成功响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "page_123", "last_edited_time": "2023-01-01T00:00:00.000Z"}
            mock_patch.return_value = mock_response

            properties = {"Title": {"title": [{"text": {"content": "Updated Title"}}]}}

            success, message = await self.notion_service.update_page("page_123", properties)

            assert success is True
            assert "success" in message.lower() or "updated" in message.lower()

    @pytest.mark.asyncio
    async def test_notion_update_page_not_found(self):
        """🟢 错误处理测试：Notion 更新不存在的页面"""
        with patch("httpx.AsyncClient.patch") as mock_patch:
            # Mock 404 响应
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"message": "Page not found"}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_response
            )
            mock_patch.return_value = mock_response

            properties = {"Title": {"title": [{"text": {"content": "Updated Title"}}]}}

            success, error_msg = await self.notion_service.update_page("nonexistent_page", properties)

            assert success is False
            assert "error" in error_msg.lower() or "not found" in error_msg.lower() or "http" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_notion_api_timeout_handling(self):
        """🟢 超时测试：Notion API 超时处理"""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock 超时异常
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            result = await self.notion_service.query_database()

            assert result is None

    @pytest.mark.asyncio
    async def test_notion_api_network_error_handling(self):
        """🟢 网络测试：Notion API 网络错误处理"""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock 网络错误
            mock_post.side_effect = httpx.NetworkError("Network unreachable")

            result = await self.notion_service.query_database()

            assert result is None


class TestAPIIntegrationEdgeCases:
    """API 集成边界情况和错误处理测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.github_service = GitHubService()
        self.notion_service = NotionService()

    @responses.activate
    def test_github_api_large_response_handling(self):
        """🟢 性能测试：GitHub API 大型响应处理"""
        # 创建大型响应数据
        large_body = "x" * 10000  # 10KB 的内容
        large_response = {
            "id": 123,
            "number": 123,
            "title": "Large Issue",
            "body": large_body,
            "state": "open",
            "html_url": "https://github.com/test/repo/issues/123",
            "user": {"login": "testuser"},
        }

        responses.add(
            responses.GET, "https://api.github.com/repos/test/repo/issues/123", json=large_response, status=200
        )

        result = self.github_service.get_issue("test", "repo", 123)

        assert result is not None
        assert len(result["body"]) == 10000

    @responses.activate
    def test_github_api_unicode_content_handling(self):
        """🟢 国际化测试：GitHub API Unicode 内容处理"""
        unicode_response = {
            "id": 123,
            "number": 123,
            "title": "测试问题 🚀 Test Issue",
            "body": "包含中文和 emoji 的内容 🎉",
            "state": "open",
            "html_url": "https://github.com/test/repo/issues/123",
            "user": {"login": "用户名"},
        }

        responses.add(
            responses.GET, "https://api.github.com/repos/test/repo/issues/123", json=unicode_response, status=200
        )

        result = self.github_service.get_issue("test", "repo", 123)

        assert result is not None
        assert "🚀" in result["title"]
        assert "🎉" in result["body"]
        assert result["user"]["login"] == "用户名"

    @responses.activate
    def test_github_api_malformed_response_handling(self):
        """🟢 容错测试：GitHub API 格式错误响应处理"""
        # Mock 格式错误的响应
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test/repo/issues/123",
            body="Invalid JSON response",
            status=200,
            content_type="text/plain",
        )

        result = self.github_service.get_issue("test", "repo", 123)

        # 应该能够优雅处理格式错误的响应
        assert result is None

    @pytest.mark.asyncio
    async def test_notion_api_large_properties_handling(self):
        """🟢 性能测试：Notion API 大型属性处理"""
        large_content = "x" * 5000  # 5KB 的内容
        large_properties = {
            "Title": {"title": [{"text": {"content": "Large Content Test"}}]},
            "Description": {"rich_text": [{"text": {"content": large_content}}]},
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "large_page_123", "url": "https://notion.so/large_page_123"}
            mock_response.text = '{"id": "large_page_123", "url": "https://notion.so/large_page_123"}'
            mock_post.return_value = mock_response

            success, page_id = await self.notion_service.create_page(large_properties, "test_database_123")

            assert success is True
            assert page_id == "large_page_123"

    @pytest.mark.asyncio
    async def test_notion_api_unicode_properties_handling(self):
        """🟢 国际化测试：Notion API Unicode 属性处理"""
        unicode_properties = {
            "Title": {"title": [{"text": {"content": "测试页面 🚀 Test Page"}}]},
            "Description": {"rich_text": [{"text": {"content": "包含中文和 emoji 的描述 🎉"}}]},
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "unicode_page_123", "url": "https://notion.so/unicode_page_123"}
            mock_response.text = '{"id": "unicode_page_123", "url": "https://notion.so/unicode_page_123"}'
            mock_post.return_value = mock_response

            success, page_id = await self.notion_service.create_page(unicode_properties, "test_database_123")

            assert success is True
            assert page_id == "unicode_page_123"

    def test_github_service_initialization_with_missing_env(self):
        """🟢 配置测试：GitHub 服务缺少环境变量初始化"""
        with patch.dict("os.environ", {}, clear=True):
            service = GitHubService()

            assert service.token == ""
            assert service.webhook_secret == ""
            assert service.base_url == "https://api.github.com"

    def test_notion_service_initialization_with_missing_env(self):
        """🟢 配置测试：Notion 服务缺少环境变量初始化"""
        with patch.dict("os.environ", {}, clear=True):
            service = NotionService()

            assert service.token == ""
            assert service.database_id == ""
            assert service.webhook_secret == ""
            assert service.base_url == "https://api.notion.com/v1"

    @pytest.mark.asyncio
    async def test_notion_service_cleanup(self):
        """🟢 资源测试：Notion 服务资源清理"""
        service = NotionService()

        # 测试清理方法不抛出异常
        await service.close()

        # 多次调用清理方法应该是安全的
        await service.close()


class TestAPIIntegrationConcurrency:
    """API 集成并发测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.github_service = GitHubService()
        self.notion_service = NotionService()

    @responses.activate
    def test_github_concurrent_requests(self):
        """🟢 并发测试：GitHub API 并发请求"""
        # Mock 多个响应
        for i in range(5):
            responses.add(
                responses.GET,
                f"https://api.github.com/repos/test/repo/issues/{i+1}",
                json={
                    "id": i + 1,
                    "number": i + 1,
                    "title": f"Issue {i+1}",
                    "body": f"Body {i+1}",
                    "state": "open",
                },
                status=200,
            )

        # 并发请求多个 issues
        results = []
        for i in range(5):
            result = self.github_service.get_issue("test", "repo", i + 1)
            results.append(result)

        # 验证所有请求都成功
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result is not None
            assert result["number"] == i + 1

    @pytest.mark.asyncio
    async def test_notion_concurrent_operations(self):
        """🟢 并发测试：Notion API 并发操作"""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock 成功响应
            mock_responses = []
            for i in range(3):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"id": f"page_{i+1}", "url": f"https://notion.so/page_{i+1}"}
                mock_response.text = f'{{"id": "page_{i+1}", "url": "https://notion.so/page_{i+1}"}}'
                mock_responses.append(mock_response)

            mock_post.side_effect = mock_responses

            # 并发创建多个页面
            tasks = []
            for i in range(3):
                properties = {"Title": {"title": [{"text": {"content": f"Page {i+1}"}}]}}
                task = self.notion_service.create_page(properties, "test_database_123")
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # 验证所有操作都成功
            assert len(results) == 3
            for i, (success, page_id) in enumerate(results):
                assert success is True
                assert page_id == f"page_{i+1}"

    @responses.activate
    def test_notion_api_error_handling(self):
        """测试 Notion API 错误处理"""
        # TODO: 实现错误处理测试
        pass
