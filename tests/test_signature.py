import pytest
from app.gitee import GiteeClient

def test_signature_verification():
    # ... 测试签名验证 ...
    secret = "s"
    payload = b"{}"
    import hashlib
    import hmac
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert GiteeClient.verify_signature(secret, payload, sig) is True
    assert GiteeClient.verify_signature(secret, payload, "bad") is False
