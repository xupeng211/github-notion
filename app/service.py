from __future__ import annotations
import os
import time
import json
import hmac
import hashlib
import logging
from typing import Tuple, Dict, Any
from contextlib import contextmanager
from threading import Lock
from collections import deque
import math

import requests
from sqlalchemy.orm import Session
from prometheus_client import Counter, Histogram, Gauge
from apscheduler.schedulers.background import BackgroundScheduler

from app.models import (
    SessionLocal, upsert_mapping, should_skip_event, mark_event_processed,
    event_hash_from_bytes, deadletter_enqueue, deadletter_count
)

# Metrics (allow disabling in tests to avoid duplicate registration)
DISABLE_METRICS = os.getenv("DISABLE_METRICS", "").lower() in ("1", "true", "yes")

if DISABLE_METRICS:
    class _Noop:
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
    EVENTS_TOTAL = _Noop()
    RETRIES_TOTAL = _Noop()
    PROCESS_LATENCY = _Noop()
    DEADLETTER_SIZE = _Noop()
    PROCESS_P95_MS = _Noop()
    DEADLETTER_REPLAY_TOTAL = _Noop()
else:
    EVENTS_TOTAL = Counter("events_total", "Total events processed", ["result"])  # result: success|skip|fail
    RETRIES_TOTAL = Counter("retries_total", "Total retry attempts")
    PROCESS_LATENCY = Histogram("process_latency_seconds", "Processing latency seconds")
    DEADLETTER_SIZE = Gauge("deadletter_size", "Current deadletter size")
    PROCESS_P95_MS = Gauge("process_p95_ms", "Approx p95 of processing latency in ms (sliding window)")
    DEADLETTER_REPLAY_TOTAL = Counter("deadletter_replay_total", "Total deadletters replayed")

logger = logging.getLogger("service")

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
DISABLE_NOTION = os.getenv("DISABLE_NOTION", "").lower() not in ("", "0", "false")
GITEE_TOKEN = os.getenv("GITEE_TOKEN", "")

_issue_locks: Dict[str, Lock] = {}
_global_lock = Lock()
_durations = deque(maxlen=200)


def _get_issue_lock(issue_id: str) -> Lock:
    with _global_lock:
        if issue_id not in _issue_locks:
            _issue_locks[issue_id] = Lock()
        return _issue_locks[issue_id]


@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def verify_gitee_signature(secret: str, payload: bytes, signature: str) -> bool:
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def exponential_backoff_request(method: str, url: str, headers: Dict[str, str] = None, json_data: Dict[str, Any] = None,
                                max_retries: int = 5, base_delay: float = 0.5) -> Tuple[bool, Dict[str, Any]]:
    headers = headers or {}
    for attempt in range(max_retries + 1):
        try:
            resp = requests.request(method, url, headers=headers, json=json_data, timeout=10)
            if resp.status_code in (429,) or 500 <= resp.status_code < 600:
                if attempt < max_retries:
                    RETRIES_TOTAL.inc()
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                else:
                    return False, {"status": resp.status_code, "text": resp.text}
            resp.raise_for_status()
            if resp.text:
                return True, resp.json()
            return True, {}
        except requests.RequestException as e:
            if attempt < max_retries:
                RETRIES_TOTAL.inc()
                time.sleep(base_delay * (2 ** attempt))
                continue
            return False, {"error": str(e)}


def notion_upsert_page(issue: Dict[str, Any]) -> Tuple[bool, str]:
    # Optional bypass for local testing without external dependency
    if DISABLE_NOTION:
        title = issue.get("title", "")
        # Return a synthetic page id to allow downstream mapping/upsert
        return True, f"DRYRUN_PAGE_{title or 'untitled'}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    title = issue.get("title", "")
    q_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    ok, data = exponential_backoff_request("POST", q_url, headers, {"filter": {"property": "Task", "title": {"equals": title}}})
    if not ok:
        return False, json.dumps(data)
    results = data.get("results", [])
    if results:
        page_id = results[0]["id"]
        p_url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"properties": {"Task": {"title": [{"text": {"content": title}}]}}}
        ok2, _ = exponential_backoff_request("PATCH", p_url, headers, payload)
        if ok2:
            return True, page_id
        return False, page_id
    c_url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Task": {"title": [{"text": {"content": title}}]},
            "Issue ID": {"rich_text": [{"text": {"content": str(issue.get("number"))}}]},
        }
    }
    ok3, res = exponential_backoff_request("POST", c_url, headers, payload)
    if ok3:
        return True, res.get("id", "")
    return False, json.dumps(res)


def process_gitee_event(body_bytes: bytes, secret: str, signature: str, event_type: str) -> Tuple[bool, str]:
    start = time.time()
    try:
        if not verify_gitee_signature(secret, body_bytes, signature):
            EVENTS_TOTAL.labels("fail").inc()
            return False, "invalid_signature"
        payload = json.loads(body_bytes.decode("utf-8"))
        issue = payload.get("issue") or {}
        issue_id = str(issue.get("number") or issue.get("id") or "")
        event_hash = event_hash_from_bytes(body_bytes)
        if not issue_id:
            EVENTS_TOTAL.labels("fail").inc()
            return False, "missing_issue_id"
        lock = _get_issue_lock(issue_id)
        with lock:
            with session_scope() as db:
                if should_skip_event(db, issue_id, event_hash):
                    EVENTS_TOTAL.labels("skip").inc()
                    return True, "duplicate"
                ok, page_or_err = notion_upsert_page(issue)
                if not ok:
                    deadletter_enqueue(db, payload, reason="notion_error", last_error=str(page_or_err))
                    DEADLETTER_SIZE.set(deadletter_count(db))
                    EVENTS_TOTAL.labels("fail").inc()
                    return False, "notion_error"
                page_id = page_or_err
                upsert_mapping(db, issue_id, page_id)
                mark_event_processed(db, issue_id, event_hash)
        EVENTS_TOTAL.labels("success").inc()
        return True, "ok"
    finally:
        dur = (time.time() - start)
        PROCESS_LATENCY.observe(dur)
        # update p95 gauge using sliding window
        _durations.append(dur * 1000.0)
        arr = sorted(_durations)
        if arr:
            k = max(0, int(math.ceil(0.95 * len(arr)) - 1))

            PROCESS_P95_MS.set(arr[k])

# Deadletter replay logic

def replay_deadletters_once(secret_token: str) -> int:
    """Replay failed deadletters once. Returns count processed successfully."""
    token_env = os.getenv("DEADLETTER_REPLAY_TOKEN", "")
    if token_env and secret_token and token_env != secret_token:
        return 0
    from app.models import SessionLocal, deadletter_list, deadletter_mark_replayed
    cnt = 0
    with SessionLocal() as s:
        items = deadletter_list(s)
        for it in items:
            payload = json.dumps(it.payload).encode()
            sig = hmac.new(os.getenv("GITEE_WEBHOOK_SECRET", "").encode(), payload, hashlib.sha256).hexdigest() if os.getenv("GITEE_WEBHOOK_SECRET") else ""
            ok, _ = process_gitee_event(payload, os.getenv("GITEE_WEBHOOK_SECRET", ""), sig, "replay")
            if ok:
                deadletter_mark_replayed(s, it.id)
                DEADLETTER_REPLAY_TOTAL.inc()
                cnt += 1
    return cnt


def start_deadletter_scheduler() -> None:
    """Start background scheduler based on env interval."""
    try:
        interval = int(os.getenv("DEADLETTER_REPLAY_INTERVAL_MINUTES", "10"))
    except Exception:
        interval = 10
    if interval <= 0:
        return
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        lambda: replay_deadletters_once(os.getenv("DEADLETTER_REPLAY_TOKEN", "")),
        "interval",
        minutes=interval,
        id="deadletter_replay",
        replace_existing=True,
    )
    scheduler.start()

