import importlib
import json
import sys


def test_verify_gitee_signature_valid_invalid(monkeypatch):
    from app import service

    secret = "s"
    body = b"{}"

    ok = service.verify_gitee_signature(secret, body, service.hmac.new(secret.encode(), body, service.hashlib.sha256).hexdigest())
    assert ok is True

    ok2 = service.verify_gitee_signature(secret, body, "bad")
    assert ok2 is False


def test_idempotency_and_mapping(tmp_path, monkeypatch):
    # Isolate DB and disable external dependency
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("DISABLE_NOTION", "1")
    monkeypatch.setenv("GITEE_WEBHOOK_SECRET", "s")

    # Reload modules to pick up env
    import prometheus_client
    prometheus_client.REGISTRY = prometheus_client.CollectorRegistry()
    # Ensure fresh imports under new env/registry
    for mod in ["app.service", "app.models"]:
        if mod in sys.modules:
            del sys.modules[mod]
    models = importlib.import_module("app.models")
    service = importlib.import_module("app.service")

    models.init_db()

    payload = {"issue": {"id": 999, "number": 999, "title": "ci-demo"}}
    body = json.dumps(payload).encode()
    import hashlib
    import hmac
    sig = hmac.new(b"s", body, hashlib.sha256).hexdigest()

    ok, msg = service.process_gitee_event(body, "s", sig, "Issue Hook")
    assert ok is True and msg in ("ok",)

    # second time should be idempotent (duplicate)
    ok2, msg2 = service.process_gitee_event(body, "s", sig, "Issue Hook")
    assert ok2 is True and msg2 == "duplicate"


def test_deadletter_replay_flow(tmp_path, monkeypatch):
    # Isolate DB
    db_file = tmp_path / "dl.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("GITEE_WEBHOOK_SECRET", "s")
    monkeypatch.setenv("DEADLETTER_REPLAY_TOKEN", "t")

    import prometheus_client
    prometheus_client.REGISTRY = prometheus_client.CollectorRegistry()
    for mod in ["app.service", "app.models"]:
        if mod in sys.modules:
            del sys.modules[mod]
    models = importlib.import_module("app.models")
    service = importlib.import_module("app.service")

    models.init_db()

    payload = {"issue": {"id": 1001, "number": 1001, "title": "dl-demo"}}
    body = json.dumps(payload).encode()
    import hashlib
    import hmac
    sig = hmac.new(b"s", body, hashlib.sha256).hexdigest()

    # First, force notion failure to enqueue deadletter
    def fail_notion(_issue):
        return False, "synthetic_error"

    monkeypatch.setattr(service, "notion_upsert_page", fail_notion)
    ok, msg = service.process_gitee_event(body, "s", sig, "Issue Hook")
    assert ok is False and msg == "notion_error"

    # Then, make notion succeed and replay once
    def succeed_notion(_issue):
        return True, "PAGE_ID"

    monkeypatch.setattr(service, "notion_upsert_page", succeed_notion)
    replayed = service.replay_deadletters_once("t")
    assert replayed >= 1


