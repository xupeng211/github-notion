"""
增强版幂等性管理器
改进事件去重逻辑，提供更准确的重复检测和更好的性能
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.idempotency import IdempotencyManager
from app.models import ProcessedEvent, SyncEvent
from app.retry_manager import RETRY_CONFIGS, RetryManager

logger = logging.getLogger(__name__)


class EnhancedIdempotencyManager(IdempotencyManager):
    """增强版幂等性管理器"""

    def __init__(self, db_session: Optional[Session] = None):
        super().__init__(db_session)
        self._cache = {}  # 内存缓存，用于快速重复检测
        self._cache_ttl = 300  # 缓存TTL 5分钟
        self.retry_manager = RetryManager(RETRY_CONFIGS["database_operations"], self.db)

    def generate_enhanced_event_id(self, provider: str, delivery_id: str, source: str = "webhook") -> str:
        """
        生成增强的事件ID
        基于 delivery_id + source 的哈希键确保唯一性

        Args:
            provider: 事件提供商（github/gitee/notion）
            delivery_id: 平台提供的投递ID
            source: 事件来源（webhook/api/manual）

        Returns:
            唯一的事件ID
        """
        # 创建复合键，确保在不同来源之间的唯一性
        composite_key = f"{provider}:{source}:{delivery_id}"

        # 使用SHA256生成稳定的哈希
        hash_object = hashlib.sha256(composite_key.encode("utf-8"))
        event_hash = hash_object.hexdigest()[:16]  # 取前16位以减少长度

        return f"{provider}:{event_hash}"

    def generate_content_fingerprint(self, payload: Dict[str, Any]) -> str:
        """
        生成内容指纹
        使用更智能的算法，忽略时间戳等不重要的字段差异

        Args:
            payload: 事件载荷

        Returns:
            内容指纹
        """
        # 提取关键字段用于指纹生成
        key_fields = self._extract_key_fields(payload)

        # 标准化并排序
        normalized = json.dumps(key_fields, sort_keys=True, ensure_ascii=False)

        # 生成SHA256哈希
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _extract_key_fields(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取用于指纹生成的关键字段
        忽略时间戳、临时ID等会变化但不影响业务逻辑的字段
        """
        key_fields = {}

        # 通用字段
        if "action" in payload:
            key_fields["action"] = payload["action"]

        # Issue相关字段
        if "issue" in payload:
            issue = payload["issue"]
            key_fields["issue"] = {
                "number": issue.get("number"),
                "title": issue.get("title", "").strip(),
                "body": issue.get("body", "").strip(),
                "state": issue.get("state"),
                "labels": sorted([label.get("name", "") for label in issue.get("labels", [])]),
            }

            # 用户信息（关键部分）
            if "user" in issue:
                key_fields["issue"]["user"] = {
                    "login": issue["user"].get("login"),
                    "type": issue["user"].get("type"),
                }

        # Pull Request相关字段
        if "pull_request" in payload:
            pr = payload["pull_request"]
            key_fields["pull_request"] = {
                "number": pr.get("number"),
                "title": pr.get("title", "").strip(),
                "body": pr.get("body", "").strip(),
                "state": pr.get("state"),
                "base": pr.get("base", {}).get("ref"),
                "head": pr.get("head", {}).get("ref"),
            }

        # Repository信息
        if "repository" in payload:
            repo = payload["repository"]
            key_fields["repository"] = {
                "full_name": repo.get("full_name"),
                "name": repo.get("name"),
            }

        return key_fields

    def is_duplicate_event_enhanced(
        self,
        event_id: str,
        content_fingerprint: str,
        delivery_id: str,
        max_age_hours: int = 24,
    ) -> Tuple[bool, str]:
        """
        增强的重复事件检测
        使用多层检测机制：内存缓存 -> 数据库检查

        Args:
            event_id: 事件ID
            content_fingerprint: 内容指纹
            delivery_id: 投递ID
            max_age_hours: 检查时间范围（小时）

        Returns:
            (是否重复, 重复原因)
        """
        # 1. 内存缓存检查（最快）
        cache_key = f"{event_id}:{content_fingerprint}"
        current_time = datetime.utcnow().timestamp()

        if cache_key in self._cache:
            cached_time, cached_reason = self._cache[cache_key]
            if current_time - cached_time < self._cache_ttl:
                logger.debug(
                    "duplicate_detected_cache",
                    extra={"event_id": event_id, "reason": cached_reason},
                )
                return True, f"cache:{cached_reason}"

        # 2. 数据库检查
        try:
            is_duplicate, reason = self._check_database_duplicate(
                event_id, content_fingerprint, delivery_id, max_age_hours
            )

            # 更新缓存
            if is_duplicate:
                self._cache[cache_key] = (current_time, reason)
                # 清理过期缓存
                self._cleanup_cache()

            return is_duplicate, reason

        except Exception as e:
            logger.error("duplicate_check_failed", extra={"event_id": event_id, "error": str(e)})
            # 发生错误时假设不重复，允许处理继续
            return False, f"check_failed:{str(e)}"

    def _check_database_duplicate(
        self,
        event_id: str,
        content_fingerprint: str,
        delivery_id: str,
        max_age_hours: int,
    ) -> Tuple[bool, str]:
        """数据库重复检查"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        # 检查事件ID重复
        existing_event = (
            self.db.query(SyncEvent).filter(SyncEvent.event_id == event_id, SyncEvent.created_at >= cutoff_time).first()
        )

        if existing_event:
            if existing_event.processed:
                return True, f"event_id_processed:{existing_event.id}"
            else:
                return True, f"event_id_pending:{existing_event.id}"

        # 检查内容指纹重复
        existing_hash = (
            self.db.query(ProcessedEvent)
            .filter(
                ProcessedEvent.event_hash == content_fingerprint,
                ProcessedEvent.created_at >= cutoff_time,
            )
            .first()
        )

        if existing_hash:
            return True, f"content_fingerprint:{existing_hash.id}"

        # 检查投递ID重复（基于delivery_id的幂等性）
        if delivery_id:
            # 在SyncEvent表中查找相同的delivery_id
            # 注意：这需要在SyncEvent模型中添加delivery_id字段
            existing_delivery = (
                self.db.query(SyncEvent)
                .filter(
                    SyncEvent.source_id == delivery_id,
                    SyncEvent.created_at >= cutoff_time,
                )  # 临时使用source_id字段
                .first()
            )

            if existing_delivery and existing_delivery.event_id != event_id:
                return True, f"delivery_id_duplicate:{existing_delivery.id}"

        return False, "not_duplicate"

    def _cleanup_cache(self):
        """清理过期的缓存条目"""
        current_time = datetime.utcnow().timestamp()
        expired_keys = []

        for key, (cached_time, _) in self._cache.items():
            if current_time - cached_time >= self._cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug("cache_cleanup", extra={"expired_count": len(expired_keys)})

    def record_event_processing_enhanced(
        self,
        event_id: str,
        content_fingerprint: str,
        provider: str,
        event_type: str,
        delivery_id: str,
        extracted_entity_id: str,
        action: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        增强的事件处理记录
        包含更详细的上下文信息和错误处理

        Returns:
            是否记录成功
        """
        try:
            # 记录到SyncEvent表
            sync_event = SyncEvent(
                event_id=event_id,
                provider=provider,
                event_type=event_type,
                source_id=extracted_entity_id,
                action=action,
                payload=json.dumps(payload, ensure_ascii=False),
                processed=False,
                created_at=datetime.utcnow(),
            )

            self.db.add(sync_event)

            # 记录到ProcessedEvent表（用于内容指纹去重）
            processed_event = ProcessedEvent(
                event_hash=content_fingerprint,
                provider=provider,
                event_type=event_type,
                created_at=datetime.utcnow(),
            )

            self.db.add(processed_event)
            self.db.commit()

            logger.info(
                "enhanced_event_processing_recorded",
                extra={
                    "event_id": event_id,
                    "provider": provider,
                    "entity_id": extracted_entity_id,
                    "delivery_id": delivery_id,
                    "content_fingerprint": content_fingerprint[:16],  # 只记录前16位
                },
            )

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(
                "event_recording_failed",
                extra={
                    "event_id": event_id,
                    "error": str(e),
                    "provider": provider,
                    "entity_id": extracted_entity_id,
                },
            )
            return False

    def get_idempotency_stats(self) -> Dict[str, Any]:
        """
        获取幂等性统计信息

        Returns:
            统计信息字典
        """
        try:
            # 基础统计
            total_events = self.db.query(SyncEvent).count()
            processed_events = self.db.query(SyncEvent).filter_by(processed=True).count()
            pending_events = total_events - processed_events

            # 最近24小时的统计
            last_24h = datetime.utcnow() - timedelta(hours=24)
            recent_events = self.db.query(SyncEvent).filter(SyncEvent.created_at >= last_24h).count()

            # 按提供商统计
            provider_stats = {}
            for provider in ["github", "gitee", "notion"]:
                count = self.db.query(SyncEvent).filter_by(provider=provider).count()
                provider_stats[provider] = count

            # 缓存统计
            cache_stats = {"cache_size": len(self._cache), "cache_ttl": self._cache_ttl}

            return {
                "total_events": total_events,
                "processed_events": processed_events,
                "pending_events": pending_events,
                "recent_24h_events": recent_events,
                "by_provider": provider_stats,
                "cache": cache_stats,
            }

        except Exception as e:
            logger.error("idempotency_stats_failed", extra={"error": str(e)})
            return {"error": str(e)}


# 使用增强幂等性的装饰器
def with_enhanced_idempotency(provider: str, event_type: str, delivery_id_key: str = "delivery_id"):
    """
    增强版幂等性装饰器

    Args:
        provider: 事件提供商
        event_type: 事件类型
        delivery_id_key: payload中delivery_id的键名
    """

    def decorator(func):
        async def wrapper(payload: Dict[str, Any], *args, **kwargs):
            # 从payload中提取delivery_id
            delivery_id = None
            if isinstance(payload, dict):
                # 尝试多种可能的键名
                for key in [delivery_id_key, "delivery_id", "id", "request_id"]:
                    if key in payload:
                        delivery_id = str(payload[key])
                        break

            if not delivery_id:
                logger.warning(
                    "no_delivery_id_found",
                    extra={"provider": provider, "event_type": event_type},
                )
                # 没有delivery_id时生成一个基于内容的临时ID
                delivery_id = hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

            manager = EnhancedIdempotencyManager()

            try:
                # 生成事件ID和内容指纹
                event_id = manager.generate_enhanced_event_id(provider, delivery_id)
                content_fingerprint = manager.generate_content_fingerprint(payload)

                # 检查重复
                is_duplicate, reason = manager.is_duplicate_event_enhanced(event_id, content_fingerprint, delivery_id)

                if is_duplicate:
                    logger.info(
                        "enhanced_duplicate_event_skipped",
                        extra={
                            "event_id": event_id,
                            "reason": reason,
                            "delivery_id": delivery_id,
                        },
                    )
                    return {"status": "duplicate", "reason": reason}

                # 记录事件处理
                extracted_entity_id = str(payload.get("issue", {}).get("number", ""))
                action = payload.get("action", "unknown")

                success = manager.record_event_processing_enhanced(
                    event_id,
                    content_fingerprint,
                    provider,
                    event_type,
                    delivery_id,
                    extracted_entity_id,
                    action,
                    payload,
                )

                if not success:
                    logger.error("failed_to_record_event")
                    return {"status": "error", "message": "Failed to record event"}

                # 执行实际的处理函数
                result = await func(payload, *args, **kwargs)

                # 标记事件处理完成
                manager.mark_event_processed(event_id, True)

                return result

            except Exception as e:
                # 标记事件处理失败
                if "event_id" in locals():
                    manager.mark_event_processed(event_id, False, str(e))

                logger.error(
                    "enhanced_idempotency_error",
                    extra={
                        "provider": provider,
                        "event_type": event_type,
                        "error": str(e),
                        "delivery_id": delivery_id,
                    },
                )
                raise

            finally:
                manager.__exit__(None, None, None)

        return wrapper

    return decorator


# 导出主要类和函数
__all__ = ["EnhancedIdempotencyManager", "with_enhanced_idempotency"]
