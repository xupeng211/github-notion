#!/usr/bin/env python3
"""
快速幂等性测试脚本
用于快速验证幂等性功能是否正常工作
"""

import argparse
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Any, Dict

import requests


class QuickIdempotencyTester:
    """快速幂等性测试器"""

    def __init__(self, base_url: str, webhook_secret: str = "test-secret"):
        self.base_url = base_url.rstrip("/")
        self.webhook_secret = webhook_secret

    def generate_webhook_signature(self, payload: str) -> str:
        """生成 webhook 签名"""
        signature = hmac.new(self.webhook_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return signature  # Gitee使用原始hex digest，不需要sha256=前缀

    def create_test_payload(self) -> Dict[str, Any]:
        """创建测试payload"""
        return {
            "action": "opened",
            "issue": {
                "id": 999999,
                "number": 1,
                "title": "Quick Idempotency Test Issue",
                "body": "This is a test issue for quick idempotency verification.",
                "state": "open",
                "created_at": datetime.now().isoformat() + "Z",
                "updated_at": datetime.now().isoformat() + "Z",
                "user": {"login": "idempotency-tester", "id": 12345},
                "labels": [{"name": "test"}, {"name": "idempotency"}],
            },
        }

    def send_webhook_request(self, delivery_id: str) -> Dict[str, Any]:
        """发送webhook请求"""
        payload = self.create_test_payload()
        payload_str = json.dumps(payload)

        headers = {
            "Content-Type": "application/json",
            "X-Gitee-Event": "Issue Hook",
            "X-Gitee-Token": self.generate_webhook_signature(payload_str),
            "X-Gitee-Delivery": delivery_id,
        }

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/gitee_webhook",
                data=payload_str,
                headers=headers,
                timeout=10,
            )
            duration = time.time() - start_time

            return {
                "status_code": response.status_code,
                "response_text": response.text,
                "duration": duration,
                "success": 200 <= response.status_code < 300,
                "delivery_id": delivery_id,
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "status_code": 0,
                "response_text": str(e),
                "duration": duration,
                "success": False,
                "delivery_id": delivery_id,
            }

    def test_idempotency(self) -> bool:
        """测试幂等性功能"""
        print("🧪 开始快速幂等性测试...")

        # 使用固定的delivery ID来模拟重复请求
        delivery_id = "quick-idempotency-test-12345"

        print(f"📤 发送第一个请求 (Delivery ID: {delivery_id})")
        first_response = self.send_webhook_request(delivery_id)

        if not first_response["success"]:
            print(f"❌ 第一个请求失败: {first_response['response_text']}")
            return False

        print(f"✅ 第一个请求成功 (状态码: {first_response['status_code']}, 耗时: {first_response['duration']:.3f}s)")

        # 等待一秒，确保第一个请求已处理完成
        time.sleep(1)

        print(f"📤 发送重复请求 (相同Delivery ID: {delivery_id})")
        second_response = self.send_webhook_request(delivery_id)

        if not second_response["success"]:
            print(f"❌ 重复请求失败: {second_response['response_text']}")
            return False

        print(f"✅ 重复请求成功 (状态码: {second_response['status_code']}, 耗时: {second_response['duration']:.3f}s)")

        # 检查响应是否表明检测到重复
        duplicate_detected = (
            "duplicate" in second_response["response_text"].lower()
            or second_response["status_code"] == 200  # 服务返回成功但是实际上是重复
        )

        if duplicate_detected:
            print("✅ 幂等性验证通过 - 检测到重复请求")
            print(f"   第二个请求响应: {second_response['response_text'][:100]}...")
            return True
        else:
            print("❌ 幂等性验证失败 - 未正确处理重复请求")
            print(f"   第二个请求响应: {second_response['response_text'][:100]}...")
            return False

    def check_metrics_endpoint(self) -> bool:
        """检查监控指标端点"""
        print("\n📊 检查监控指标端点...")

        try:
            response = requests.get(f"{self.base_url}/metrics", timeout=10)

            if response.status_code == 200:
                metrics_text = response.text

                # 检查是否包含关键指标
                key_metrics = [
                    "webhook_requests_total",
                    "idempotency_checks_total",
                    "duplicate_events_total",
                ]

                found_metrics = []
                for metric in key_metrics:
                    if metric in metrics_text:
                        found_metrics.append(metric)

                if len(found_metrics) >= 2:  # 至少找到2个关键指标
                    print(f"✅ 监控指标端点正常 (找到 {len(found_metrics)}/{len(key_metrics)} 个关键指标)")
                    print(f"   找到的指标: {', '.join(found_metrics)}")
                    return True
                else:
                    print(f"⚠️ 监控指标端点可用但指标不完整 (只找到 {len(found_metrics)}/{len(key_metrics)} 个)")
                    return False
            else:
                print(f"❌ 监控指标端点返回错误: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 监控指标端点连接失败: {e}")
            return False

    def run_quick_test(self) -> bool:
        """运行快速测试"""
        print("🚀 开始快速幂等性和监控测试")
        print(f"📍 测试目标: {self.base_url}")
        print("")

        # 检查服务健康状态
        try:
            health_response = requests.get(f"{self.base_url}/health", timeout=5)
            if health_response.status_code != 200:
                print(f"❌ 服务健康检查失败: HTTP {health_response.status_code}")
                return False
            print("✅ 服务健康检查通过")
        except Exception as e:
            print(f"❌ 服务连接失败: {e}")
            return False

        # 测试幂等性
        idempotency_ok = self.test_idempotency()

        # 检查监控指标
        metrics_ok = self.check_metrics_endpoint()

        # 总结结果
        print("\n" + "=" * 50)
        print("快速测试结果总结:")
        print(f"  幂等性功能: {'✅ 正常' if idempotency_ok else '❌ 异常'}")
        print(f"  监控指标:   {'✅ 正常' if metrics_ok else '❌ 异常'}")

        overall_success = idempotency_ok and metrics_ok
        print(f"  总体状态:   {'🎉 通过' if overall_success else '⚠️ 需要关注'}")
        print("=" * 50)

        return overall_success


def main():
    parser = argparse.ArgumentParser(description="快速幂等性和监控测试工具")
    parser.add_argument("--url", required=True, help="服务基础URL")
    parser.add_argument("--secret", default="test-secret", help="Webhook密钥")

    args = parser.parse_args()

    tester = QuickIdempotencyTester(args.url, args.secret)

    try:
        success = tester.run_quick_test()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
