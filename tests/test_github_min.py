"""
最小化github.py覆盖率测试
专注于最便宜的覆盖点：初始化、签名验证
"""

from unittest.mock import patch


class TestGitHubMinimal:
    """github.py最小覆盖率测试"""

    def test_github_service_init_with_env(self):
        """测试GitHub服务初始化 - 有环境变量"""
        with patch.dict(
            "os.environ", {"GITHUB_TOKEN": "ghp_test_token_123", "GITHUB_WEBHOOK_SECRET": "test_webhook_secret"}
        ):
            from app.github import GitHubService

            service = GitHubService()
            assert service.token == "ghp_test_token_123"
            assert service.webhook_secret == "test_webhook_secret"
            assert service.base_url == "https://api.github.com"
            assert service.session is not None

    def test_github_service_init_without_env(self):
        """测试GitHub服务初始化 - 无环境变量"""
        with patch.dict("os.environ", {}, clear=True):
            from app.github import GitHubService

            service = GitHubService()
            assert service.token == ""
            assert service.webhook_secret == ""
            assert service.base_url == "https://api.github.com"
            assert service.session is not None

    def test_verify_webhook_signature_no_secret(self):
        """测试webhook签名验证 - 无密钥"""
        with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": ""}):
            from app.github import GitHubService

            service = GitHubService()
            result = service.verify_webhook_signature(b"payload", "sha256=signature")
            assert result is False

    def test_verify_webhook_signature_no_signature(self):
        """测试webhook签名验证 - 无签名"""
        with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": "secret"}):
            from app.github import GitHubService

            service = GitHubService()
            result = service.verify_webhook_signature(b"payload", "")
            assert result is False

    def test_verify_webhook_signature_invalid_format(self):
        """测试webhook签名验证 - 无效格式"""
        with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": "secret"}):
            from app.github import GitHubService

            service = GitHubService()
            result = service.verify_webhook_signature(b"payload", "invalid-format")
            assert result is False

    def test_verify_webhook_signature_valid(self):
        """测试webhook签名验证 - 有效签名"""
        import hashlib
        import hmac

        secret = "test-secret"
        payload = b"test-payload"

        with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": secret}):
            from app.github import GitHubService

            service = GitHubService()

            # 生成正确的签名
            signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

            result = service.verify_webhook_signature(payload, f"sha256={signature}")
            assert result is True

    def test_verify_webhook_signature_invalid(self):
        """测试webhook签名验证 - 无效签名"""
        with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": "secret"}):
            from app.github import GitHubService

            service = GitHubService()
            result = service.verify_webhook_signature(b"payload", "sha256=invalid-signature")
            assert result is False

    def test_github_service_session_configuration(self):
        """测试GitHub服务会话配置"""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            from app.github import GitHubService

            service = GitHubService()

            # 验证会话配置
            assert service.session is not None
            assert "Authorization" in service.session.headers
            assert service.session.headers["Authorization"] == "Bearer test_token"
            assert service.session.headers["Accept"] == "application/vnd.github+json"
