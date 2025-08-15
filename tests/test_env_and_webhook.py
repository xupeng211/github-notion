import hashlib
import hmac
import json
import os

from fastapi.testclient import TestClient

os.environ.setdefault("DB_URL", "sqlite:///data/test.db")

from app.models import init_db
from app.server import app  # noqa

client = TestClient(app)
init_db()


def sign(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    response_data = r.json()
    # 健康状态可能是 healthy 或 degraded（如果没有配置 Notion token）
    assert response_data.get("status") in ["healthy", "degraded"]
    # 确保包含必要的检查信息
    assert "checks" in response_data
    assert "database" in response_data["checks"]


def test_signature_validation():
    secret = "s"
    payload = json.dumps({"issue": {"number": 1, "title": "t"}}).encode()
    sig = sign(secret, payload)
    r = client.post(
        "/gitee_webhook",
        data=payload,
        headers={"X-Gitee-Token": sig, "Content-Type": "application/json"},
    )
    # service expects env GITEE_WEBHOOK_SECRET; here it's empty, so invalid
    assert r.status_code == 403


def test_duplicate_idempotency(monkeypatch):
    os.environ["GITEE_WEBHOOK_SECRET"] = "k"
    os.environ["NOTION_TOKEN"] = "t"
    os.environ["NOTION_DATABASE_ID"] = "db"

    # Stub network calls
    from app import service

    def ok_upsert(issue):
        return True, "page_1"

    monkeypatch.setattr(service, "notion_upsert_page", ok_upsert)

    payload = json.dumps({"issue": {"number": 2, "title": "X"}}).encode()
    sig = sign("k", payload)
    r1 = client.post(
        "/gitee_webhook",
        data=payload,
        headers={"X-Gitee-Token": sig, "Content-Type": "application/json"},
    )
    r2 = client.post(
        "/gitee_webhook",
        data=payload,
        headers={"X-Gitee-Token": sig, "Content-Type": "application/json"},
    )
    assert r1.status_code == 200
    assert r2.status_code in (200, 201)


def test_retry_deadletter(monkeypatch):
    os.environ["GITEE_WEBHOOK_SECRET"] = "k"
    os.environ["NOTION_TOKEN"] = "t"
    os.environ["NOTION_DATABASE_ID"] = "db"

    from app import service

    def fail_upsert(issue):
        return False, "err"

    monkeypatch.setattr(service, "notion_upsert_page", fail_upsert)
    payload = json.dumps({"issue": {"number": 3, "title": "Y"}}).encode()
    sig = sign("k", payload)
    r = client.post(
        "/gitee_webhook",
        data=payload,
        headers={"X-Gitee-Token": sig, "Content-Type": "application/json"},
    )
    assert r.status_code == 400


def test_conflict_strategy(monkeypatch):
    os.environ["GITEE_WEBHOOK_SECRET"] = "k"
    os.environ["NOTION_TOKEN"] = "t"
    os.environ["NOTION_DATABASE_ID"] = "db"

    from app import service

    seq = [
        (True, "page_a"),
        (True, "page_b"),
    ]

    def upsert_seq(issue):
        return seq.pop(0)

    monkeypatch.setattr(service, "notion_upsert_page", upsert_seq)

    payload1 = json.dumps({"issue": {"number": 4, "title": "Z"}}).encode()
    sig1 = sign("k", payload1)
    r1 = client.post(
        "/gitee_webhook",
        data=payload1,
        headers={"X-Gitee-Token": sig1, "Content-Type": "application/json"},
    )
    assert r1.status_code == 200

    payload2 = json.dumps({"issue": {"number": 4, "title": "Z2"}}).encode()
    sig2 = sign("k", payload2)
    r2 = client.post(
        "/gitee_webhook",
        data=payload2,
        headers={"X-Gitee-Token": sig2, "Content-Type": "application/json"},
    )
    assert r2.status_code == 200


def test_replay_script_imports():
    # Ensure replay script imports without error
    import importlib

    importlib.import_module("scripts.replay_deadletter")
