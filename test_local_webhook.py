#!/usr/bin/env python3
"""
测试本地 GitHub Webhook 功能
"""

import hashlib
import hmac
import json

import requests


def create_github_signature(payload_body, secret):
    """创建 GitHub webhook 签名"""
    signature = hmac.new(secret.encode("utf-8"), payload_body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def test_github_webhook():
    """测试 GitHub webhook 端点"""

    # 使用本地服务器的 webhook secret
    webhook_secret = "7a0f7d8a1b968a26275206e7ded245849207a302651eed1ef5b965dad931c518"

    # 创建测试 payload
    payload = {
        "action": "opened",
        "issue": {
            "id": 12345,
            "number": 1,
            "title": "本地测试 Issue",
            "body": "这是一个本地测试创建的 issue",
            "state": "open",
            "user": {"login": "test-user", "name": "Test User"},
            "html_url": "https://github.com/test-user/test-repo/issues/1",
            "created_at": "2025-08-17T19:30:00Z",
            "updated_at": "2025-08-17T19:30:00Z",
        },
        "repository": {
            "id": 12345,
            "name": "test-repo",
            "full_name": "test-user/test-repo",
            "html_url": "https://github.com/test-user/test-repo",
            "owner": {"login": "test-user", "name": "Test User"},
        },
        "sender": {"login": "test-user", "name": "Test User"},
    }

    payload_json = json.dumps(payload)
    signature = create_github_signature(payload_json, webhook_secret)

    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issues",
        "X-GitHub-Delivery": "test-delivery-12345",
        "X-Hub-Signature-256": signature,
        "User-Agent": "GitHub-Hookshot/test",
    }

    print("🧪 测试 GitHub Webhook 端点...")
    print(f"URL: http://localhost:8000/github_webhook")
    print(f"Event: issues")
    print(f"Action: opened")
    print(f"Signature: {signature[:20]}...")
    print()

    try:
        response = requests.post("http://localhost:8000/github_webhook", data=payload_json, headers=headers, timeout=30)

        print(f"状态码: {response.status_code}")

        if response.text:
            try:
                response_json = response.json()
                print(f"响应内容: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
            except:
                print(f"响应内容: {response.text}")
        else:
            print("响应内容: (空)")

        return response.status_code == 200

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def test_invalid_signature():
    """测试无效签名"""
    payload = {"test": "invalid"}
    payload_json = json.dumps(payload)

    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issues",
        "X-GitHub-Delivery": "test-delivery-invalid",
        "X-Hub-Signature-256": "sha256=invalid_signature",
        "User-Agent": "GitHub-Hookshot/test",
    }

    print("🧪 测试无效签名...")

    try:
        response = requests.post("http://localhost:8000/github_webhook", data=payload_json, headers=headers, timeout=10)

        print(f"状态码: {response.status_code}")
        print(f"预期: 403 (Forbidden)")

        return response.status_code == 403

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


if __name__ == "__main__":
    print("🚀 开始本地 GitHub Webhook 测试")
    print("=" * 50)

    # 测试有效的 webhook
    success1 = test_github_webhook()
    print()

    # 测试无效签名
    success2 = test_invalid_signature()
    print()

    print("=" * 50)
    if success1 and success2:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败")
        print(f"有效 webhook: {'✅' if success1 else '❌'}")
        print(f"无效签名: {'✅' if success2 else '❌'}")
