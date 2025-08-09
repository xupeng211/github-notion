#!/usr/bin/env python3

"""
性能测试脚本，用于测试 Gitee-Notion 同步服务的性能和负载能力
"""

import requests
import json
import time
import concurrent.futures
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceTester:
    def __init__(self, base_url: str, webhook_secret: str = None):
        self.base_url = base_url.rstrip('/')
        self.webhook_secret = webhook_secret
        self.session = requests.Session()
        
        # 测试结果统计
        self.results: List[Dict[str, Any]] = []
    
    def generate_test_payload(self) -> Dict[str, Any]:
        """生成测试用的 webhook payload"""
        return {
            "action": "open",
            "issue": {
                "number": f"test_{int(time.time())}",
                "title": f"Performance Test Issue {datetime.now().isoformat()}",
                "body": "This is a test issue for performance testing.",
                "state": "open",
                "labels": [
                    {"name": "test"},
                    {"name": "performance"}
                ],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "user": {
                    "name": "test_user"
                }
            }
        }
    
    def send_webhook_request(self) -> Dict[str, Any]:
        """发送单个 webhook 请求"""
        start_time = time.time()
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-Gitee-Event': 'Issue Hook'
            }
            
            if self.webhook_secret:
                headers['X-Gitee-Token'] = self.webhook_secret
            
            payload = self.generate_test_payload()
            response = self.session.post(
                f"{self.base_url}/gitee_webhook",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            duration = time.time() - start_time
            status_code = response.status_code
            
            return {
                'duration': duration,
                'status_code': status_code,
                'success': 200 <= status_code < 300,
                'error': None
            }
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                'duration': duration,
                'status_code': None,
                'success': False,
                'error': str(e)
            }
    
    def run_load_test(self, num_requests: int, concurrency: int) -> Dict[str, Any]:
        """运行负载测试"""
        logger.info(f"开始负载测试: {num_requests} 请求, 并发数 {concurrency}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(self.send_webhook_request) for _ in range(num_requests)]
            self.results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 分析结果
        successful_requests = sum(1 for r in self.results if r['success'])
        failed_requests = len(self.results) - successful_requests
        durations = [r['duration'] for r in self.results]
        
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        # 计算百分位数
        sorted_durations = sorted(durations)
        p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
        p99 = sorted_durations[int(len(sorted_durations) * 0.99)]
        
        return {
            'total_requests': num_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'average_duration': avg_duration,
            'max_duration': max_duration,
            'min_duration': min_duration,
            'p95_duration': p95,
            'p99_duration': p99
        }
    
    def check_health(self) -> bool:
        """检查服务健康状态"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Gitee-Notion 同步服务性能测试工具')
    parser.add_argument('--url', required=True, help='服务基础 URL')
    parser.add_argument('--requests', type=int, default=100, help='总请求数')
    parser.add_argument('--concurrency', type=int, default=10, help='并发数')
    parser.add_argument('--webhook-secret', help='Webhook 密钥')
    
    args = parser.parse_args()
    
    tester = PerformanceTester(args.url, args.webhook_secret)
    
    # 检查服务健康状态
    if not tester.check_health():
        logger.error("服务健康检查失败，退出测试")
        return 1
    
    # 运行负载测试
    results = tester.run_load_test(args.requests, args.concurrency)
    
    # 打印结果
    print("\n=== 测试结果 ===")
    print(f"总请求数: {results['total_requests']}")
    print(f"成功请求: {results['successful_requests']}")
    print(f"失败请求: {results['failed_requests']}")
    print(f"平均响应时间: {results['average_duration']:.3f} 秒")
    print(f"最大响应时间: {results['max_duration']:.3f} 秒")
    print(f"最小响应时间: {results['min_duration']:.3f} 秒")
    print(f"95% 响应时间: {results['p95_duration']:.3f} 秒")
    print(f"99% 响应时间: {results['p99_duration']:.3f} 秒")
    
    return 0

if __name__ == "__main__":
    exit(main()) 