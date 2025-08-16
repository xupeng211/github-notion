"""
测试工具函数 - 提高覆盖率
"""

from datetime import datetime, timezone

from app.utils import (
    extract_issue_info,
    format_datetime,
    generate_sync_hash,
    is_valid_url,
    safe_json_loads,
    validate_webhook_signature,
)


class TestUtils:
    """测试工具函数"""

    def test_validate_webhook_signature_valid(self):
        """测试有效的 webhook 签名验证"""
        payload = b'{"test": "data"}'
        secret = "test-secret"
        # 使用 HMAC-SHA256 计算正确的签名
        import hashlib
        import hmac

        expected_signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        result = validate_webhook_signature(payload, expected_signature, secret)
        assert result is True

    def test_validate_webhook_signature_invalid(self):
        """测试无效的 webhook 签名验证"""
        payload = b'{"test": "data"}'
        secret = "test-secret"
        invalid_signature = "sha256=invalid_signature"

        result = validate_webhook_signature(payload, invalid_signature, secret)
        assert result is False

    def test_validate_webhook_signature_missing_prefix(self):
        """测试缺少 sha256= 前缀的签名"""
        payload = b'{"test": "data"}'
        secret = "test-secret"
        signature_without_prefix = "abcdef123456"

        result = validate_webhook_signature(payload, signature_without_prefix, secret)
        assert result is False

    def test_extract_issue_info_github(self):
        """测试从 GitHub payload 提取 issue 信息"""
        payload = {
            "action": "opened",
            "issue": {
                "id": 123,
                "number": 456,
                "title": "Test Issue",
                "body": "This is a test issue",
                "state": "open",
                "html_url": "https://github.com/user/repo/issues/456",
                "user": {"login": "testuser"},
            },
            "repository": {"full_name": "user/repo"},
        }

        info = extract_issue_info(payload, "github")
        assert info["id"] == 123
        assert info["number"] == 456
        assert info["title"] == "Test Issue"
        assert info["state"] == "open"
        assert info["platform"] == "github"

    def test_extract_issue_info_gitee(self):
        """测试从 Gitee payload 提取 issue 信息"""
        payload = {
            "action": "open",
            "issue": {
                "id": 789,
                "number": "I123",
                "title": "Gitee Issue",
                "body": "This is a gitee issue",
                "state": "open",
                "html_url": "https://gitee.com/user/repo/issues/I123",
                "user": {"login": "giteeuser"},
            },
            "repository": {"full_name": "user/repo"},
        }

        info = extract_issue_info(payload, "gitee")
        assert info["id"] == 789
        assert info["number"] == "I123"
        assert info["title"] == "Gitee Issue"
        assert info["platform"] == "gitee"

    def test_extract_issue_info_missing_fields(self):
        """测试缺少字段的 payload"""
        payload = {
            "action": "opened",
            "issue": {
                "id": 123,
                "title": "Incomplete Issue"
                # 缺少其他字段
            },
        }

        info = extract_issue_info(payload, "github")
        assert info["id"] == 123
        assert info["title"] == "Incomplete Issue"
        assert info.get("number") is None
        assert info.get("body") is None

    def test_format_datetime_with_timezone(self):
        """测试带时区的日期时间格式化"""
        dt = datetime(2023, 12, 25, 15, 30, 45, tzinfo=timezone.utc)
        formatted = format_datetime(dt)
        assert "2023-12-25" in formatted
        assert "15:30:45" in formatted

    def test_format_datetime_naive(self):
        """测试无时区的日期时间格式化"""
        dt = datetime(2023, 12, 25, 15, 30, 45)
        formatted = format_datetime(dt)
        assert "2023-12-25" in formatted
        assert "15:30:45" in formatted

    def test_format_datetime_none(self):
        """测试 None 值的日期时间格式化"""
        formatted = format_datetime(None)
        assert formatted == ""

    def test_safe_json_loads_valid(self):
        """测试有效 JSON 字符串解析"""
        json_str = '{"key": "value", "number": 123}'
        result = safe_json_loads(json_str)
        assert result == {"key": "value", "number": 123}

    def test_safe_json_loads_invalid(self):
        """测试无效 JSON 字符串解析"""
        invalid_json = '{"key": "value", invalid}'
        result = safe_json_loads(invalid_json)
        assert result == {}

    def test_safe_json_loads_empty(self):
        """测试空字符串解析"""
        result = safe_json_loads("")
        assert result == {}

    def test_safe_json_loads_none(self):
        """测试 None 值解析"""
        result = safe_json_loads(None)
        assert result == {}

    def test_generate_sync_hash_consistent(self):
        """测试同步哈希生成的一致性"""
        data = {"id": 123, "title": "Test", "updated_at": "2023-12-25T15:30:45Z"}
        hash1 = generate_sync_hash(data)
        hash2 = generate_sync_hash(data)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 哈希长度

    def test_generate_sync_hash_different_data(self):
        """测试不同数据生成不同哈希"""
        data1 = {"id": 123, "title": "Test 1"}
        data2 = {"id": 123, "title": "Test 2"}
        hash1 = generate_sync_hash(data1)
        hash2 = generate_sync_hash(data2)
        assert hash1 != hash2

    def test_is_valid_url_valid_urls(self):
        """测试有效 URL 验证"""
        valid_urls = [
            "https://github.com/user/repo",
            "http://example.com",
            "https://api.notion.com/v1/pages",
            "https://gitee.com/user/repo/issues/123",
        ]

        for url in valid_urls:
            assert is_valid_url(url) is True, f"URL should be valid: {url}"

    def test_is_valid_url_invalid_urls(self):
        """测试无效 URL 验证"""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # 不支持的协议
            "https://",  # 不完整的 URL
            "",  # 空字符串
            None,  # None 值
            "javascript:alert('xss')",  # 危险的协议
        ]

        for url in invalid_urls:
            assert is_valid_url(url) is False, f"URL should be invalid: {url}"
