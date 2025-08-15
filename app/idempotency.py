"""
事件幂等性管理模块
提供事件去重、重放保护等功能，确保同一事件不被重复处理
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any, Dict
from sqlalchemy.orm import Session
from app.models import SyncEvent, ProcessedEvent, SessionLocal

logger = logging.getLogger(__name__)


class IdempotencyManager:
    """事件幂等性管理器"""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        self._should_close_session = db_session is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session:
            self.db.close()

    def generate_event_id(
        self,
        provider: str,
        event_type: str,
        delivery_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> str:
        """
        生成唯一的事件ID

        Args:
            provider: 事件提供商（github/gitee/notion）
            event_type: 事件类型（issues/pull_request/push等）
            delivery_id: 平台提供的投递ID
            entity_id: 实体ID（issue ID等）
            timestamp: 时间戳

        Returns:
            str: 唯一的事件ID
        """
        # 优先使用平台提供的delivery_id
        if delivery_id:
            return f"{provider}:{delivery_id}"

        # 否则基于内容生成
        components = [provider, event_type]
        if entity_id:
            components.append(entity_id)
        if timestamp:
            components.append(timestamp)

        content = ":".join(components)
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{provider}:{hash_value}"

    def generate_content_hash(self, payload: Dict[str, Any]) -> str:
        """
        生成内容哈希值，用于检测内容变更

        Args:
            payload: 事件载荷数据

        Returns:
            str: 内容哈希值
        """
        # 提取关键字段用于哈希
        key_fields = {}

        if "issue" in payload:
            issue = payload["issue"]
            key_fields.update({
                "title": issue.get("title", ""),
                "body": issue.get("body", ""),
                "state": issue.get("state", ""),
                "updated_at": issue.get("updated_at", "")
            })

        if "pull_request" in payload:
            pr = payload["pull_request"]
            key_fields.update({
                "title": pr.get("title", ""),
                "body": pr.get("body", ""),
                "state": pr.get("state", ""),
                "updated_at": pr.get("updated_at", "")
            })

        # Notion页面内容
        if "properties" in payload:
            key_fields["properties"] = payload["properties"]

        # 生成哈希
        content = json.dumps(key_fields, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def is_duplicate_event(
        self,
        event_id: str,
        content_hash: str,
        max_age_hours: int = 24
    ) -> Tuple[bool, Optional[str]]:
        """
        检查是否为重复事件

        Args:
            event_id: 事件ID
            content_hash: 内容哈希
            max_age_hours: 检查的最大时间范围（小时）

        Returns:
            Tuple[bool, str]: (是否重复, 重复原因)
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

            # 检查是否存在相同的事件ID
            existing_event = self.db.query(SyncEvent).filter(
                SyncEvent.event_id == event_id,
                SyncEvent.created_at >= cutoff_time
            ).first()

            if existing_event:
                if existing_event.status == "processed":
                    return True, f"duplicate_event_id_processed:{existing_event.id}"
                elif existing_event.status == "pending":
                    return True, f"duplicate_event_id_pending:{existing_event.id}"

            # 检查是否存在相同内容哈希的已处理事件
            existing_hash = self.db.query(ProcessedEvent).filter(
                ProcessedEvent.event_hash == content_hash,
                ProcessedEvent.created_at >= cutoff_time
            ).first()

            if existing_hash:
                return True, f"duplicate_content_hash:{existing_hash.id}"

            return False, None

        except Exception as e:
            logger.error("duplicate_check_failed", extra={"error": str(e)})
            # 出错时谨慎处理，允许通过
            return False, None

    def record_event_processing(
        self,
        event_id: str,
        content_hash: str,
        provider: str,
        event_type: str,
        entity_id: str,
        action: str,
        payload: Dict[str, Any]
    ) -> SyncEvent:
        """
        记录事件开始处理

        Args:
            event_id: 事件ID
            content_hash: 内容哈希
            provider: 提供商
            event_type: 事件类型
            entity_id: 实体ID
            action: 操作类型
            payload: 事件载荷

        Returns:
            SyncEvent: 创建的同步事件记录
        """
        try:
            sync_event = SyncEvent(
                event_id=event_id,
                event_hash=content_hash,
                source_platform=provider,
                target_platform="notion" if provider != "notion" else "github",
                entity_type="issue" if "issue" in payload else "page",
                entity_id=entity_id,
                action=action,
                sync_direction=f"{provider}_to_notion" if provider != "notion" else "notion_to_github",
                status="pending"
            )

            self.db.add(sync_event)
            self.db.commit()
            self.db.refresh(sync_event)

            logger.info("event_processing_recorded", extra={
                "event_id": event_id,
                "provider": provider,
                "entity_id": entity_id
            })

            return sync_event

        except Exception as e:
            logger.error("record_event_processing_failed", extra={"error": str(e)})
            self.db.rollback()
            raise

    def mark_event_processed(
        self,
        event_id: str,
        success: bool,
        error_message: Optional[str] = None
    ) -> bool:
        """
        标记事件处理完成

        Args:
            event_id: 事件ID
            success: 是否成功
            error_message: 错误信息（如果失败）

        Returns:
            bool: 是否成功更新
        """
        try:
            sync_event = self.db.query(SyncEvent).filter(
                SyncEvent.event_id == event_id
            ).first()

            if not sync_event:
                logger.warning("sync_event_not_found", extra={"event_id": event_id})
                return False

            sync_event.processed_at = datetime.utcnow()
            sync_event.status = "processed" if success else "failed"

            if success:
                # 记录到已处理事件表
                processed_event = ProcessedEvent(
                    event_hash=sync_event.event_hash,
                    issue_id=sync_event.entity_id,
                    source_platform=sync_event.source_platform
                )
                self.db.add(processed_event)

            self.db.commit()

            logger.info("event_processing_completed", extra={
                "event_id": event_id,
                "success": success,
                "error": error_message
            })

            return True

        except Exception as e:
            logger.error("mark_event_processed_failed", extra={"error": str(e)})
            self.db.rollback()
            return False

    def cleanup_old_events(self, days_to_keep: int = 7) -> int:
        """
        清理过期的事件记录

        Args:
            days_to_keep: 保留的天数

        Returns:
            int: 清理的记录数
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)

            # 清理已处理的旧事件
            deleted_sync = self.db.query(SyncEvent).filter(
                SyncEvent.created_at < cutoff_time,
                SyncEvent.status == "processed"
            ).delete()

            deleted_processed = self.db.query(ProcessedEvent).filter(
                ProcessedEvent.created_at < cutoff_time
            ).delete()

            self.db.commit()

            total_deleted = deleted_sync + deleted_processed
            logger.info("old_events_cleaned", extra={
                "sync_events": deleted_sync,
                "processed_events": deleted_processed,
                "total": total_deleted
            })

            return total_deleted

        except Exception as e:
            logger.error("cleanup_old_events_failed", extra={"error": str(e)})
            self.db.rollback()
            return 0


def with_idempotency(
    provider: str,
    event_type: str,
    delivery_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    max_age_hours: int = 24
):
    """
    幂等性装饰器

    使用示例:
    @with_idempotency("github", "issues", delivery_id="12345")
    async def process_github_issue(payload):
        # 处理逻辑
    """
    def decorator(func):
        async def wrapper(payload, *args, **kwargs):
            with IdempotencyManager() as manager:
                # 生成事件ID和内容哈希
                event_id = manager.generate_event_id(
                    provider, event_type, delivery_id, entity_id
                )
                content_hash = manager.generate_content_hash(payload)

                # 检查是否重复
                is_duplicate, reason = manager.is_duplicate_event(
                    event_id, content_hash, max_age_hours
                )

                if is_duplicate:
                    logger.info("duplicate_event_skipped", extra={
                        "event_id": event_id,
                        "reason": reason
                    })
                    return True, f"duplicate_event_skipped:{reason}"

                # 记录事件开始处理
                action = payload.get("action", "unknown")
                extracted_entity_id = entity_id or str(
                    payload.get("issue", {}).get("number") or
                    payload.get("pull_request", {}).get("number") or
                    payload.get("id", "unknown")
                )

                sync_event = manager.record_event_processing(
                    event_id, content_hash, provider, event_type,
                    extracted_entity_id, action, payload
                )

                try:
                    # 执行实际处理逻辑
                    result = await func(payload, *args, **kwargs)

                    # 标记成功
                    manager.mark_event_processed(event_id, True)
                    return result

                except Exception as e:
                    # 标记失败
                    manager.mark_event_processed(event_id, False, str(e))
                    raise

        return wrapper
    return decorator
