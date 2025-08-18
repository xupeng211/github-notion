"""
最小化service.py覆盖率测试
专注于最便宜的覆盖点：锁管理、会话管理、签名验证
"""

from unittest.mock import Mock, patch


class TestServiceMinimal:
    """service.py最小覆盖率测试"""

    def test_get_issue_lock_basic(self):
        """测试issue锁获取基础功能"""
        from app.service import _get_issue_lock

        # 测试获取锁
        lock1 = _get_issue_lock("issue-123")
        assert lock1 is not None

        # 测试相同ID返回相同锁
        lock2 = _get_issue_lock("issue-123")
        assert lock1 is lock2

        # 测试不同ID返回不同锁
        lock3 = _get_issue_lock("issue-456")
        assert lock3 is not lock1

    def test_session_scope_success(self):
        """测试数据库会话上下文管理器成功路径"""
        from app.service import session_scope

        # Mock SessionLocal
        with patch("app.service.SessionLocal") as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session

            # 测试正常使用
            with session_scope() as db_session:
                assert db_session is mock_session

            # 验证session被正确关闭
            mock_session.close.assert_called_once()

    def test_session_scope_exception(self):
        """测试数据库会话上下文管理器异常处理"""
        from app.service import session_scope

        # Mock SessionLocal
        with patch("app.service.SessionLocal") as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session

            # 测试异常情况下session仍被关闭
            try:
                with session_scope() as db_session:
                    assert db_session is mock_session
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # 验证即使有异常，session也被正确关闭
            mock_session.close.assert_called_once()

    def test_verify_notion_signature_no_secret(self):
        """测试Notion签名验证 - 无密钥情况"""
        from app.service import verify_notion_signature

        # 无密钥时应该跳过验证
        result = verify_notion_signature("", b"payload", "signature")
        assert result is True

    def test_verify_notion_signature_no_signature(self):
        """测试Notion签名验证 - 无签名情况"""
        from app.service import verify_notion_signature

        # 无签名时应该返回False
        result = verify_notion_signature("secret", b"payload", "")
        assert result is False

    def test_verify_notion_signature_valid(self):
        """测试Notion签名验证 - 有效签名"""
        import hashlib
        import hmac

        from app.service import verify_notion_signature

        secret = "test-secret"
        payload = b"test-payload"

        # 生成正确的签名
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # 验证正确签名
        result = verify_notion_signature(secret, payload, signature)
        assert result is True

    def test_verify_notion_signature_invalid(self):
        """测试Notion签名验证 - 无效签名"""
        from app.service import verify_notion_signature

        # 验证错误签名
        result = verify_notion_signature("secret", b"payload", "invalid-signature")
        assert result is False

    def test_exponential_backoff_request_basic(self):
        """测试指数退避请求基础功能"""
        from app.service import exponential_backoff_request

        # Mock requests.request
        with patch("app.service.requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_request.return_value = mock_response

            success, result = exponential_backoff_request("GET", "https://api.example.com/test")

            assert success is True
            assert result == {"success": True}
            mock_request.assert_called_once()

    def test_disable_metrics_flag(self):
        """测试指标禁用标志"""
        from app.service import DISABLE_METRICS

        # 测试指标禁用标志存在
        assert isinstance(DISABLE_METRICS, bool)
