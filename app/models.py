from __future__ import annotations
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DB_URL = os.getenv("DB_URL", "sqlite:///data/sync.db")
engine = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()


class Mapping(Base):
    __tablename__ = "mapping"
    id = Column(Integer, primary_key=True)
    issue_id = Column(String, nullable=False, unique=True, index=True)
    notion_page_id = Column(String, nullable=False, unique=True, index=True)


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


class ProcessedEvent(Base):
    __tablename__ = "processed_event"
    id = Column(Integer, primary_key=True)
    event_hash = Column(String, nullable=False, unique=True, index=True)
    issue_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def init_db() -> None:
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)


autodebounce_window = timedelta(minutes=5)


def event_hash_from_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def should_skip_event(db: Session, issue_id: str, event_hash: str) -> bool:
    ev = db.query(ProcessedEvent).filter_by(event_hash=event_hash).first()
    if ev:
        # already processed
        return True
    # Optionally: debounce by time per issue (ignore rapid duplicates)
    latest = (
        db.query(ProcessedEvent)
        .filter_by(issue_id=issue_id)
        .order_by(ProcessedEvent.created_at.desc())
        .first()
    )
    if latest and (datetime.utcnow() - latest.created_at) < autodebounce_window:
        return False
    return False


def mark_event_processed(db: Session, issue_id: str, event_hash: str) -> None:
    rec = ProcessedEvent(event_hash=event_hash, issue_id=issue_id)
    db.add(rec)
    db.commit()


def upsert_mapping(db: Session, issue_id: str, notion_page_id: str) -> None:
    m = db.query(Mapping).filter_by(issue_id=issue_id).first()
    if m:
        if m.notion_page_id != notion_page_id:
            m.notion_page_id = notion_page_id
            db.commit()
        return
    existing = db.query(Mapping).filter_by(notion_page_id=notion_page_id).first()
    if existing:
        existing.issue_id = issue_id
        db.commit()
        return
    db.add(Mapping(issue_id=issue_id, notion_page_id=notion_page_id))
    db.commit()


def deadletter_enqueue(db: Session, payload: dict, reason: str, last_error: Optional[str] = None) -> None:
    dl = DeadLetter(payload=payload, reason=reason, last_error=last_error, status="failed", retries=0)
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

