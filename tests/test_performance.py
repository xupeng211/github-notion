#!/usr/bin/env python3

import concurrent.futures
import hashlib
import hmac
import json
import os
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
import requests

# 设置测试环境变量
os.environ.setdefault("DB_URL", "sqlite:///data/perf_test.db")
os.environ.setdefault("LOG_LEVEL", "ERROR")
os.environ.setdefault("DISABLE_NOTION", "1")

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PERF_TESTS") != "1",
    reason="Set RUN_PERF_TESTS=1 to enable performance tests",
)

# 测试配置
TEST_CONFIG = {
    "base_url": os.getenv("TEST_BASE_URL", "http://localhost:8787"),
    "gitee_webhook_secret": os.getenv("TEST_GITEE_WEBHOOK_SECRET", "test-secret"),
    "test_duration": int(os.getenv("TEST_DURATION", "300")),  # 默认测试时间 5 分钟
    "concurrent_users": int(os.getenv("CONCURRENT_USERS", "10")),  # 默认并发用户数
    "request_interval": float(os.getenv("REQUEST_INTERVAL", "1.0")),  # 请求间隔（秒）
}


class PerformanceTest:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def generate_test_payload(self) -> Dict[str, Any]:
        """生成测试用的 webhook payload"""
        return {
            "action": "open",
            "issue": {
                "number": f"perf_test_{int(time.time())}",
                "title": f"Performance Test Issue {datetime.now(timezone.utc).isoformat()}",
                "body": "This is a test issue for performance testing.",
                "state": "open",
                "labels": [{"name": "test"}, {"name": "performance"}],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "user": {"name": "test_user"},
            },
        }

    def calculate_signature(self, payload: str) -> str:
        """计算 webhook 签名"""
        return hmac.new(
            TEST_CONFIG["gitee_webhook_secret"].encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    def send_request(self) -> Dict[str, Any]:
        """发送单个请求并记录结果"""
        payload = self.generate_test_payload()
        payload_str = json.dumps(payload)

        headers = {
            "Content-Type": "application/json",
            "X-Gitee-Token": self.calculate_signature(payload_str),
            "X-Gitee-Event": "Issue Hook",
        }

        start_time = time.time()
        try:
            response = requests.post(
                f"{TEST_CONFIG['base_url']}/gitee_webhook",
                headers=headers,
                data=payload_str,
                timeout=30,
            )

            end_time = time.time()
            duration = end_time - start_time

            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration": duration,
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
            }

            if not result["success"]:
                self.errors.append(
                    {
                        "timestamp": result["timestamp"],
                        "status_code": result["status_code"],
                        "response": response.text,
                    }
                )

            return result

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            error_result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration": duration,
                "status_code": None,
                "success": False,
                "error": str(e),
            }

            self.errors.append(error_result)
            return error_result

    def run_load_test(self):
        """运行负载测试"""
        print("开始负载测试:")
        print(f"- 基础 URL: {TEST_CONFIG['base_url']}")
        print(f"- 测试时长: {TEST_CONFIG['test_duration']} 秒")
        print(f"- 并发用户: {TEST_CONFIG['concurrent_users']}")
        print(f"- 请求间隔: {TEST_CONFIG['request_interval']} 秒")

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=TEST_CONFIG["concurrent_users"]) as executor:
            while time.time() - start_time < TEST_CONFIG["test_duration"]:
                futures = []
                for _ in range(TEST_CONFIG["concurrent_users"]):
                    futures.append(executor.submit(self.send_request))
                    time.sleep(TEST_CONFIG["request_interval"] / TEST_CONFIG["concurrent_users"])

                for future in concurrent.futures.as_completed(futures):
                    self.results.append(future.result())

        self.print_results()

    def print_results(self):
        """打印测试结果"""
        if not self.results:
            print("没有测试结果")
            return

        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r["success"])
        failed_requests = total_requests - successful_requests

        durations = [r["duration"] for r in self.results]
        avg_duration = statistics.mean(durations)
        median_duration = statistics.median(durations)
        p95_duration = sorted(durations)[int(len(durations) * 0.95)]
        p99_duration = sorted(durations)[int(len(durations) * 0.99)]

        print("\n=== 测试结果 ===")
        print(f"总请求数: {total_requests}")
        print(f"成功请求: {successful_requests}")
        print(f"失败请求: {failed_requests}")
        print(f"成功率: {(successful_requests/total_requests)*100:.2f}%")
        print("\n响应时间统计:")
        print(f"- 平均响应时间: {avg_duration:.3f} 秒")
        print(f"- 中位数响应时间: {median_duration:.3f} 秒")
        print(f"- 95% 响应时间: {p95_duration:.3f} 秒")
        print(f"- 99% 响应时间: {p99_duration:.3f} 秒")

        if self.errors:
            print(f"\n错误统计 ({len(self.errors)} 个错误):")
            error_types = {}
            for error in self.errors:
                error_type = error.get("status_code", "Connection Error")
                error_types[error_type] = error_types.get(error_type, 0) + 1

            for error_type, count in error_types.items():
                print(f"- {error_type}: {count} 次")

        # 计算每秒请求数
        test_duration = self.results[-1]["timestamp"] - self.results[0]["timestamp"]
        requests_per_second = total_requests / test_duration
        print("\n性能指标:")
        print(f"- 每秒请求数: {requests_per_second:.2f}")
        print(f"- 总测试时长: {test_duration:.2f} 秒")


def main():
    """主函数"""
    test = PerformanceTest()
    test.run_load_test()


if __name__ == "__main__":
    main()
