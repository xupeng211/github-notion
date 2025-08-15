#!/usr/bin/env python3
"""
监控指标分析工具
用于分析和验证Prometheus监控指标的准确性和完整性
"""

import argparse
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

import requests


class MetricsAnalyzer:
    """监控指标分析器"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.metrics_history: List[Dict[str, Any]] = []

        # 关键指标定义
        self.key_metrics = {
            "webhook_requests_total": {
                "type": "counter",
                "description": "Webhook请求总数",
                "labels": ["provider", "event_type", "status"],
            },
            "webhook_request_duration_seconds": {
                "type": "histogram",
                "description": "Webhook请求耗时",
                "labels": ["provider", "event_type"],
            },
            "idempotency_checks_total": {
                "type": "counter",
                "description": "幂等性检查总数",
                "labels": ["provider", "result"],
            },
            "duplicate_events_total": {
                "type": "counter",
                "description": "重复事件总数",
                "labels": ["provider", "duplicate_type"],
            },
            "sync_events_total": {
                "type": "counter",
                "description": "同步事件总数",
                "labels": [
                    "source_platform",
                    "target_platform",
                    "entity_type",
                    "action",
                    "status",
                ],
            },
            "github_api_calls_total": {
                "type": "counter",
                "description": "GitHub API调用总数",
                "labels": ["method", "endpoint", "status_code"],
            },
            "notion_api_calls_total": {
                "type": "counter",
                "description": "Notion API调用总数",
                "labels": ["method", "endpoint", "status_code"],
            },
        }

    def fetch_metrics(self) -> Dict[str, Any]:
        """获取当前的监控指标"""
        try:
            response = requests.get(f"{self.base_url}/metrics", timeout=10)
            if response.status_code == 200:
                return {
                    "timestamp": datetime.now(),
                    "status": "success",
                    "raw_text": response.text,
                    "parsed_metrics": self.parse_prometheus_metrics(response.text),
                }
            else:
                return {
                    "timestamp": datetime.now(),
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "raw_text": "",
                    "parsed_metrics": {},
                }
        except Exception as e:
            return {
                "timestamp": datetime.now(),
                "status": "error",
                "error": str(e),
                "raw_text": "",
                "parsed_metrics": {},
            }

    def parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, Dict[str, Any]]:
        """解析Prometheus格式的指标"""
        metrics = defaultdict(lambda: {"values": [], "help": "", "type": ""})

        for line in metrics_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # 解析HELP注释
            if line.startswith("# HELP "):
                parts = line[7:].split(" ", 1)
                if len(parts) >= 2:
                    metric_name, help_text = parts[0], parts[1]
                    metrics[metric_name]["help"] = help_text

            # 解析TYPE注释
            elif line.startswith("# TYPE "):
                parts = line[7:].split(" ", 1)
                if len(parts) >= 2:
                    metric_name, metric_type = parts[0], parts[1]
                    metrics[metric_name]["type"] = metric_type

            # 跳过其他注释
            elif line.startswith("#"):
                continue

            # 解析指标值
            else:
                try:
                    if " " in line:
                        metric_part, value_part = line.rsplit(" ", 1)
                        value = float(value_part)

                        # 解析指标名称和标签
                        if "{" in metric_part and "}" in metric_part:
                            metric_name = metric_part.split("{")[0]
                            labels_str = metric_part[metric_part.index("{") + 1 : metric_part.rindex("}")]
                            labels = self.parse_labels(labels_str)
                        else:
                            metric_name = metric_part
                            labels = {}

                        metrics[metric_name]["values"].append({"labels": labels, "value": value})

                except (ValueError, IndexError):
                    continue

        return dict(metrics)

    def parse_labels(self, labels_str: str) -> Dict[str, str]:
        """解析Prometheus标签"""
        labels = {}
        if not labels_str:
            return labels

        # 简单的标签解析
        for label_pair in labels_str.split(","):
            label_pair = label_pair.strip()
            if "=" in label_pair:
                key, value = label_pair.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"')
                labels[key] = value

        return labels

    def analyze_metrics_completeness(self, parsed_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """分析指标完整性"""
        found_metrics = set(parsed_metrics.keys())
        expected_metrics = set(self.key_metrics.keys())

        missing_metrics = expected_metrics - found_metrics
        unexpected_metrics = found_metrics - expected_metrics

        # 检查每个指标的标签完整性
        label_analysis = {}
        for metric_name, metric_data in parsed_metrics.items():
            if metric_name in self.key_metrics:
                expected_labels = set(self.key_metrics[metric_name].get("labels", []))

                actual_labels = set()
                for value_entry in metric_data["values"]:
                    actual_labels.update(value_entry["labels"].keys())

                label_analysis[metric_name] = {
                    "expected_labels": list(expected_labels),
                    "actual_labels": list(actual_labels),
                    "missing_labels": list(expected_labels - actual_labels),
                    "unexpected_labels": list(actual_labels - expected_labels),
                }

        return {
            "total_metrics": len(found_metrics),
            "expected_metrics": len(expected_metrics),
            "found_key_metrics": len(found_metrics & expected_metrics),
            "missing_metrics": list(missing_metrics),
            "unexpected_metrics": list(unexpected_metrics),
            "completeness_ratio": (
                len(found_metrics & expected_metrics) / len(expected_metrics) if expected_metrics else 1.0
            ),
            "label_analysis": label_analysis,
        }

    def analyze_metrics_values(self, parsed_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """分析指标数值合理性"""
        analysis = {}

        for metric_name, metric_data in parsed_metrics.items():
            if metric_name not in self.key_metrics:
                continue

            values = [entry["value"] for entry in metric_data["values"]]
            if not values:
                continue

            metric_type = self.key_metrics[metric_name]["type"]

            analysis[metric_name] = {
                "type": metric_type,
                "total_series": len(metric_data["values"]),
                "total_value": sum(values),
                "max_value": max(values),
                "min_value": min(values),
                "avg_value": sum(values) / len(values),
                "non_zero_series": sum(1 for v in values if v > 0),
                "zero_series": sum(1 for v in values if v == 0),
            }

            # 对于counter类型，检查是否有负值（不合理）
            if metric_type == "counter":
                negative_values = [v for v in values if v < 0]
                analysis[metric_name]["negative_values"] = len(negative_values)
                analysis[metric_name]["has_negative"] = len(negative_values) > 0

        return analysis

    def collect_metrics_over_time(self, duration_minutes: int = 5, interval_seconds: int = 30) -> List[Dict[str, Any]]:
        """在一段时间内收集指标"""
        print(f"📊 开始收集指标，持续 {duration_minutes} 分钟，间隔 {interval_seconds} 秒...")

        end_time = time.time() + (duration_minutes * 60)
        metrics_snapshots = []

        while time.time() < end_time:
            metrics_data = self.fetch_metrics()
            metrics_snapshots.append(metrics_data)

            if metrics_data["status"] == "success":
                print(
                    f"✅ {metrics_data['timestamp'].strftime('%H:%M:%S')} - 指标收集成功 "
                    f"({len(metrics_data['parsed_metrics'])} 个指标)"
                )
            else:
                print(
                    f"❌ {metrics_data['timestamp'].strftime('%H:%M:%S')} - 指标收集失败: "
                    f"{metrics_data.get('error', 'Unknown error')}"
                )

            time.sleep(interval_seconds)

        self.metrics_history.extend(metrics_snapshots)
        return metrics_snapshots

    def analyze_metrics_trends(self, metrics_snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析指标趋势"""
        if len(metrics_snapshots) < 2:
            return {"error": "需要至少2个时间点的数据来分析趋势"}

        trends = {}

        # 提取每个时间点的指标总和
        for metric_name in self.key_metrics.keys():
            metric_values_over_time = []

            for snapshot in metrics_snapshots:
                if snapshot["status"] != "success":
                    continue

                parsed_metrics = snapshot["parsed_metrics"]
                if metric_name in parsed_metrics:
                    total_value = sum(entry["value"] for entry in parsed_metrics[metric_name]["values"])
                    metric_values_over_time.append({"timestamp": snapshot["timestamp"], "value": total_value})

            if len(metric_values_over_time) >= 2:
                initial_value = metric_values_over_time[0]["value"]
                final_value = metric_values_over_time[-1]["value"]

                trends[metric_name] = {
                    "initial_value": initial_value,
                    "final_value": final_value,
                    "absolute_change": final_value - initial_value,
                    "relative_change": (
                        ((final_value - initial_value) / initial_value * 100) if initial_value > 0 else 0
                    ),
                    "data_points": len(metric_values_over_time),
                    "trend": (
                        "increasing"
                        if final_value > initial_value
                        else ("decreasing" if final_value < initial_value else "stable")
                    ),
                }

        return trends

    def generate_analysis_report(self, include_trends: bool = True) -> str:
        """生成分析报告"""
        if not self.metrics_history:
            return "❌ 没有可用的指标数据进行分析"

        # 使用最新的指标数据进行分析
        latest_snapshot = None
        for snapshot in reversed(self.metrics_history):
            if snapshot["status"] == "success":
                latest_snapshot = snapshot
                break

        if not latest_snapshot:
            return "❌ 没有成功的指标数据快照"

        report = []
        report.append("=" * 80)
        report.append("监控指标分析报告")
        report.append("=" * 80)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"数据快照时间: {latest_snapshot['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"总数据点: {len(self.metrics_history)}")
        report.append("")

        # 完整性分析
        completeness = self.analyze_metrics_completeness(latest_snapshot["parsed_metrics"])
        report.append("📋 指标完整性分析:")
        report.append(f"  找到指标: {completeness['total_metrics']}")
        report.append(f"  预期核心指标: {completeness['expected_metrics']}")
        report.append(
            f"  核心指标覆盖: {completeness['found_key_metrics']}/{completeness['expected_metrics']} "
            f"({completeness['completeness_ratio']:.1%})"
        )

        if completeness["missing_metrics"]:
            report.append(f"  缺失指标: {', '.join(completeness['missing_metrics'])}")

        if completeness["unexpected_metrics"]:
            report.append(f"  额外指标: {len(completeness['unexpected_metrics'])} 个")

        report.append("")

        # 数值分析
        values_analysis = self.analyze_metrics_values(latest_snapshot["parsed_metrics"])
        report.append("📈 指标数值分析:")

        for metric_name, analysis in values_analysis.items():
            report.append(f"  {metric_name} ({analysis['type']}):")
            report.append(f"    时间序列数: {analysis['total_series']}")
            report.append(f"    总值: {analysis['total_value']:.2f}")
            report.append(f"    最大值: {analysis['max_value']:.2f}")
            report.append(f"    平均值: {analysis['avg_value']:.2f}")
            report.append(f"    非零序列: {analysis['non_zero_series']}/{analysis['total_series']}")

            if analysis.get("has_negative"):
                report.append(f"    ⚠️ 发现负值: {analysis['negative_values']} 个 (Counter类型不应有负值)")

        report.append("")

        # 趋势分析（如果有多个数据点）
        if include_trends and len(self.metrics_history) > 1:
            trends = self.analyze_metrics_trends(self.metrics_history)
            if "error" not in trends:
                report.append("📊 指标趋势分析:")
                for metric_name, trend in trends.items():
                    report.append(f"  {metric_name}:")
                    report.append(f"    趋势: {trend['trend']}")
                    report.append(f"    变化量: {trend['absolute_change']:.2f} ({trend['relative_change']:+.1f}%)")
                    report.append(f"    初始值: {trend['initial_value']:.2f}")
                    report.append(f"    最终值: {trend['final_value']:.2f}")
                report.append("")

        # 标签分析
        label_analysis = completeness.get("label_analysis", {})
        if label_analysis:
            report.append("🏷️ 标签完整性分析:")
            for metric_name, labels in label_analysis.items():
                if labels["missing_labels"] or labels["unexpected_labels"]:
                    report.append(f"  {metric_name}:")
                    if labels["missing_labels"]:
                        report.append(f"    缺失标签: {', '.join(labels['missing_labels'])}")
                    if labels["unexpected_labels"]:
                        report.append(f"    额外标签: {', '.join(labels['unexpected_labels'])}")
            report.append("")

        # 评估总结
        report.append("🎯 评估总结:")

        # 完整性评分
        completeness_score = completeness["completeness_ratio"] * 100
        if completeness_score >= 90:
            report.append("  ✅ 指标完整性: 优秀")
        elif completeness_score >= 70:
            report.append("  ⚠️ 指标完整性: 良好")
        else:
            report.append("  ❌ 指标完整性: 需要改进")

        # 数据质量评分
        total_metrics = len(values_analysis)
        problematic_metrics = sum(1 for analysis in values_analysis.values() if analysis.get("has_negative", False))

        if problematic_metrics == 0:
            report.append("  ✅ 数据质量: 优秀")
        elif problematic_metrics <= total_metrics * 0.1:
            report.append("  ⚠️ 数据质量: 良好")
        else:
            report.append("  ❌ 数据质量: 需要关注")

        report.append("=" * 80)

        return "\n".join(report)

    def run_comprehensive_analysis(self, duration_minutes: int = 5) -> bool:
        """运行综合分析"""
        print(f"🔍 开始监控指标综合分析 (持续 {duration_minutes} 分钟)")
        print(f"📍 目标服务: {self.base_url}")
        print("")

        # 首先检查指标端点是否可用
        initial_metrics = self.fetch_metrics()
        if initial_metrics["status"] != "success":
            print(f"❌ 无法访问指标端点: {initial_metrics.get('error', 'Unknown error')}")
            return False

        print(f"✅ 指标端点可访问，发现 {len(initial_metrics['parsed_metrics'])} 个指标")

        # 收集一段时间内的指标
        metrics_snapshots = self.collect_metrics_over_time(duration_minutes)

        # 生成并打印报告
        report = self.generate_analysis_report()
        print("\n" + report)

        # 保存报告到文件
        report_filename = f"metrics_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"📋 分析报告已保存到: {report_filename}")

        # 简单的成功评估
        successful_snapshots = sum(1 for s in metrics_snapshots if s["status"] == "success")
        success_rate = successful_snapshots / len(metrics_snapshots) if metrics_snapshots else 0

        if success_rate >= 0.9:
            print("🎉 监控指标分析完成，系统表现良好")
            return True
        else:
            print(f"⚠️ 监控指标分析完成，成功率 {success_rate:.1%}，需要关注")
            return False


def main():
    parser = argparse.ArgumentParser(description="监控指标分析工具")
    parser.add_argument("--url", required=True, help="服务基础URL")
    parser.add_argument("--duration", type=int, default=5, help="监控持续时间（分钟）")
    parser.add_argument("--interval", type=int, default=30, help="采样间隔（秒）")
    parser.add_argument("--quick", action="store_true", help="快速分析（只分析当前状态）")

    args = parser.parse_args()

    analyzer = MetricsAnalyzer(args.url)

    try:
        if args.quick:
            # 快速分析
            print("⚡ 运行快速指标分析...")
            metrics_data = analyzer.fetch_metrics()
            analyzer.metrics_history = [metrics_data]

            if metrics_data["status"] == "success":
                report = analyzer.generate_analysis_report(include_trends=False)
                print(report)
                return 0
            else:
                print(f"❌ 指标获取失败: {metrics_data.get('error', 'Unknown error')}")
                return 1
        else:
            # 完整分析
            success = analyzer.run_comprehensive_analysis(args.duration)
            return 0 if success else 1

    except KeyboardInterrupt:
        print("\n⏹️ 分析被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 分析执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
