"""
🚀 性能基准测试
测试系统关键功能的性能指标
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from app.service import async_notion_upsert_page, process_github_event
from app.webhook_security import WebhookSecurityValidator, validate_webhook_security


class TestPerformanceBenchmarks:
    """性能基准测试"""

    def test_webhook_security_performance(self, benchmark):
        """🚀 性能测试：Webhook 安全验证性能"""
        validator = WebhookSecurityValidator("test_secret", "github")
        payload = b'{"test": "data"}' * 100  # 1KB payload

        import hashlib
        import hmac

        signature = "sha256=" + hmac.new("test_secret".encode(), payload, hashlib.sha256).hexdigest()

        # 基准测试
        result = benchmark(validator.verify_signature, payload, signature)

        assert result is True

        # 性能断言
        assert benchmark.stats["mean"] < 0.001  # 平均响应时间 < 1ms
        assert benchmark.stats["max"] < 0.005  # 最大响应时间 < 5ms

    def test_webhook_validation_performance(self, benchmark):
        """🚀 性能测试：完整 Webhook 验证性能"""
        payload = b'{"action": "opened", "issue": {"number": 123}}' * 50  # 2KB payload

        import hashlib
        import hmac

        signature = "sha256=" + hmac.new("test_secret".encode(), payload, hashlib.sha256).hexdigest()

        # 基准测试
        result = benchmark(validate_webhook_security, payload, signature, "test_secret", "github", "delivery_123")

        assert result[0] is True

        # 性能断言
        assert benchmark.stats["mean"] < 0.005  # 平均响应时间 < 5ms

    @patch("app.service.session_scope")
    @patch("app.service.should_skip_event")
    @patch("app.service.should_skip_sync_event")
    @patch("app.service.notion_upsert_page")
    @patch("app.service.upsert_mapping")
    @patch("app.service.mark_event_processed")
    def test_github_event_processing_performance(
        self, mock_mark, mock_upsert, mock_notion, mock_skip_sync, mock_skip_event, mock_session, benchmark
    ):
        """🚀 性能测试：GitHub 事件处理性能"""
        # 设置 mocks
        mock_session.return_value.__enter__.return_value = MagicMock()
        mock_skip_event.return_value = False
        mock_skip_sync.return_value = False
        mock_notion.return_value = (True, "page_123")

        # 创建测试 payload
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Performance Test Issue",
                "body": "Test issue for performance benchmarking",
                "state": "open",
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "testuser"},
            },
            "repository": {"name": "test-repo", "owner": {"login": "testowner"}},
        }

        import json

        body_bytes = json.dumps(payload).encode("utf-8")

        # 基准测试
        result = benchmark(process_github_event, body_bytes, "issues")

        assert result[0] is True

        # 性能断言
        assert benchmark.stats["mean"] < 0.1  # 平均响应时间 < 100ms
        assert benchmark.stats["max"] < 0.5  # 最大响应时间 < 500ms

    @pytest.mark.asyncio
    async def test_async_notion_upsert_performance(self, benchmark):
        """🚀 性能测试：异步 Notion 页面创建性能"""
        test_issue = {
            "number": 123,
            "title": "Performance Test Issue",
            "body": "Test issue for performance benchmarking",
            "state": "open",
            "html_url": "https://github.com/test/repo/issues/123",
            "user": {"login": "testuser"},
        }

        with (
            patch("app.service.DISABLE_NOTION", False),
            patch("app.service.async_exponential_backoff_request") as mock_request,
        ):

            # Mock 快速响应
            mock_request.side_effect = [
                (True, {"results": []}),  # 查询结果
                (True, {"id": "page_123", "url": "https://notion.so/page123"}),  # 创建结果
            ]

            # 异步基准测试
            async def run_test():
                return await async_notion_upsert_page(test_issue)

            result = benchmark(asyncio.run, run_test())

            assert result[0] is True

            # 性能断言
            assert benchmark.stats["mean"] < 0.05  # 平均响应时间 < 50ms

    def test_large_payload_processing_performance(self, benchmark):
        """🚀 性能测试：大型 payload 处理性能"""
        # 创建 10KB 的大型 payload
        large_body = "x" * 10000
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Large Payload Test",
                "body": large_body,
                "state": "open",
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "testuser"},
            },
            "repository": {"name": "test-repo", "owner": {"login": "testowner"}},
        }

        import json

        body_bytes = json.dumps(payload).encode("utf-8")

        with patch("app.service.session_scope"), patch("app.service.should_skip_event", return_value=True):

            # 基准测试
            result = benchmark(process_github_event, body_bytes, "issues")

            assert result[0] is True

            # 性能断言 (大型 payload 允许更长时间)
            assert benchmark.stats["mean"] < 0.2  # 平均响应时间 < 200ms
            assert benchmark.stats["max"] < 1.0  # 最大响应时间 < 1s

    def test_concurrent_webhook_validation_performance(self, benchmark):
        """🚀 性能测试：并发 Webhook 验证性能"""
        validator = WebhookSecurityValidator("test_secret", "github")
        payload = b'{"test": "concurrent_data"}'

        import hashlib
        import hmac

        signature = "sha256=" + hmac.new("test_secret".encode(), payload, hashlib.sha256).hexdigest()

        def concurrent_validation():
            """模拟并发验证"""
            results = []
            for i in range(10):  # 10个并发验证
                result = validator.verify_signature(payload, signature)
                results.append(result)
            return all(results)

        # 基准测试
        result = benchmark(concurrent_validation)

        assert result is True

        # 性能断言 (并发场景允许更长时间)
        assert benchmark.stats["mean"] < 0.01  # 平均响应时间 < 10ms


class TestMemoryUsage:
    """内存使用测试"""

    def test_webhook_security_memory_usage(self):
        """🧠 内存测试：Webhook 安全验证内存使用"""
        import tracemalloc

        tracemalloc.start()

        validator = WebhookSecurityValidator("test_secret", "github")
        payload = b'{"test": "memory_test"}' * 1000  # 10KB payload

        import hashlib
        import hmac

        signature = "sha256=" + hmac.new("test_secret".encode(), payload, hashlib.sha256).hexdigest()

        # 执行多次验证
        for _ in range(100):
            validator.verify_signature(payload, signature)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 内存断言
        assert peak < 10 * 1024 * 1024  # 峰值内存 < 10MB
        print(f"内存使用: 当前 {current / 1024:.1f}KB, 峰值 {peak / 1024:.1f}KB")

    def test_large_payload_memory_usage(self):
        """🧠 内存测试：大型 payload 内存使用"""
        import tracemalloc

        tracemalloc.start()

        # 创建 1MB 的 payload
        large_payload = b'{"data": "' + b"x" * (1024 * 1024) + b'"}'

        validator = WebhookSecurityValidator("test_secret", "github")

        import hashlib
        import hmac

        signature = "sha256=" + hmac.new("test_secret".encode(), large_payload, hashlib.sha256).hexdigest()

        result = validator.verify_signature(large_payload, signature)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert result is True
        # 内存断言 (大型 payload 允许更多内存)
        assert peak < 50 * 1024 * 1024  # 峰值内存 < 50MB
        print(f"大型 payload 内存使用: 当前 {current / 1024 / 1024:.1f}MB, 峰值 {peak / 1024 / 1024:.1f}MB")


class TestStressTests:
    """压力测试"""

    def test_webhook_validation_stress(self):
        """💪 压力测试：Webhook 验证压力测试"""
        validator = WebhookSecurityValidator("test_secret", "github")
        payload = b'{"test": "stress_test"}'

        import hashlib
        import hmac

        signature = "sha256=" + hmac.new("test_secret".encode(), payload, hashlib.sha256).hexdigest()

        start_time = time.time()

        # 执行 1000 次验证
        success_count = 0
        for i in range(1000):
            if validator.verify_signature(payload, signature):
                success_count += 1

        end_time = time.time()
        duration = end_time - start_time

        # 压力测试断言
        assert success_count == 1000  # 所有验证都应该成功
        assert duration < 1.0  # 1000次验证应该在1秒内完成

        throughput = 1000 / duration
        print(f"Webhook 验证吞吐量: {throughput:.0f} 次/秒")

        # 吞吐量断言
        assert throughput > 1000  # 吞吐量 > 1000 次/秒

    @pytest.mark.slow
    def test_extended_stress_test(self):
        """💪 压力测试：扩展压力测试 (标记为慢速测试)"""
        validator = WebhookSecurityValidator("test_secret", "github")

        # 测试不同大小的 payload
        payload_sizes = [100, 1000, 10000]  # 100B, 1KB, 10KB

        for size in payload_sizes:
            payload = b'{"data": "' + b"x" * size + b'"}'

            import hashlib
            import hmac

            signature = "sha256=" + hmac.new("test_secret".encode(), payload, hashlib.sha256).hexdigest()

            start_time = time.time()

            # 执行 100 次验证
            for _ in range(100):
                result = validator.verify_signature(payload, signature)
                assert result is True

            duration = time.time() - start_time
            throughput = 100 / duration

            print(f"Payload {size}B: {throughput:.0f} 次/秒")

            # 性能应该随 payload 大小线性下降
            expected_min_throughput = max(100, 1000 - size)
            assert throughput > expected_min_throughput
