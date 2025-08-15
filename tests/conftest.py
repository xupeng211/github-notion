"""
pytest配置文件 - 设置测试环境全局配置
"""

import os


def pytest_configure(config):
    """设置测试环境变量"""
    # 确保测试环境配置正确
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DISABLE_METRICS"] = "1"
    os.environ["DISABLE_NOTION"] = "1"
    os.environ["GITEE_WEBHOOK_SECRET"] = "test-webhook-secret-for-testing-12345678"
    os.environ["GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret-for-testing-12345678"
    os.environ["DEADLETTER_REPLAY_TOKEN"] = "test-deadletter-token-for-testing-12345678"
    os.environ["LOG_LEVEL"] = "WARNING"
