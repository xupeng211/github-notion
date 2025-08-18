"""
🔧 CI/CD 环境配置验证器
专为 CI/CD 环境设计的宽松配置验证
"""

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def validate_config_for_ci() -> bool:
    """
    CI/CD 环境的配置验证
    只验证关键配置，允许占位符值
    """

    # 基础配置检查
    config_summary = {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "app_port": os.getenv("APP_PORT", "8000"),
        "db_url": os.getenv("DB_URL", "sqlite:///./data/app.db"),
    }

    logger.info("CI/CD 配置验证", extra={"config_summary": config_summary})

    # 检查关键环境变量是否存在（允许占位符值）
    required_vars = [
        "GITHUB_WEBHOOK_SECRET",
        "DEADLETTER_REPLAY_TOKEN",
    ]

    missing_vars = []
    placeholder_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        elif value.startswith("placeholder_"):
            placeholder_vars.append(var)

    # 在 CI/CD 环境中，允许占位符值
    if missing_vars:
        logger.error(f"缺少必需的环境变量: {missing_vars}")
        return False

    if placeholder_vars:
        logger.warning(f"使用占位符值的变量: {placeholder_vars}")
        logger.warning("这在 CI/CD 环境中是可接受的，但在生产环境中需要真实值")

    logger.info("✅ CI/CD 配置验证通过")
    return True


def validate_config_on_startup_ci():
    """
    CI/CD 环境启动时的配置验证
    """
    logger.info("开始 CI/CD 配置验证...")

    if not validate_config_for_ci():
        logger.error("❌ CI/CD 配置验证失败")
        # 在 CI/CD 环境中，我们可以选择继续运行而不是退出
        # 这样可以让健康检查端点正常工作
        logger.warning("⚠️ 继续启动，但某些功能可能不可用")
    else:
        logger.info("✅ CI/CD 配置验证成功")
