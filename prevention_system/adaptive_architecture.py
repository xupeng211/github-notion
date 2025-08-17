"""
自适应架构模式
根据环境能力自动调整功能实现
"""

import functools
import logging
from typing import Callable, Dict, Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """能力注册表"""

    def __init__(self):
        self._capabilities: Dict[str, bool] = {}
        self._detectors: Dict[str, Callable] = {}
        self._fallbacks: Dict[str, Callable] = {}

    def register_capability(self, name: str, detector: Callable[[Session], bool]):
        """注册能力检测器"""
        self._detectors[name] = detector

    def register_fallback(self, capability: str, fallback_func: Callable):
        """注册回退函数"""
        self._fallbacks[capability] = fallback_func

    def detect_capability(self, name: str, db: Session) -> bool:
        """检测特定能力"""
        if name not in self._capabilities:
            if name in self._detectors:
                try:
                    self._capabilities[name] = self._detectors[name](db)
                    logger.info(f"Capability '{name}' detected: {self._capabilities[name]}")
                except Exception as e:
                    logger.warning(f"Failed to detect capability '{name}': {e}")
                    self._capabilities[name] = False
            else:
                self._capabilities[name] = False

        return self._capabilities[name]

    def get_fallback(self, capability: str) -> Optional[Callable]:
        """获取回退函数"""
        return self._fallbacks.get(capability)


# 全局能力注册表
capability_registry = CapabilityRegistry()


def adaptive_function(capability: str, fallback_capability: Optional[str] = None):
    """自适应函数装饰器"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 假设第一个参数是数据库会话
            db = None
            for arg in args:
                if isinstance(arg, Session):
                    db = arg
                    break

            if db is None:
                # 如果没有找到数据库会话，直接执行原函数
                return func(*args, **kwargs)

            # 检测能力
            has_capability = capability_registry.detect_capability(capability, db)

            if has_capability:
                # 有能力，执行原函数
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Function {func.__name__} failed despite capability: {e}")
                    # 尝试回退
                    if fallback_capability:
                        fallback_func = capability_registry.get_fallback(fallback_capability)
                        if fallback_func:
                            return fallback_func(*args, **kwargs)
                    raise
            else:
                # 没有能力，使用回退
                fallback_func = capability_registry.get_fallback(capability)
                if fallback_func:
                    logger.info(f"Using fallback for {func.__name__} due to missing capability: {capability}")
                    return fallback_func(*args, **kwargs)
                else:
                    raise RuntimeError(f"No fallback available for capability: {capability}")

        return wrapper

    return decorator


# 预定义的能力检测器
def detect_source_platform_column(db: Session) -> bool:
    """检测是否有source_platform字段"""
    try:
        inspector = inspect(db.bind)
        if "processed_event" not in inspector.get_table_names():
            return False
        columns = [col["name"] for col in inspector.get_columns("processed_event")]
        return "source_platform" in columns
    except Exception:
        return False


def detect_alembic_version_table(db: Session) -> bool:
    """检测是否有alembic版本表"""
    try:
        inspector = inspect(db.bind)
        return "alembic_version" in inspector.get_table_names()
    except Exception:
        return False


def detect_redis_capability(db: Session) -> bool:
    """检测Redis能力"""
    import os

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return False

    try:
        import redis

        r = redis.from_url(redis_url)
        r.ping()
        return True
    except Exception:
        return False


# 注册能力检测器
capability_registry.register_capability("source_platform_column", detect_source_platform_column)
capability_registry.register_capability("alembic_version_table", detect_alembic_version_table)
capability_registry.register_capability("redis_available", detect_redis_capability)


# 回退函数示例
def should_skip_event_fallback(db: Session, issue_id: str, platform: str = None) -> bool:
    """should_skip_event的回退实现"""
    from app.models import ProcessedEvent

    # 不使用source_platform字段的查询
    latest = db.query(ProcessedEvent).filter_by(issue_id=issue_id).order_by(ProcessedEvent.created_at.desc()).first()

    return latest is not None


def mark_event_processed_fallback(db: Session, issue_id: str, content_hash: str, platform: str = None):
    """mark_event_processed的回退实现"""
    from app.models import ProcessedEvent

    # 不使用source_platform字段的插入
    processed = ProcessedEvent(
        issue_id=issue_id,
        content_hash=content_hash,
        # 不设置source_platform字段
    )
    db.add(processed)
    db.commit()


# 注册回退函数
capability_registry.register_fallback("source_platform_column", should_skip_event_fallback)


class AdaptiveQueryBuilder:
    """自适应查询构建器"""

    def __init__(self, db: Session):
        self.db = db
        self.capabilities = {}
        self._detect_capabilities()

    def _detect_capabilities(self):
        """检测数据库能力"""
        self.capabilities = {
            "source_platform_column": capability_registry.detect_capability("source_platform_column", self.db),
            "alembic_version_table": capability_registry.detect_capability("alembic_version_table", self.db),
        }

    def build_processed_event_query(self, issue_id: str, platform: Optional[str] = None):
        """构建ProcessedEvent查询"""
        from app.models import ProcessedEvent

        query = self.db.query(ProcessedEvent).filter_by(issue_id=issue_id)

        if self.capabilities["source_platform_column"] and platform:
            query = query.filter_by(source_platform=platform)

        return query.order_by(ProcessedEvent.created_at.desc())

    def build_processed_event_insert(self, issue_id: str, content_hash: str, platform: Optional[str] = None):
        """构建ProcessedEvent插入"""
        from app.models import ProcessedEvent

        data = {
            "issue_id": issue_id,
            "content_hash": content_hash,
        }

        if self.capabilities["source_platform_column"] and platform:
            data["source_platform"] = platform

        return ProcessedEvent(**data)


# 使用示例装饰器的函数
@adaptive_function("source_platform_column")
def should_skip_event_adaptive(db: Session, issue_id: str, platform: str) -> bool:
    """自适应的should_skip_event实现"""
    builder = AdaptiveQueryBuilder(db)
    latest = builder.build_processed_event_query(issue_id, platform).first()
    return latest is not None


@adaptive_function("source_platform_column")
def mark_event_processed_adaptive(db: Session, issue_id: str, content_hash: str, platform: str):
    """自适应的mark_event_processed实现"""
    builder = AdaptiveQueryBuilder(db)
    processed = builder.build_processed_event_insert(issue_id, content_hash, platform)
    db.add(processed)
    db.commit()


class EnvironmentAwareService:
    """环境感知服务基类"""

    def __init__(self, db: Session):
        self.db = db
        self.capabilities = self._detect_capabilities()

    def _detect_capabilities(self) -> Dict[str, bool]:
        """检测环境能力"""
        return {
            "source_platform_column": capability_registry.detect_capability("source_platform_column", self.db),
            "redis_available": capability_registry.detect_capability("redis_available", self.db),
            "alembic_version_table": capability_registry.detect_capability("alembic_version_table", self.db),
        }

    def get_capability(self, name: str) -> bool:
        """获取能力状态"""
        return self.capabilities.get(name, False)

    def require_capability(self, name: str) -> bool:
        """要求特定能力，如果没有则抛出异常"""
        if not self.get_capability(name):
            raise RuntimeError(f"Required capability '{name}' not available in current environment")
        return True


# 环境感知的服务实现示例
class AdaptiveEventProcessor(EnvironmentAwareService):
    """自适应事件处理器"""

    def process_event(self, issue_id: str, content_hash: str, platform: str) -> bool:
        """处理事件"""
        # 检查是否应该跳过
        if self.should_skip_event(issue_id, platform):
            return False

        # 标记为已处理
        self.mark_event_processed(issue_id, content_hash, platform)
        return True

    def should_skip_event(self, issue_id: str, platform: str) -> bool:
        """检查是否应该跳过事件"""
        builder = AdaptiveQueryBuilder(self.db)

        if self.get_capability("source_platform_column"):
            # 使用完整查询
            latest = builder.build_processed_event_query(issue_id, platform).first()
        else:
            # 使用基础查询
            latest = builder.build_processed_event_query(issue_id).first()

        return latest is not None

    def mark_event_processed(self, issue_id: str, content_hash: str, platform: str):
        """标记事件为已处理"""
        builder = AdaptiveQueryBuilder(self.db)
        processed = builder.build_processed_event_insert(issue_id, content_hash, platform)
        self.db.add(processed)
        self.db.commit()
