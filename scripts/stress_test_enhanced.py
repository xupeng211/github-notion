#!/usr/bin/env python3
"""
增强压力测试脚本
专门测试新增的安全验证、幂等性、监控指标等功能在高负载下的表现
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import os
import statistics
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

import aiohttp

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EnhancedStressTester:
    """增强压力测试器"""

    def __init__(
        self,
        base_url: str,
        github_secret: str = "test-secret",
        gitee_secret: str = "test-secret",
        notion_secret: str = "test-secret",
    ):
        self.base_url = base_url.rstrip("/")
        self.github_secret = github_secret
        self.gitee_secret = gitee_secret
        self.notion_secret = notion_secret
        self.results: List[Dict[str, Any]] = []

    def generate_github_payload(self, issue_number: int) -> Tuple[Dict[str, Any], str]:
        """生成GitHub webhook payload和签名"""
        payload = {
            "action": "opened",
            "number": issue_number,
            "issue": {
                "id": 1000000 + issue_number,
                "number": issue_number,
                "title": f"Stress Test Issue {issue_number}",
                "body": f"This is stress test issue #{issue_number}",
                "state": "open",
                "created_at": datetime.now().isoformat() + "Z",
                "updated_at": datetime.now().isoformat() + "Z",
                "user": {"login": "stress-tester", "id": 12345},
                "labels": [{"name": "test"}, {"name": "performance"}],
                "assignees": [],
                "milestone": None,
            },
            "repository": {
                "id": 123456789,
                "name": "stress-test",
                "full_name": "stress-tester/stress-test",
                "html_url": "https://github.com/stress-tester/stress-test",
            },
        }

        # 生成GitHub签名
        body_str = json.dumps(payload, separators=(",", ":"))
        signature = hmac.new(self.github_secret.encode(), body_str.encode(), hashlib.sha256).hexdigest()

        return payload, f"sha256={signature}"

    def generate_gitee_payload(self, issue_number: int) -> Tuple[Dict[str, Any], str]:
        """生成Gitee webhook payload和签名"""
        payload = {
            "action": "open",
            "issue": {
                "id": 2000000 + issue_number,
                "number": issue_number,
                "title": f"Gitee Stress Test Issue {issue_number}",
                "body": f"This is Gitee stress test issue #{issue_number}",
                "state": "开启",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "user": {"name": "stress-tester", "id": 54321},
            },
        }

        return payload, self.gitee_secret

    def generate_notion_payload(self, page_number: int) -> Tuple[Dict[str, Any], str]:
        """生成Notion webhook payload和签名"""
        timestamp = str(int(time.time()))
        payload = {
            "object": "page",
            "id": f"stress-test-page-{page_number}",
            "created_time": datetime.now().isoformat() + "Z",
            "last_edited_time": datetime.now().isoformat() + "Z",
            "properties": {
                "Title": {"title": [{"text": {"content": f"Notion Stress Test {page_number}"}}]},
                "Status": {"select": {"name": "In Progress"}},
            },
        }

        # 生成Notion风格的签名
        body_str = json.dumps(payload, separators=(",", ":"))
        payload_to_sign = f"{timestamp}.{body_str}"
        signature = hmac.new(self.notion_secret.encode(), payload_to_sign.encode(), hashlib.sha256).hexdigest()

        return payload, f"sha256={signature}", timestamp

    async def send_webhook_request(
        self,
        session: aiohttp.ClientSession,
        provider: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        delivery_id: str,
    ) -> Dict[str, Any]:
        """发送单个webhook请求"""
        start_time = time.time()
        endpoint = f"{self.base_url}/{provider}_webhook"

        try:
            async with session.post(endpoint, json=payload, headers=headers) as response:
                response_text = await response.text()
                duration = time.time() - start_time

                return {
                    "provider": provider,
                    "delivery_id": delivery_id,
                    "duration": duration,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300,
                    "response_size": len(response_text),
                    "error": (None if 200 <= response.status < 300 else response_text[:200]),
                }

        except Exception as e:
            duration = time.time() - start_time
            return {
                "provider": provider,
                "delivery_id": delivery_id,
                "duration": duration,
                "status_code": None,
                "success": False,
                "response_size": 0,
                "error": str(e)[:200],
            }

    async def run_concurrent_test(
        self, num_requests: int, concurrency: int, test_providers: List[str]
    ) -> List[Dict[str, Any]]:
        """运行并发测试"""
        print(f"🚀 开始压力测试: {num_requests} 请求, 并发数 {concurrency}")
        print(f"📋 测试提供商: {', '.join(test_providers)}")

        connector = aiohttp.TCPConnector(limit=concurrency * 2)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []

            for i in range(num_requests):
                for provider in test_providers:
                    delivery_id = f"stress-test-{provider}-{i}-{int(time.time())}"

                    if provider == "github":
                        payload, signature = self.generate_github_payload(i)
                        headers = {
                            "Content-Type": "application/json",
                            "X-GitHub-Event": "issues",
                            "X-Hub-Signature-256": signature,
                            "X-GitHub-Delivery": delivery_id,
                        }
                    elif provider == "gitee":
                        payload, token = self.generate_gitee_payload(i)
                        headers = {
                            "Content-Type": "application/json",
                            "X-Gitee-Event": "Issue Hook",
                            "X-Gitee-Token": token,
                            "X-Gitee-Delivery": delivery_id,
                            "X-Gitee-Timestamp": str(int(time.time())),
                        }
                    elif provider == "notion":
                        payload, signature, timestamp = self.generate_notion_payload(i)
                        headers = {
                            "Content-Type": "application/json",
                            "Notion-Signature": signature,
                            "Notion-Request-Id": delivery_id,
                            "Notion-Timestamp": timestamp,
                        }
                    else:
                        continue

                    task = self.send_webhook_request(session, provider, payload, headers, delivery_id)
                    tasks.append(task)

            # 执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤异常结果
            valid_results = []
            for result in results:
                if isinstance(result, Exception):
                    print(f"⚠️ 任务异常: {result}")
                else:
                    valid_results.append(result)

            return valid_results

    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析测试结果"""
        if not results:
            return {"error": "No valid results"}

        # 总体统计
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = total_requests - successful_requests

        # 性能统计
        durations = [r["duration"] for r in results]
        response_sizes = [r["response_size"] for r in results]

        # 按提供商分组统计
        provider_stats = {}
        for provider in set(r["provider"] for r in results):
            provider_results = [r for r in results if r["provider"] == provider]
            provider_durations = [r["duration"] for r in provider_results]

            provider_stats[provider] = {
                "total": len(provider_results),
                "success": sum(1 for r in provider_results if r["success"]),
                "failed": sum(1 for r in provider_results if not r["success"]),
                "avg_duration": (statistics.mean(provider_durations) if provider_durations else 0),
                "p95_duration": (
                    statistics.quantiles(provider_durations, n=20)[18] if len(provider_durations) > 1 else 0
                ),
                "p99_duration": (
                    statistics.quantiles(provider_durations, n=100)[98] if len(provider_durations) > 1 else 0
                ),
            }

        # 状态码统计
        status_codes = {}
        for result in results:
            code = result["status_code"] or "error"
            status_codes[code] = status_codes.get(code, 0) + 1

        return {
            "summary": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": ((successful_requests / total_requests) * 100 if total_requests > 0 else 0),
            },
            "performance": {
                "avg_duration": statistics.mean(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "p95_duration": (statistics.quantiles(durations, n=20)[18] if len(durations) > 1 else 0),
                "p99_duration": (statistics.quantiles(durations, n=100)[98] if len(durations) > 1 else 0),
                "avg_response_size": (statistics.mean(response_sizes) if response_sizes else 0),
            },
            "provider_breakdown": provider_stats,
            "status_codes": status_codes,
            "error_samples": [r["error"] for r in results if r["error"]][:5],  # 前5个错误样例
        }

    async def check_service_health(self) -> bool:
        """检查服务健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return False

    async def test_idempotency(self, num_duplicates: int = 10) -> Dict[str, Any]:
        """测试幂等性功能"""
        print(f"🔄 测试事件幂等性 (重复发送 {num_duplicates} 次相同事件)")

        # 生成一个固定的测试负载
        payload, signature = self.generate_github_payload(99999)  # 使用固定ID
        delivery_id = "idempotency-test-fixed-id"

        headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": signature,
            "X-GitHub-Delivery": delivery_id,
        }

        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_duplicates):
                task = self.send_webhook_request(session, "github", payload, headers, delivery_id)
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            success_count = sum(1 for r in results if r["success"])
            duplicate_responses = sum(1 for r in results if "duplicate" in str(r.get("error", "")))

            return {
                "duplicate_sends": num_duplicates,
                "successful_responses": success_count,
                "duplicate_detected": duplicate_responses,
                "idempotency_working": duplicate_responses > 0 or success_count == 1,
            }


async def main():
    parser = argparse.ArgumentParser(description="增强压力测试工具")
    parser.add_argument("--url", default="http://localhost:8000", help="服务URL")
    parser.add_argument("--requests", type=int, default=50, help="每个提供商的请求数")
    parser.add_argument("--concurrency", type=int, default=10, help="并发数")
    parser.add_argument("--providers", default="github,gitee,notion", help="测试的提供商 (逗号分隔)")
    parser.add_argument("--github-secret", default="test-secret", help="GitHub webhook密钥")
    parser.add_argument("--gitee-secret", default="test-secret", help="Gitee webhook密钥")
    parser.add_argument("--notion-secret", default="test-secret", help="Notion webhook密钥")

    args = parser.parse_args()

    providers = args.providers.split(",")
    tester = EnhancedStressTester(args.url, args.github_secret, args.gitee_secret, args.notion_secret)

    print("🔍 检查服务健康状态...")
    if not await tester.check_service_health():
        print("❌ 服务不可用，退出测试")
        return 1
    print("✅ 服务健康检查通过")

    # 1. 运行主要压力测试
    print(f"\n🚀 开始主要压力测试")
    start_time = time.time()
    results = await tester.run_concurrent_test(args.requests, args.concurrency, providers)
    test_duration = time.time() - start_time

    # 2. 测试幂等性
    print(f"\n🔄 测试幂等性功能")
    idempotency_results = await tester.test_idempotency()

    # 3. 分析结果
    analysis = tester.analyze_results(results)

    # 4. 生成报告
    print(f"\n{'='*60}")
    print(f"📊 压力测试报告")
    print(f"{'='*60}")
    print(f"测试时长: {test_duration:.2f} 秒")
    print(f"总请求数: {analysis['summary']['total_requests']}")
    print(f"成功请求: {analysis['summary']['successful_requests']}")
    print(f"失败请求: {analysis['summary']['failed_requests']}")
    print(f"成功率: {analysis['summary']['success_rate']:.1f}%")
    print(f"平均响应时间: {analysis['performance']['avg_duration']*1000:.1f} ms")
    print(f"P95响应时间: {analysis['performance']['p95_duration']*1000:.1f} ms")
    print(f"P99响应时间: {analysis['performance']['p99_duration']*1000:.1f} ms")
    print(f"QPS: {analysis['summary']['total_requests']/test_duration:.1f}")

    print(f"\n📋 各提供商性能:")
    for provider, stats in analysis["provider_breakdown"].items():
        success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  {provider}:")
        print(f"    成功率: {success_rate:.1f}% ({stats['success']}/{stats['total']})")
        print(f"    平均响应: {stats['avg_duration']*1000:.1f} ms")
        print(f"    P95: {stats['p95_duration']*1000:.1f} ms")

    print(f"\n🔄 幂等性测试结果:")
    print(f"  重复发送: {idempotency_results['duplicate_sends']} 次")
    print(f"  成功响应: {idempotency_results['successful_responses']} 次")
    print(f"  检测到重复: {idempotency_results['duplicate_detected']} 次")
    print(f"  幂等性正常: {'✅' if idempotency_results['idempotency_working'] else '❌'}")

    if analysis["status_codes"]:
        print(f"\n📈 状态码分布:")
        for code, count in analysis["status_codes"].items():
            print(f"  {code}: {count}")

    if analysis["error_samples"]:
        print(f"\n❌ 错误样例:")
        for error in analysis["error_samples"]:
            print(f"  - {error}")

    # 性能评估
    avg_duration_ms = analysis["performance"]["avg_duration"] * 1000
    success_rate = analysis["summary"]["success_rate"]
    qps = analysis["summary"]["total_requests"] / test_duration

    print(f"\n🎯 性能评估:")
    if success_rate >= 95 and avg_duration_ms < 500 and qps >= 10:
        print("  ✅ 优秀 - 性能表现良好，可以部署")
    elif success_rate >= 90 and avg_duration_ms < 1000 and qps >= 5:
        print("  ⚠️  良好 - 性能可接受，建议优化后部署")
    else:
        print("  ❌ 需要优化 - 性能不达标，建议优化后再部署")
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
