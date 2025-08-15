#!/usr/bin/env python3
"""
压力测试运行脚本
集成所有测试工具，提供完整的幂等性和监控压力测试套件
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class StressTestRunner:
    """压力测试运行器"""

    def __init__(self, base_url: str, webhook_secret: str = "test-secret"):
        self.base_url = base_url.rstrip("/")
        self.webhook_secret = webhook_secret
        self.test_results: Dict[str, Any] = {}

        # 测试配置
        self.test_config = {
            "quick_test_enabled": True,
            "idempotency_stress_enabled": True,
            "metrics_analysis_enabled": True,
            "comprehensive_stress_enabled": True,
            # 快速测试参数
            "quick_test_timeout": 60,
            # 幂等性压力测试参数
            "idempotency_concurrent": 50,
            "idempotency_requests": 1000,
            "idempotency_duplicate_rate": 0.3,
            # 指标分析参数
            "metrics_duration_minutes": 5,
            "metrics_interval_seconds": 30,
            # 综合压力测试参数
            "comprehensive_concurrent": 100,
            "comprehensive_requests": 2000,
            "comprehensive_duration_minutes": 10,
        }

    def check_service_health(self) -> bool:
        """检查服务健康状态"""
        print("🏥 检查服务健康状态...")

        try:
            import requests

            response = requests.get(f"{self.base_url}/health", timeout=10)

            if response.status_code == 200:
                print("✅ 服务健康检查通过")
                return True
            else:
                print(f"❌ 服务健康检查失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 服务连接失败: {e}")
            return False

    def run_quick_test(self) -> Dict[str, Any]:
        """运行快速测试"""
        print("\n" + "=" * 60)
        print("🚀 运行快速功能验证测试")
        print("=" * 60)

        start_time = time.time()

        try:
            # 运行快速幂等性测试
            cmd = [sys.executable, "quick_idempotency_test.py", "--url", self.base_url, "--secret", self.webhook_secret]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.test_config["quick_test_timeout"])

            duration = time.time() - start_time
            success = result.returncode == 0

            return {
                "name": "快速功能验证",
                "success": success,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                "name": "快速功能验证",
                "success": False,
                "duration": duration,
                "error": "测试超时",
                "stdout": "",
                "stderr": "",
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "name": "快速功能验证",
                "success": False,
                "duration": duration,
                "error": str(e),
                "stdout": "",
                "stderr": "",
            }

    def run_idempotency_stress_test(self) -> Dict[str, Any]:
        """运行幂等性压力测试"""
        print("\n" + "=" * 60)
        print("⚡ 运行幂等性压力测试")
        print("=" * 60)

        start_time = time.time()

        try:
            cmd = [
                sys.executable,
                "idempotency_monitoring_stress_test.py",
                "--url",
                self.base_url,
                "--secret",
                self.webhook_secret,
                "--concurrent",
                str(self.test_config["idempotency_concurrent"]),
                "--requests",
                str(self.test_config["idempotency_requests"]),
                "--duplicate-rate",
                str(self.test_config["idempotency_duplicate_rate"]),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10分钟超时

            duration = time.time() - start_time
            success = result.returncode == 0

            return {
                "name": "幂等性压力测试",
                "success": success,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                "name": "幂等性压力测试",
                "success": False,
                "duration": duration,
                "error": "测试超时",
                "stdout": "",
                "stderr": "",
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "name": "幂等性压力测试",
                "success": False,
                "duration": duration,
                "error": str(e),
                "stdout": "",
                "stderr": "",
            }

    def run_metrics_analysis(self) -> Dict[str, Any]:
        """运行监控指标分析"""
        print("\n" + "=" * 60)
        print("📊 运行监控指标分析")
        print("=" * 60)

        start_time = time.time()

        try:
            cmd = [
                sys.executable,
                "metrics_analyzer.py",
                "--url",
                self.base_url,
                "--duration",
                str(self.test_config["metrics_duration_minutes"]),
                "--interval",
                str(self.test_config["metrics_interval_seconds"]),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.test_config["metrics_duration_minutes"] * 60 + 120,  # 额外2分钟缓冲
            )

            duration = time.time() - start_time
            success = result.returncode == 0

            return {
                "name": "监控指标分析",
                "success": success,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                "name": "监控指标分析",
                "success": False,
                "duration": duration,
                "error": "分析超时",
                "stdout": "",
                "stderr": "",
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "name": "监控指标分析",
                "success": False,
                "duration": duration,
                "error": str(e),
                "stdout": "",
                "stderr": "",
            }

    def run_comprehensive_stress_test(self) -> Dict[str, Any]:
        """运行综合压力测试"""
        print("\n" + "=" * 60)
        print("🔥 运行综合压力测试")
        print("=" * 60)

        start_time = time.time()

        try:
            # 使用现有的performance-test.py进行基础压力测试
            cmd = [
                sys.executable,
                "performance-test.py",
                "--url",
                self.base_url,
                "--requests",
                str(self.test_config["comprehensive_requests"]),
                "--concurrency",
                str(self.test_config["comprehensive_concurrent"]),
                "--webhook-secret",
                self.webhook_secret,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.test_config["comprehensive_duration_minutes"] * 60
            )

            duration = time.time() - start_time
            success = result.returncode == 0

            return {
                "name": "综合压力测试",
                "success": success,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                "name": "综合压力测试",
                "success": False,
                "duration": duration,
                "error": "测试超时",
                "stdout": "",
                "stderr": "",
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "name": "综合压力测试",
                "success": False,
                "duration": duration,
                "error": str(e),
                "stdout": "",
                "stderr": "",
            }

    def extract_key_metrics_from_output(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """从测试输出中提取关键指标"""
        key_metrics = {}

        for test_name, result in test_results.items():
            if not result.get("success", False):
                continue

            stdout = result.get("stdout", "")

            # 提取响应时间指标
            if "平均响应时间" in stdout:
                for line in stdout.split("\n"):
                    if "平均响应时间:" in line:
                        try:
                            time_str = line.split(":")[1].strip().split()[0]
                            key_metrics[f"{test_name}_avg_response_time"] = float(time_str)
                        except (IndexError, ValueError):
                            pass

            # 提取错误率
            if "错误率" in stdout:
                for line in stdout.split("\n"):
                    if "错误率:" in line:
                        try:
                            rate_str = line.split(":")[1].strip().rstrip("%")
                            key_metrics[f"{test_name}_error_rate"] = float(rate_str) / 100
                        except (IndexError, ValueError):
                            pass

            # 提取幂等性准确率
            if "幂等性准确率" in stdout:
                for line in stdout.split("\n"):
                    if "幂等性准确率:" in line:
                        try:
                            rate_str = line.split(":")[1].strip().rstrip("%")
                            key_metrics[f"{test_name}_idempotency_accuracy"] = float(rate_str) / 100
                        except (IndexError, ValueError):
                            pass

        return key_metrics

    def generate_summary_report(self) -> str:
        """生成测试总结报告"""
        report = []
        report.append("=" * 80)
        report.append("压力测试总结报告")
        report.append("=" * 80)
        report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"测试目标: {self.base_url}")
        report.append("")

        # 测试概要
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        total_duration = sum(result.get("duration", 0) for result in self.test_results.values())

        report.append("📋 测试概要:")
        report.append(f"  总测试数: {total_tests}")
        report.append(f"  成功测试: {successful_tests}")
        report.append(f"  失败测试: {total_tests - successful_tests}")
        report.append(f"  总耗时: {total_duration:.1f} 秒")
        report.append("")

        # 各测试详细结果
        report.append("📊 测试详细结果:")
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result.get("success", False) else "❌"
            report.append(f"  {status_icon} {result.get('name', test_name)}:")
            report.append(f"    状态: {'成功' if result.get('success', False) else '失败'}")
            report.append(f"    耗时: {result.get('duration', 0):.1f} 秒")

            if not result.get("success", False):
                error = result.get("error", "未知错误")
                report.append(f"    错误: {error}")

                stderr = result.get("stderr", "").strip()
                if stderr:
                    report.append(f"    错误详情: {stderr[:200]}...")

        report.append("")

        # 关键指标汇总
        key_metrics = self.extract_key_metrics_from_output(self.test_results)
        if key_metrics:
            report.append("📈 关键指标汇总:")
            for metric_name, value in key_metrics.items():
                if "response_time" in metric_name:
                    report.append(f"  {metric_name}: {value:.3f}s")
                elif "error_rate" in metric_name or "accuracy" in metric_name:
                    report.append(f"  {metric_name}: {value:.2%}")
                else:
                    report.append(f"  {metric_name}: {value}")
            report.append("")

        # 总体评估
        report.append("🎯 总体评估:")

        if successful_tests == total_tests:
            report.append("  ✅ 所有测试通过，系统在高负载下表现良好")
        elif successful_tests >= total_tests * 0.8:
            report.append("  ⚠️ 大部分测试通过，但有部分问题需要关注")
        else:
            report.append("  ❌ 多个测试失败，系统可能存在严重问题")

        # 建议
        report.append("\n💡 建议:")

        if successful_tests < total_tests:
            report.append("  • 检查失败的测试日志，识别具体问题")
            report.append("  • 优化系统配置或代码以提高稳定性")

        # 检查关键指标是否在合理范围内
        for metric_name, value in key_metrics.items():
            if "error_rate" in metric_name and value > 0.05:
                report.append(f"  • 错误率过高 ({value:.2%})，需要优化错误处理")
            elif "response_time" in metric_name and value > 2.0:
                report.append(f"  • 响应时间过长 ({value:.3f}s)，需要性能优化")
            elif "idempotency_accuracy" in metric_name and value < 0.95:
                report.append(f"  • 幂等性准确率偏低 ({value:.2%})，需要检查幂等性逻辑")

        if all(result.get("success", False) for result in self.test_results.values()):
            report.append("  • 系统表现良好，可以考虑在生产环境中部署")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def run_all_tests(self) -> bool:
        """运行所有压力测试"""
        print("🧪 开始运行完整的压力测试套件")
        print(f"📍 测试目标: {self.base_url}")
        print("")

        # 检查服务健康状态
        if not self.check_service_health():
            print("❌ 服务健康检查失败，无法继续测试")
            return False

        # 运行各项测试
        test_sequence = []

        if self.test_config["quick_test_enabled"]:
            test_sequence.append(("quick_test", self.run_quick_test))

        if self.test_config["idempotency_stress_enabled"]:
            test_sequence.append(("idempotency_stress", self.run_idempotency_stress_test))

        if self.test_config["metrics_analysis_enabled"]:
            test_sequence.append(("metrics_analysis", self.run_metrics_analysis))

        if self.test_config["comprehensive_stress_enabled"]:
            test_sequence.append(("comprehensive_stress", self.run_comprehensive_stress_test))

        # 执行测试
        for test_key, test_func in test_sequence:
            try:
                result = test_func()
                self.test_results[test_key] = result

                if result.get("success", False):
                    print(f"✅ {result.get('name', test_key)} 完成")
                else:
                    print(f"❌ {result.get('name', test_key)} 失败")
                    if "error" in result:
                        print(f"   错误: {result['error']}")

            except Exception as e:
                print(f"❌ {test_key} 执行异常: {e}")
                self.test_results[test_key] = {"name": test_key, "success": False, "duration": 0, "error": str(e)}

        # 生成总结报告
        summary_report = self.generate_summary_report()
        print("\n" + summary_report)

        # 保存报告到文件
        report_filename = f"stress_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(summary_report)

        print(f"📋 测试总结报告已保存到: {report_filename}")

        # 评估总体成功率
        successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        total_tests = len(self.test_results)
        success_rate = successful_tests / total_tests if total_tests > 0 else 0

        return success_rate >= 0.8  # 80%的测试通过则认为总体成功


def main():
    parser = argparse.ArgumentParser(description="压力测试套件运行器")
    parser.add_argument("--url", required=True, help="服务基础URL")
    parser.add_argument("--secret", default="test-secret", help="Webhook密钥")

    # 测试选项
    parser.add_argument("--skip-quick", action="store_true", help="跳过快速测试")
    parser.add_argument("--skip-idempotency", action="store_true", help="跳过幂等性压力测试")
    parser.add_argument("--skip-metrics", action="store_true", help="跳过指标分析")
    parser.add_argument("--skip-comprehensive", action="store_true", help="跳过综合压力测试")

    # 参数调整
    parser.add_argument("--idempotency-concurrent", type=int, default=50, help="幂等性测试并发数")
    parser.add_argument("--idempotency-requests", type=int, default=1000, help="幂等性测试请求数")
    parser.add_argument("--comprehensive-concurrent", type=int, default=100, help="综合测试并发数")
    parser.add_argument("--comprehensive-requests", type=int, default=2000, help="综合测试请求数")

    args = parser.parse_args()

    # 创建测试运行器
    runner = StressTestRunner(args.url, args.secret)

    # 更新测试配置
    runner.test_config.update(
        {
            "quick_test_enabled": not args.skip_quick,
            "idempotency_stress_enabled": not args.skip_idempotency,
            "metrics_analysis_enabled": not args.skip_metrics,
            "comprehensive_stress_enabled": not args.skip_comprehensive,
            "idempotency_concurrent": args.idempotency_concurrent,
            "idempotency_requests": args.idempotency_requests,
            "comprehensive_concurrent": args.comprehensive_concurrent,
            "comprehensive_requests": args.comprehensive_requests,
        }
    )

    try:
        success = runner.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 测试套件执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
