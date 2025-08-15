#!/usr/bin/env python3
"""
幂等性和监控压力测试脚本
专门测试幂等性机制和监控指标在高负载条件下的性能表现
"""

import os
import sys
import json
import time
import hmac
import asyncio
import aiohttp
import hashlib
import argparse
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import requests
from dataclasses import dataclass
from collections import defaultdict
import threading

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@dataclass
class TestResult:
    """测试结果数据类"""
    timestamp: datetime
    duration: float
    status_code: int
    success: bool
    error: Optional[str] = None
    duplicate_detected: bool = False
    metrics_recorded: bool = False
    response_size: int = 0
    

class IdempotencyMonitoringStressTester:
    """幂等性和监控压力测试器"""
    
    def __init__(self, base_url: str, webhook_secret: str = "test-secret"):
        self.base_url = base_url.rstrip('/')
        self.webhook_secret = webhook_secret
        self.results: List[TestResult] = []
        self.metrics_cache: Dict[str, Any] = {}
        self.lock = threading.Lock()
        
        # 测试配置
        self.test_config = {
            "max_concurrent": 50,
            "total_requests": 1000,
            "duplicate_rate": 0.3,  # 30%的请求为重复请求
            "timeout": 30,
            "metrics_check_interval": 5
        }
    
    def generate_webhook_signature(self, payload: str) -> str:
        """生成 webhook 签名"""
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature  # Gitee使用原始hex digest，不需要sha256=前缀
    
    def create_test_payload(self, test_id: int, is_duplicate: bool = False) -> Dict[str, Any]:
        """创建测试用的 payload"""
        # 如果是重复请求，使用固定的内容来确保真正的重复
        if is_duplicate:
            issue_id = 1  # 固定ID
            timestamp = "2024-01-01T00:00:00Z"  # 固定时间戳
            body_content = "This is a duplicate stress test issue for idempotency testing."
        else:
            issue_id = test_id
            timestamp = datetime.now().isoformat() + "Z"
            body_content = f"This is a stress test issue for idempotency testing. Test ID: {test_id}"
        
        return {
            "action": "opened",
            "issue": {
                "id": 1000000 + issue_id,
                "number": issue_id,
                "title": f"Stress Test Issue #{issue_id}",
                "body": body_content,
                "state": "open",
                "created_at": timestamp,
                "updated_at": timestamp,
                "user": {
                    "login": "stress-tester",
                    "id": 99999
                },
                "labels": [
                    {"name": "stress-test"},
                    {"name": "idempotency" if is_duplicate else "unique"}
                ]
            }
        }
    
    async def send_webhook_request(self, session: aiohttp.ClientSession, test_id: int, 
                                   is_duplicate: bool = False) -> TestResult:
        """发送单个 webhook 请求"""
        start_time = time.time()
        
        try:
            payload = self.create_test_payload(test_id, is_duplicate)
            payload_str = json.dumps(payload)
            
            # 重复请求使用固定的delivery_id来触发幂等性检测
            if is_duplicate:
                delivery_id = "stress-test-duplicate-fixed-id"
            else:
                delivery_id = f"stress-test-{test_id}-unique"
            
            headers = {
                'Content-Type': 'application/json',
                'X-Gitee-Event': 'Issue Hook',
                'X-Gitee-Token': self.generate_webhook_signature(payload_str),
                'X-Gitee-Delivery': delivery_id
            }
            
            async with session.post(
                f"{self.base_url}/gitee_webhook",
                data=payload_str,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.test_config["timeout"])
            ) as response:
                response_text = await response.text()
                duration = time.time() - start_time
                
                return TestResult(
                    timestamp=datetime.now(),
                    duration=duration,
                    status_code=response.status,
                    success=200 <= response.status < 300,
                    duplicate_detected=(
                        "duplicate" in response_text.lower() or 
                        "replay_attack_detected" in response_text.lower() or
                        response.status == 403  # 重复请求通常返回403
                    ),
                    response_size=len(response_text)
                )
                
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                timestamp=datetime.now(),
                duration=duration,
                status_code=0,
                success=False,
                error=str(e)
            )
    
    async def fetch_metrics(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """获取监控指标"""
        try:
            async with session.get(f"{self.base_url}/metrics") as response:
                if response.status == 200:
                    metrics_text = await response.text()
                    return self.parse_prometheus_metrics(metrics_text)
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    def parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, Any]:
        """解析 Prometheus 格式的指标"""
        metrics = {}
        
        for line in metrics_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            try:
                # 简单的指标解析
                if ' ' in line:
                    metric_part, value_part = line.rsplit(' ', 1)
                    metrics[metric_part] = float(value_part)
            except (ValueError, IndexError):
                continue
        
        return metrics
    
    async def monitor_metrics(self, session: aiohttp.ClientSession, duration_seconds: int):
        """持续监控指标"""
        end_time = time.time() + duration_seconds
        metrics_history = []
        
        while time.time() < end_time:
            metrics = await self.fetch_metrics(session)
            if "error" not in metrics:
                metrics_history.append({
                    "timestamp": datetime.now(),
                    "metrics": metrics
                })
            
            await asyncio.sleep(self.test_config["metrics_check_interval"])
        
        return metrics_history
    
    async def run_idempotency_stress_test(self, concurrent_requests: int, 
                                          total_requests: int) -> Dict[str, Any]:
        """运行幂等性压力测试"""
        print(f"🚀 开始幂等性压力测试: {total_requests} 请求，并发数: {concurrent_requests}")
        
        connector = aiohttp.TCPConnector(limit=concurrent_requests * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            
            # 启动指标监控
            monitor_task = asyncio.create_task(
                self.monitor_metrics(session, duration_seconds=60)
            )
            
            # 创建请求任务
            tasks = []
            for i in range(total_requests):
                is_duplicate = i % int(1 / self.test_config["duplicate_rate"]) == 0
                task = asyncio.create_task(
                    self.send_webhook_request(session, i, is_duplicate)
                )
                tasks.append(task)
                
                # 控制并发数
                if len(tasks) >= concurrent_requests:
                    completed_tasks = await asyncio.gather(*tasks[:concurrent_requests])
                    self.results.extend(completed_tasks)
                    tasks = tasks[concurrent_requests:]
            
            # 处理剩余任务
            if tasks:
                completed_tasks = await asyncio.gather(*tasks)
                self.results.extend(completed_tasks)
            
            # 等待监控结束
            metrics_history = await monitor_task
        
        return self.analyze_results(metrics_history)
    
    def analyze_results(self, metrics_history: List[Dict]) -> Dict[str, Any]:
        """分析测试结果"""
        successful_requests = sum(1 for r in self.results if r.success)
        failed_requests = len(self.results) - successful_requests
        duplicate_detected_count = sum(1 for r in self.results if r.duplicate_detected)
        
        durations = [r.duration for r in self.results if r.success]
        
        if durations:
            avg_duration = statistics.mean(durations)
            median_duration = statistics.median(durations)
            p95_duration = sorted(durations)[int(len(durations) * 0.95)]
            p99_duration = sorted(durations)[int(len(durations) * 0.99)]
        else:
            avg_duration = median_duration = p95_duration = p99_duration = 0
        
        # 分析指标
        metrics_analysis = self.analyze_metrics(metrics_history)
        
        # 计算错误率
        error_rate = failed_requests / len(self.results) if self.results else 0
        
        # 分析幂等性表现
        expected_duplicates = int(len(self.results) * self.test_config["duplicate_rate"])
        idempotency_accuracy = duplicate_detected_count / expected_duplicates if expected_duplicates > 0 else 0
        
        return {
            "summary": {
                "total_requests": len(self.results),
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "error_rate": error_rate,
                "duplicate_detected": duplicate_detected_count,
                "expected_duplicates": expected_duplicates,
                "idempotency_accuracy": idempotency_accuracy
            },
            "performance": {
                "avg_response_time": avg_duration,
                "median_response_time": median_duration,
                "p95_response_time": p95_duration,
                "p99_response_time": p99_duration,
                "total_duration": max(r.timestamp for r in self.results) - min(r.timestamp for r in self.results)
            },
            "metrics": metrics_analysis
        }
    
    def analyze_metrics(self, metrics_history: List[Dict]) -> Dict[str, Any]:
        """分析监控指标"""
        if not metrics_history:
            return {"error": "No metrics data collected"}
        
        # 提取关键指标的变化
        key_metrics = [
            "webhook_requests_total",
            "idempotency_checks_total",
            "duplicate_events_total",
            "sync_events_total",
            "webhook_request_duration_seconds"
        ]
        
        metrics_analysis = {}
        
        for metric_name in key_metrics:
            values = []
            for entry in metrics_history:
                for full_metric_name, value in entry["metrics"].items():
                    if metric_name in full_metric_name:
                        values.append(value)
            
            if values:
                metrics_analysis[metric_name] = {
                    "initial": values[0] if values else 0,
                    "final": values[-1] if values else 0,
                    "increase": (values[-1] - values[0]) if len(values) >= 2 else 0,
                    "max": max(values),
                    "avg": statistics.mean(values)
                }
        
        return metrics_analysis
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成测试报告"""
        report = []
        report.append("=" * 80)
        report.append("幂等性和监控压力测试报告")
        report.append("=" * 80)
        report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"测试目标: {self.base_url}")
        report.append("")
        
        # 概要信息
        summary = results["summary"]
        report.append("📊 测试概要:")
        report.append(f"  总请求数: {summary['total_requests']}")
        report.append(f"  成功请求: {summary['successful_requests']}")
        report.append(f"  失败请求: {summary['failed_requests']}")
        report.append(f"  错误率: {summary['error_rate']:.2%}")
        report.append(f"  检测到重复事件: {summary['duplicate_detected']}")
        report.append(f"  预期重复事件: {summary['expected_duplicates']}")
        report.append(f"  幂等性准确率: {summary['idempotency_accuracy']:.2%}")
        report.append("")
        
        # 性能指标
        perf = results["performance"]
        report.append("⚡ 性能指标:")
        report.append(f"  平均响应时间: {perf['avg_response_time']:.3f}s")
        report.append(f"  中位响应时间: {perf['median_response_time']:.3f}s")
        report.append(f"  95% 响应时间: {perf['p95_response_time']:.3f}s")
        report.append(f"  99% 响应时间: {perf['p99_response_time']:.3f}s")
        report.append("")
        
        # 监控指标分析
        metrics = results["metrics"]
        if "error" not in metrics:
            report.append("📈 监控指标分析:")
            for metric_name, data in metrics.items():
                report.append(f"  {metric_name}:")
                report.append(f"    初始值: {data['initial']:.2f}")
                report.append(f"    最终值: {data['final']:.2f}")
                report.append(f"    增长量: {data['increase']:.2f}")
                report.append(f"    最大值: {data['max']:.2f}")
                report.append(f"    平均值: {data['avg']:.2f}")
        else:
            report.append(f"❌ 监控指标收集失败: {metrics['error']}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    async def run_comprehensive_test(self):
        """运行综合压力测试"""
        print("🧪 开始运行幂等性和监控综合压力测试...")
        
        # 检查服务健康状态
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code != 200:
                print(f"❌ 服务健康检查失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 服务连接失败: {e}")
            return False
        
        print("✅ 服务健康检查通过")
        
        # 运行压力测试
        results = await self.run_idempotency_stress_test(
            concurrent_requests=self.test_config["max_concurrent"],
            total_requests=self.test_config["total_requests"]
        )
        
        # 生成并打印报告
        report = self.generate_report(results)
        print(report)
        
        # 保存报告到文件
        report_filename = f"idempotency_monitoring_stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📋 报告已保存到: {report_filename}")
        
        # 评估测试结果
        return self.evaluate_test_results(results)
    
    def evaluate_test_results(self, results: Dict[str, Any]) -> bool:
        """评估测试结果是否符合预期"""
        summary = results["summary"]
        perf = results["performance"]
        
        # 定义通过标准
        criteria = {
            "error_rate": 0.05,  # 错误率 < 5%
            "idempotency_accuracy": 0.95,  # 幂等性准确率 > 95%
            "avg_response_time": 2.0,  # 平均响应时间 < 2s
            "p99_response_time": 5.0   # 99%响应时间 < 5s
        }
        
        passed_checks = []
        failed_checks = []
        
        # 检查错误率
        if summary["error_rate"] <= criteria["error_rate"]:
            passed_checks.append(f"✅ 错误率: {summary['error_rate']:.2%} <= {criteria['error_rate']:.1%}")
        else:
            failed_checks.append(f"❌ 错误率: {summary['error_rate']:.2%} > {criteria['error_rate']:.1%}")
        
        # 检查幂等性准确率
        if summary["idempotency_accuracy"] >= criteria["idempotency_accuracy"]:
            passed_checks.append(f"✅ 幂等性准确率: {summary['idempotency_accuracy']:.2%} >= {criteria['idempotency_accuracy']:.1%}")
        else:
            failed_checks.append(f"❌ 幂等性准确率: {summary['idempotency_accuracy']:.2%} < {criteria['idempotency_accuracy']:.1%}")
        
        # 检查响应时间
        if perf["avg_response_time"] <= criteria["avg_response_time"]:
            passed_checks.append(f"✅ 平均响应时间: {perf['avg_response_time']:.3f}s <= {criteria['avg_response_time']}s")
        else:
            failed_checks.append(f"❌ 平均响应时间: {perf['avg_response_time']:.3f}s > {criteria['avg_response_time']}s")
        
        if perf["p99_response_time"] <= criteria["p99_response_time"]:
            passed_checks.append(f"✅ 99%响应时间: {perf['p99_response_time']:.3f}s <= {criteria['p99_response_time']}s")
        else:
            failed_checks.append(f"❌ 99%响应时间: {perf['p99_response_time']:.3f}s > {criteria['p99_response_time']}s")
        
        print("\n🔍 测试结果评估:")
        for check in passed_checks:
            print(f"  {check}")
        for check in failed_checks:
            print(f"  {check}")
        
        all_passed = len(failed_checks) == 0
        print(f"\n{'🎉 压力测试通过!' if all_passed else '⚠️ 压力测试未完全通过，需要关注以上问题'}")
        
        return all_passed


def main():
    parser = argparse.ArgumentParser(description='幂等性和监控压力测试工具')
    parser.add_argument('--url', required=True, help='服务基础URL')
    parser.add_argument('--secret', default='test-secret', help='Webhook密钥')
    parser.add_argument('--concurrent', type=int, default=50, help='并发请求数')
    parser.add_argument('--requests', type=int, default=1000, help='总请求数')
    parser.add_argument('--duplicate-rate', type=float, default=0.3, help='重复请求比例')
    
    args = parser.parse_args()
    
    tester = IdempotencyMonitoringStressTester(args.url, args.secret)
    
    # 更新测试配置
    tester.test_config.update({
        "max_concurrent": args.concurrent,
        "total_requests": args.requests,
        "duplicate_rate": args.duplicate_rate
    })
    
    # 运行测试
    try:
        success = asyncio.run(tester.run_comprehensive_test())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 