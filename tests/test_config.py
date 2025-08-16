"""
测试配置模块 - 提高覆盖率
"""

import os
from unittest.mock import patch

from app.config import Config


class TestConfig:
    """测试配置类"""

    def test_config_defaults(self):
        """测试配置默认值"""
        config = Config()

        # 测试默认值
        assert config.ENVIRONMENT == "development"
        assert config.LOG_LEVEL == "INFO"
        assert config.PORT == 8000
        assert config.DISABLE_METRICS is False
        assert config.DISABLE_NOTION is False

    def test_config_from_env(self):
        """测试从环境变量读取配置"""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
                "LOG_LEVEL": "ERROR",
                "PORT": "9000",
                "DISABLE_METRICS": "1",
                "DISABLE_NOTION": "true",
                "GITHUB_TOKEN": "test-github-token",
                "NOTION_TOKEN": "test-notion-token",
            },
        ):
            config = Config()

            assert config.ENVIRONMENT == "production"
            assert config.LOG_LEVEL == "ERROR"
            assert config.PORT == 9000
            assert config.DISABLE_METRICS is True
            assert config.DISABLE_NOTION is True
            assert config.GITHUB_TOKEN == "test-github-token"
            assert config.NOTION_TOKEN == "test-notion-token"

    def test_config_boolean_parsing(self):
        """测试布尔值解析"""
        test_cases = [
            ("1", True),
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("yes", True),
            ("0", False),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("no", False),
            ("", False),
            ("invalid", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"DISABLE_METRICS": env_value}):
                config = Config()
                assert config.DISABLE_METRICS == expected, f"Failed for value: {env_value}"

    def test_config_int_parsing(self):
        """测试整数解析"""
        with patch.dict(os.environ, {"PORT": "3000"}):
            config = Config()
            assert config.PORT == 3000
            assert isinstance(config.PORT, int)

    def test_config_invalid_int(self):
        """测试无效整数使用默认值"""
        with patch.dict(os.environ, {"PORT": "invalid"}):
            config = Config()
            assert config.PORT == 8000  # 应该使用默认值

    def test_config_webhook_secrets(self):
        """测试 webhook 密钥配置"""
        with patch.dict(
            os.environ, {"GITHUB_WEBHOOK_SECRET": "github-secret-123", "GITEE_WEBHOOK_SECRET": "gitee-secret-456"}
        ):
            config = Config()
            assert config.GITHUB_WEBHOOK_SECRET == "github-secret-123"
            assert config.GITEE_WEBHOOK_SECRET == "gitee-secret-456"

    def test_config_database_url(self):
        """测试数据库 URL 配置"""
        with patch.dict(os.environ, {"DB_URL": "sqlite:///custom.db"}):
            config = Config()
            assert config.DB_URL == "sqlite:///custom.db"

    def test_config_notion_settings(self):
        """测试 Notion 相关配置"""
        with patch.dict(
            os.environ,
            {"NOTION_TOKEN": "notion-token-123", "NOTION_DATABASE_ID": "db-123", "NOTION_PAGE_ID": "page-123"},
        ):
            config = Config()
            assert config.NOTION_TOKEN == "notion-token-123"
            assert config.NOTION_DATABASE_ID == "db-123"
            assert config.NOTION_PAGE_ID == "page-123"

    def test_config_aws_settings(self):
        """测试 AWS 相关配置"""
        with patch.dict(
            os.environ,
            {
                "AWS_ACCESS_KEY_ID": "aws-key-123",
                "AWS_SECRET_ACCESS_KEY": "aws-secret-123",
                "AWS_REGION": "us-west-2",
                "SQS_QUEUE_URL": "https://sqs.us-west-2.amazonaws.com/123/queue",
            },
        ):
            config = Config()
            assert config.AWS_ACCESS_KEY_ID == "aws-key-123"
            assert config.AWS_SECRET_ACCESS_KEY == "aws-secret-123"
            assert config.AWS_REGION == "us-west-2"
            assert config.SQS_QUEUE_URL == "https://sqs.us-west-2.amazonaws.com/123/queue"

    def test_config_empty_values(self):
        """测试空值处理"""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "NOTION_TOKEN": "", "LOG_LEVEL": ""}):
            config = Config()
            assert config.GITHUB_TOKEN == ""
            assert config.NOTION_TOKEN == ""
            assert config.LOG_LEVEL == ""  # 空字符串应该被保留

    def test_config_missing_env_vars(self):
        """测试缺失环境变量的处理"""
        # 清除可能存在的环境变量

        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            # 缺失的环境变量应该返回空字符串或默认值
            assert hasattr(config, "ENVIRONMENT")
            assert hasattr(config, "LOG_LEVEL")
            assert hasattr(config, "PORT")
