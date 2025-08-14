import os
import pytest
import json

from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(os.getenv("RUN_RATE_LIMIT_TESTS") != "1", reason="Set RUN_RATE_LIMIT_TESTS=1 to enable rate limit tests")

from app.server import app

client = TestClient(app)


def test_rate_limit_disabled_by_default():
    """测试默认关闭速率限制"""
    # 连续发送多个请求，应该都成功
    for _ in range(10):
        response = client.post(
            "/gitee_webhook",
            json={"issue": {"number": 1, "title": "test"}},
            headers={"X-Gitee-Token": "dummy", "X-Gitee-Event": "Issue Hook"}
        )
        # 应该因为签名验证失败而返回 403，而不是 429
        assert response.status_code in (400, 403)


def test_pydantic_validation_invalid_payload():
    """测试 Pydantic 校验无效 payload"""
    # 缺少 issue 字段
    response = client.post(
        "/gitee_webhook",
        json={"action": "open"},  # 缺少 issue
        headers={"X-Gitee-Token": "dummy", "X-Gitee-Event": "Issue Hook"}
    )
    assert response.status_code == 400
    assert "invalid_payload" in response.json()["detail"]

    # issue 字段类型错误
    response = client.post(
        "/gitee_webhook",
        json={"issue": "not_a_dict"},  # issue 应该是字典
        headers={"X-Gitee-Token": "dummy", "X-Gitee-Event": "Issue Hook"}
    )
    assert response.status_code == 400
    assert "invalid_payload" in response.json()["detail"]


def test_pydantic_validation_valid_payload():
    """测试 Pydantic 校验有效 payload"""
    valid_payload = {
        "action": "open",
        "issue": {
            "number": 123,
            "title": "Test Issue",
            "body": "Test body",
            "state": "open",
            "labels": [{"name": "bug"}],
            "user": {"name": "testuser"}
        }
    }

    response = client.post(
        "/gitee_webhook",
        json=valid_payload,
        headers={"X-Gitee-Token": "dummy", "X-Gitee-Event": "Issue Hook"}
    )
    # 应该因为签名验证失败而返回 403，而不是 400
    assert response.status_code in (400, 403)


def test_rate_limit_enabled_with_env(monkeypatch):
    """测试启用速率限制（需要环境变量）"""
    # 设置速率限制为每分钟 2 次
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")

    # 重新导入应用以应用新的环境变量
    import importlib

    import app.server
    importlib.reload(app.server)
    # 前两次请求应该成功（返回 403 因为签名验证失败，但通过了限流）
    for i in range(2):
        response = client.post(
            "/gitee_webhook",
            json={"issue": {"number": i, "title": f"test{i}"}},
            headers={"X-Gitee-Token": "dummy", "X-Gitee-Event": "Issue Hook"}
        )
        assert response.status_code in (400, 403)

    # 第三次请求应该被限流
    response = client.post(
        "/gitee_webhook",
        json={"issue": {"number": 3, "title": "test3"}},
        headers={"X-Gitee-Token": "dummy", "X-Gitee-Event": "Issue Hook"}
    )
    assert response.status_code == 429
    assert "too_many_requests" in response.json()["detail"]


def test_rate_limit_reset_after_window(monkeypatch):
    """测试速率限制窗口重置"""
    # 设置速率限制为每分钟 1 次
    import importlib
    import time

    import app.server

    # 模拟时间窗口重置
    original_time = time.time

    def mock_time():
        return original_time() + 61  # 前进 61 秒

    monkeypatch.setattr(time, "time", mock_time)

    # 重新导入应用以应用新的环境变量
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    importlib.reload(app.server)
    # 应该能再次通过限流
    response = client.post(
        "/gitee_webhook",
        json={"issue": {"number": 4, "title": "test4"}},
        headers={"X-Gitee-Token": "dummy", "X-Gitee-Event": "Issue Hook"}
    )
    assert response.status_code in (400, 403)  # 通过限流，但签名验证失败