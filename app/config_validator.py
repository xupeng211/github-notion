"""
应用配置验证模块
在FastAPI应用启动时强制校验必须的环境变量
确保生产环境不会使用不安全的默认值
"""

import logging
import os
import sys
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """配置验证结果"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ConfigValidator:
    """配置验证器"""

    # 必须配置的环境变量及其不安全的默认值
    REQUIRED_SECURE_VARS = {
        "GITEE_WEBHOOK_SECRET": [
            "",
            "changeme-secure-token",
            "your_webhook_secret_here",
            "your-gitee-webhook-secret-here",
            "test-secret",
            "CHANGE_ME_SECURE_GITEE_SECRET",
            "CHANGE_ME_STAGING_GITEE_SECRET",
            "CHANGE_ME_PRODUCTION_GITEE_SECRET_MINIMUM_32_CHARS",
        ],
        "GITHUB_WEBHOOK_SECRET": [
            "",
            "changeme-secure-token",
            "your_webhook_secret_here",
            "your-github-webhook-secret-here",
            "test-secret",
            "CHANGE_ME_SECURE_GITHUB_SECRET",
            "CHANGE_ME_STAGING_GITHUB_SECRET",
            "CHANGE_ME_PRODUCTION_GITHUB_SECRET_MINIMUM_32_CHARS",
        ],
        "DEADLETTER_REPLAY_TOKEN": [
            "",
            "your_admin_token_here",
            "changeme-admin-token",
            "CHANGE_ME_SECURE_ADMIN_TOKEN",
            "CHANGE_ME_STAGING_ADMIN_TOKEN",
            "CHANGE_ME_PRODUCTION_ADMIN_TOKEN_MINIMUM_32_CHARS",
        ],
    }

    # 推荐配置的环境变量
    RECOMMENDED_VARS = {
        "GITHUB_TOKEN": [
            "",
            "ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "ghp_STAGING_TOKEN_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "ghp_PRODUCTION_TOKEN_PLEASE_CHANGE_THIS",
        ],
        "NOTION_TOKEN": [
            "",
            "secret_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "secret_STAGING_TOKEN_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "secret_PRODUCTION_TOKEN_PLEASE_CHANGE_THIS",
        ],
        "NOTION_DATABASE_ID": [
            "",
            "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "STAGING_DATABASE_ID_XXXXXXXXXXXXXX",
            "PRODUCTION_DATABASE_ID_CHANGE_ME",
        ],
    }

    # 数据库URL检查
    UNSAFE_DB_PATTERNS = ["sqlite:///", "CHANGE_ME_DB_PASSWORD", "user:password@"]

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.is_production = self.environment.lower() == "production"
        self.is_staging = self.environment.lower() == "staging"

    def validate_all(self) -> ValidationResult:
        """执行完整的配置验证"""
        errors = []
        warnings = []

        # 验证必须的安全变量
        security_errors = self._validate_security_vars()
        errors.extend(security_errors)

        # 验证推荐的配置变量
        config_warnings = self._validate_recommended_vars()
        warnings.extend(config_warnings)

        # 验证数据库配置
        db_issues = self._validate_database_config()
        if self.is_production:
            errors.extend(db_issues)
        else:
            warnings.extend(db_issues)

        # 生产环境特殊检查
        if self.is_production:
            prod_errors = self._validate_production_specific()
            errors.extend(prod_errors)

        # 检查环境变量长度和强度
        strength_warnings = self._validate_credential_strength()
        warnings.extend(strength_warnings)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_security_vars(self) -> List[str]:
        """验证必须的安全变量"""
        errors = []

        for var_name, unsafe_values in self.REQUIRED_SECURE_VARS.items():
            current_value = os.getenv(var_name, "")

            if not current_value:
                errors.append(f"❌ {var_name} 未设置，必须配置")
                continue

            if current_value in unsafe_values:
                errors.append(f"❌ {var_name} 使用不安全的默认值 '{current_value}'，" f"必须修改为安全的随机字符串")
                continue

            # 检查是否包含"CHANGE_ME"模式
            if "CHANGE_ME" in current_value.upper():
                errors.append(f"❌ {var_name} 包含占位符 'CHANGE_ME'，" f"必须修改为真实的安全值")

        return errors

    def _validate_recommended_vars(self) -> List[str]:
        """验证推荐的配置变量"""
        warnings = []

        for var_name, placeholder_values in self.RECOMMENDED_VARS.items():
            current_value = os.getenv(var_name, "")

            if not current_value:
                warnings.append(f"⚠️ {var_name} 未设置，某些功能可能无法正常工作")
                continue

            if current_value in placeholder_values:
                warnings.append(f"⚠️ {var_name} 似乎使用占位符值 '{current_value[:20]}...'，" f"请确保使用真实的API令牌")

        return warnings

    def _validate_database_config(self) -> List[str]:
        """验证数据库配置"""
        issues = []
        db_url = os.getenv("DB_URL", "")

        if not db_url:
            issues.append("❌ DB_URL 未设置")
            return issues

        # 检查不安全的数据库配置
        for pattern in self.UNSAFE_DB_PATTERNS:
            if pattern in db_url:
                if pattern == "sqlite:///" and self.is_production:
                    issues.append("❌ 生产环境不应使用SQLite数据库，" "请使用PostgreSQL或MySQL")
                elif "CHANGE_ME" in pattern:
                    issues.append(f"❌ DB_URL包含占位符密码 '{pattern}'，" f"必须修改为真实密码")
                elif pattern == "user:password@":
                    issues.append("⚠️ DB_URL使用默认用户名密码，建议修改为安全凭证")

        return issues

    def _validate_production_specific(self) -> List[str]:
        """生产环境特殊验证"""
        errors = []

        # 检查日志级别
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if log_level == "DEBUG":
            errors.append("❌ 生产环境不应使用DEBUG日志级别，" "建议使用INFO或WARNING")

        # 检查功能开关
        if os.getenv("DISABLE_NOTION") == "1":
            errors.append("❌ 生产环境不应禁用Notion功能 (DISABLE_NOTION=1)")

        if os.getenv("DISABLE_METRICS") == "1":
            errors.append("❌ 生产环境不应禁用监控指标 (DISABLE_METRICS=1)")

        return errors

    def _validate_credential_strength(self) -> List[str]:
        """验证凭证强度"""
        warnings = []

        # 检查webhook密钥长度
        for var_name in ["GITEE_WEBHOOK_SECRET", "GITHUB_WEBHOOK_SECRET"]:
            value = os.getenv(var_name, "")
            if value and len(value) < 16:
                warnings.append(f"⚠️ {var_name} 长度只有{len(value)}字符，" f"建议至少16字符以提高安全性")
            elif value and len(value) < 32 and self.is_production:
                warnings.append(f"⚠️ {var_name} 在生产环境建议至少32字符，" f"当前{len(value)}字符")

        return warnings

    def get_config_summary(self) -> Dict[str, str]:
        """获取配置摘要（不包含敏感信息）"""
        summary = {
            "environment": self.environment,
            "db_type": "sqlite" if "sqlite" in os.getenv("DB_URL", "") else "external",
            "notion_enabled": ("disabled" if os.getenv("DISABLE_NOTION") == "1" else "enabled"),
            "metrics_enabled": ("disabled" if os.getenv("DISABLE_METRICS") == "1" else "enabled"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        }

        # 检查关键配置是否设置（不显示值）
        for var in self.REQUIRED_SECURE_VARS.keys():
            summary[f"{var.lower()}_configured"] = "yes" if os.getenv(var) else "no"

        return summary


def validate_config_on_startup() -> None:
    """
    在应用启动时验证配置
    如果配置无效则退出应用
    """
    validator = ConfigValidator()
    result = validator.validate_all()

    # 打印配置摘要
    summary = validator.get_config_summary()
    logger.info("应用配置摘要:", extra={"config_summary": summary})

    # 处理警告
    if result.warnings:
        logger.warning("配置警告:")
        for warning in result.warnings:
            logger.warning(f"  {warning}")

    # 处理错误
    if result.errors:
        logger.error("配置验证失败:")
        for error in result.errors:
            logger.error(f"  {error}")

        # 额外提示缺失或占位值的具体变量
        missing = []
        placeholders = []
        for var_name, unsafe_values in ConfigValidator.REQUIRED_SECURE_VARS.items():
            val = os.getenv(var_name, "")
            if not val:
                missing.append(var_name)
            elif val in unsafe_values or "CHANGE_ME" in val.upper():
                placeholders.append(var_name)
        if missing or placeholders:
            logger.error("关键信息: 以下变量缺失或使用占位值")
            if missing:
                logger.error(f"  缺失: {', '.join(missing)}")
            if placeholders:
                logger.error(f"  占位: {', '.join(placeholders)}")

        logger.error("\n" + "=" * 60)
        logger.error("❌ 应用启动失败：配置验证不通过")
        logger.error("请检查并修正上述配置错误后重新启动")
        logger.error("=" * 60)

        # 强制退出应用
        sys.exit(1)

    # 验证通过
    logger.info("✅ 配置验证通过，应用启动中...")


# 在模块导入时自动执行验证（可选）
def validate_if_main_app() -> None:
    """只有在主应用启动时才验证，避免在测试等场景下验证"""
    # 检查是否在运行主应用
    import sys

    if (
        len(sys.argv) > 0
        and ("uvicorn" in sys.argv[0] or "server.py" in sys.argv[0])
        and not any("test" in arg.lower() for arg in sys.argv)
    ):
        validate_config_on_startup()


# 导出主要函数
__all__ = [
    "ConfigValidator",
    "ValidationResult",
    "validate_config_on_startup",
    "validate_if_main_app",
]
