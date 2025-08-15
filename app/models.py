from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DB_URL = os.getenv("DB_URL", "sqlite:///data/sync.db")
engine = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()


class Mapping(Base):
    """映射表：支持Gitee、GitHub和Notion之间的关联"""

    __tablename__ = "mapping"
    id = Column(Integer, primary_key=True)

    # 源数据标识（支持多平台）
    source_platform = Column(String, nullable=False, default="gitee")  # gitee, github
    source_id = Column(String, nullable=False, index=True)  # issue_id
    source_url = Column(String, nullable=True)  # 源链接

    # Notion页面信息
    notion_page_id = Column(String, nullable=False, index=True)
    notion_database_id = Column(String, nullable=True)

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 同步状态
    sync_enabled = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    sync_hash = Column(String, nullable=True)  # 用于检测变更


class SyncEvent(Base):
    """同步事件表：用于防止同步循环"""

    __tablename__ = "sync_event"
    id = Column(Integer, primary_key=True)

    # 事件标识
    event_id = Column(String, nullable=False, unique=True, index=True)
    event_hash = Column(String, nullable=False, index=True)

    # 同步方向和实体
    source_platform = Column(String, nullable=False)  # github, notion, gitee
    target_platform = Column(String, nullable=False)  # github, notion, gitee
    entity_type = Column(String, nullable=False)  # issue, page
    entity_id = Column(String, nullable=False, index=True)

    # 操作信息
    action = Column(String, nullable=False)  # created, updated, closed, etc.
    sync_direction = Column(String, nullable=False)  # source_to_target

    # 时间戳和状态
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, processed, failed

    # 防循环机制
    is_sync_induced = Column(Boolean, default=False, nullable=False)  # 是否由同步引起
    parent_event_id = Column(String, nullable=True)  # 父事件ID


class DeadLetter(Base):
    __tablename__ = "deadletter"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    payload = Column(JSON, nullable=False)
    reason = Column(String, nullable=False)
    retries = Column(Integer, default=0, nullable=False)
    last_error = Column(Text)
    status = Column(String, default="failed", nullable=False)  # failed|pending|replayed

    # 扩展信息
    source_platform = Column(String, nullable=True)  # github, notion, gitee
    entity_id = Column(String, nullable=True)


class ProcessedEvent(Base):
    __tablename__ = "processed_event"
    id = Column(Integer, primary_key=True)
    event_hash = Column(String, nullable=False, unique=True, index=True)
    issue_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 扩展支持多平台
    source_platform = Column(String, default="gitee", nullable=False)


class SyncConfig(Base):
    """同步配置表"""

    __tablename__ = "sync_config"
    id = Column(Integer, primary_key=True)

    # 配置键值
    config_key = Column(String, nullable=False, unique=True, index=True)
    config_value = Column(JSON, nullable=False)

    # 描述和分类
    description = Column(Text, nullable=True)
    category = Column(String, default="general", nullable=False)  # general, github, notion, gitee

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db() -> None:
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine, checkfirst=True)


autodebounce_window = timedelta(minutes=5)


def event_hash_from_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def should_skip_event(db: Session, issue_id: str, event_hash: str, platform: str = "gitee") -> bool:
    """检查是否应跳过事件处理"""
    # 检查是否已处理过相同事件
    ev = db.query(ProcessedEvent).filter_by(event_hash=event_hash).first()
    if ev:
        return True

    # 检查同步事件表中是否存在相同的同步哈希
    sync_ev = db.query(SyncEvent).filter_by(event_hash=event_hash, status="processed").first()
    if sync_ev:
        return True

    # 防抖动：检查同一实体的最近事件
    latest = (
        db.query(ProcessedEvent)
        .filter_by(issue_id=issue_id, source_platform=platform)
        .order_by(ProcessedEvent.created_at.desc())
        .first()
    )
    if latest and (datetime.utcnow() - latest.created_at) < autodebounce_window:
        return False
    return False


def mark_event_processed(db: Session, issue_id: str, event_hash: str, platform: str = "gitee") -> None:
    """标记事件为已处理"""
    rec = ProcessedEvent(event_hash=event_hash, issue_id=issue_id, source_platform=platform)
    db.add(rec)
    db.commit()


def create_sync_event(
    db: Session,
    source_platform: str,
    target_platform: str,
    entity_id: str,
    action: str,
    event_hash: str,
    is_sync_induced: bool = False,
    parent_event_id: Optional[str] = None,
) -> str:
    """创建同步事件记录"""
    import uuid

    event_id = str(uuid.uuid4())

    sync_event = SyncEvent(
        event_id=event_id,
        event_hash=event_hash,
        source_platform=source_platform,
        target_platform=target_platform,
        entity_type="issue",  # 目前主要处理issue
        entity_id=entity_id,
        action=action,
        sync_direction=f"{source_platform}_to_{target_platform}",
        is_sync_induced=is_sync_induced,
        parent_event_id=parent_event_id,
    )

    db.add(sync_event)
    db.commit()
    return event_id


def should_skip_sync_event(
    db: Session, event_hash: str, entity_id: str, source_platform: str, target_platform: str
) -> bool:
    """检查是否应跳过同步事件（防循环）"""
    # 检查最近是否有相同方向的同步事件
    recent_sync = (
        db.query(SyncEvent)
        .filter(
            SyncEvent.entity_id == entity_id,
            SyncEvent.source_platform == target_platform,  # 反向同步
            SyncEvent.target_platform == source_platform,
            SyncEvent.created_at > datetime.utcnow() - timedelta(minutes=10),  # 10分钟窗口
        )
        .first()
    )

    if recent_sync:
        return True

    # 检查相同哈希的事件
    existing = db.query(SyncEvent).filter_by(event_hash=event_hash).first()
    return existing is not None


def mark_sync_event_processed(db: Session, event_id: str) -> None:
    """标记同步事件为已处理"""
    sync_event = db.query(SyncEvent).filter_by(event_id=event_id).first()
    if sync_event:
        sync_event.status = "processed"
        sync_event.processed_at = datetime.utcnow()
        db.commit()


def upsert_mapping(
    db: Session,
    source_platform: str,
    source_id: str,
    notion_page_id: str,
    source_url: Optional[str] = None,
    notion_database_id: Optional[str] = None,
) -> None:
    """更新或插入映射关系"""
    # 查找现有映射
    m = db.query(Mapping).filter_by(source_platform=source_platform, source_id=source_id).first()
    if m:
        if m.notion_page_id != notion_page_id:
            m.notion_page_id = notion_page_id
            m.updated_at = datetime.utcnow()
        if source_url:
            m.source_url = source_url
        if notion_database_id:
            m.notion_database_id = notion_database_id
            db.commit()
        return

    # 检查notion_page_id是否已存在
    existing = db.query(Mapping).filter_by(notion_page_id=notion_page_id).first()
    if existing:
        existing.source_platform = source_platform
        existing.source_id = source_id
        existing.updated_at = datetime.utcnow()
        if source_url:
            existing.source_url = source_url
        if notion_database_id:
            existing.notion_database_id = notion_database_id
        db.commit()
        return

    # 创建新映射
    db.add(
        Mapping(
            source_platform=source_platform,
            source_id=source_id,
            source_url=source_url,
            notion_page_id=notion_page_id,
            notion_database_id=notion_database_id,
        )
    )
    db.commit()


def get_mapping_by_source(db: Session, source_platform: str, source_id: str) -> Optional[Mapping]:
    """根据源平台和ID获取映射"""
    return db.query(Mapping).filter_by(source_platform=source_platform, source_id=source_id).first()


def get_mapping_by_notion_page(db: Session, notion_page_id: str) -> Optional[Mapping]:
    """根据Notion页面ID获取映射"""
    return db.query(Mapping).filter_by(notion_page_id=notion_page_id).first()


def deadletter_enqueue(
    db: Session,
    payload: dict,
    reason: str,
    last_error: Optional[str] = None,
    source_platform: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> None:
    dl = DeadLetter(
        payload=payload,
        reason=reason,
        last_error=last_error,
        status="failed",
        retries=0,
        source_platform=source_platform,
        entity_id=entity_id,
    )
    db.add(dl)
    db.commit()


def deadletter_list(db: Session) -> List[DeadLetter]:
    return db.query(DeadLetter).filter(DeadLetter.status == "failed").all()


def deadletter_count(db: Session) -> int:
    return db.query(DeadLetter).filter(DeadLetter.status == "failed").count()


def deadletter_mark_replayed(db: Session, dl_id: int) -> None:
    rec = db.query(DeadLetter).filter_by(id=dl_id).first()
    if rec:
        rec.status = "replayed"
        db.commit()


def deadletter_increment_retry(db: Session, dl_id: int, last_error: Optional[str] = None) -> None:
    rec = db.query(DeadLetter).filter_by(id=dl_id).first()
    if rec:
        rec.retries += 1
        if last_error:
            rec.last_error = last_error
        db.commit()


# 配置管理函数
def get_config(db: Session, key: str) -> Optional[dict]:
    """获取配置"""
    config = db.query(SyncConfig).filter_by(config_key=key).first()
    return config.config_value if config else None


def set_config(
    db: Session, key: str, value: dict, description: Optional[str] = None, category: str = "general"
) -> None:
    """设置配置"""
    config = db.query(SyncConfig).filter_by(config_key=key).first()
    if config:
        config.config_value = value
        config.updated_at = datetime.utcnow()
        if description:
            config.description = description
        config.category = category
    else:
        config = SyncConfig(config_key=key, config_value=value, description=description, category=category)
        db.add(config)
        db.commit()
