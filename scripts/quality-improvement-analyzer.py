#!/usr/bin/env python3
"""
📈 持续质量改进分析器
基于测试数据分析和优化建议
"""
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


class QualityAnalyzer:
    """质量分析器"""

    def __init__(self, reports_dir: str = "quality-reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

    def analyze_coverage_trends(self) -> Dict:
        """分析覆盖率趋势"""
        print("📊 分析覆盖率趋势...")

        coverage_files = list(self.reports_dir.glob("coverage-*.xml"))
        if not coverage_files:
            print("⚠️  未找到覆盖率报告文件")
            return {}

        trends = {}
        for file in sorted(coverage_files):
            try:
                tree = ET.parse(file)
                root = tree.getroot()

                timestamp = file.stem.split("-")[-1]
                overall_coverage = float(root.attrib["line-rate"]) * 100

                module_coverage = {}
                for pkg in root.findall(".//package"):
                    name = pkg.attrib["name"]
                    if name.startswith("app"):
                        module_coverage[name] = float(pkg.attrib["line-rate"]) * 100

                trends[timestamp] = {"overall": overall_coverage, "modules": module_coverage}
            except Exception as e:
                print(f"⚠️  解析覆盖率文件失败 {file}: {e}")

        return trends

    def analyze_test_failures(self) -> Dict:
        """分析测试失败模式"""
        print("🔍 分析测试失败模式...")

        failure_patterns = {"security": [], "business": [], "api": [], "performance": []}

        # 分析 pytest 输出日志
        log_files = list(self.reports_dir.glob("test-*.log"))
        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    content = f.read()

                # 提取失败信息
                if "FAILED" in content:
                    lines = content.split("\n")
                    for line in lines:
                        if "FAILED" in line:
                            if "security" in line.lower():
                                failure_patterns["security"].append(line)
                            elif "business" in line.lower() or "service" in line.lower():
                                failure_patterns["business"].append(line)
                            elif "api" in line.lower() or "integration" in line.lower():
                                failure_patterns["api"].append(line)
                            elif "performance" in line.lower():
                                failure_patterns["performance"].append(line)
            except Exception as e:
                print(f"⚠️  解析日志文件失败 {log_file}: {e}")

        return failure_patterns

    def analyze_performance_trends(self) -> Dict:
        """分析性能趋势"""
        print("🚀 分析性能趋势...")

        perf_files = list(self.reports_dir.glob("benchmark-*.json"))
        if not perf_files:
            print("⚠️  未找到性能基准报告")
            return {}

        performance_trends = {}
        for file in sorted(perf_files):
            try:
                with open(file, "r") as f:
                    data = json.load(f)

                timestamp = file.stem.split("-")[-1]
                benchmarks = {}

                for benchmark in data.get("benchmarks", []):
                    name = benchmark["name"]
                    stats = benchmark["stats"]
                    benchmarks[name] = {"mean": stats["mean"], "max": stats["max"], "min": stats["min"]}

                performance_trends[timestamp] = benchmarks
            except Exception as e:
                print(f"⚠️  解析性能文件失败 {file}: {e}")

        return performance_trends

    def generate_improvement_recommendations(
        self, coverage_trends: Dict, failure_patterns: Dict, performance_trends: Dict
    ) -> List[str]:
        """生成改进建议"""
        print("💡 生成改进建议...")

        recommendations = []

        # 覆盖率改进建议
        if coverage_trends:
            latest_coverage = list(coverage_trends.values())[-1]
            overall = latest_coverage["overall"]
            modules = latest_coverage["modules"]

            if overall < 70:
                recommendations.append(f"🎯 整体覆盖率 {overall:.1f}% 低于目标 70%，建议优先提升覆盖率")

            for module, coverage in modules.items():
                if coverage < 50:
                    recommendations.append(f"🔴 {module} 覆盖率 {coverage:.1f}% 过低，需要立即添加测试")
                elif coverage < 70:
                    recommendations.append(f"🟡 {module} 覆盖率 {coverage:.1f}% 需要改进")

        # 失败模式改进建议
        for test_type, failures in failure_patterns.items():
            if failures:
                count = len(failures)
                recommendations.append(f"⚠️  {test_type} 测试有 {count} 个失败，需要修复")

        # 性能改进建议
        if performance_trends:
            latest_perf = list(performance_trends.values())[-1]
            for benchmark, stats in latest_perf.items():
                if stats["mean"] > 0.1:  # 100ms
                    recommendations.append(f"🐌 {benchmark} 平均执行时间 {stats['mean']:.3f}s 过长，需要优化")

        return recommendations

    def generate_quality_report(self) -> str:
        """生成质量报告"""
        print("📋 生成质量报告...")

        coverage_trends = self.analyze_coverage_trends()
        failure_patterns = self.analyze_test_failures()
        performance_trends = self.analyze_performance_trends()
        recommendations = self.generate_improvement_recommendations(
            coverage_trends, failure_patterns, performance_trends
        )

        report = f"""# 📈 质量改进分析报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 覆盖率趋势

"""

        if coverage_trends:
            latest = list(coverage_trends.values())[-1]
            report += f"### 当前覆盖率状态\n"
            report += f"- **整体覆盖率**: {latest['overall']:.1f}%\n"

            for module, coverage in latest["modules"].items():
                status = "🟢" if coverage >= 70 else "🟡" if coverage >= 50 else "🔴"
                report += f"- **{module}**: {status} {coverage:.1f}%\n"
        else:
            report += "⚠️  暂无覆盖率数据\n"

        report += f"""
## 🔍 测试失败分析

"""

        total_failures = sum(len(failures) for failures in failure_patterns.values())
        if total_failures > 0:
            report += f"### 失败统计\n"
            for test_type, failures in failure_patterns.items():
                if failures:
                    report += f"- **{test_type}**: {len(failures)} 个失败\n"
        else:
            report += "✅ 无测试失败\n"

        report += f"""
## 🚀 性能趋势

"""

        if performance_trends:
            latest_perf = list(performance_trends.values())[-1]
            report += f"### 当前性能状态\n"
            for benchmark, stats in latest_perf.items():
                status = "🟢" if stats["mean"] < 0.01 else "🟡" if stats["mean"] < 0.1 else "🔴"
                report += f"- **{benchmark}**: {status} {stats['mean']:.3f}s (平均)\n"
        else:
            report += "⚠️  暂无性能数据\n"

        report += f"""
## 💡 改进建议

"""

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec}\n"
        else:
            report += "🎉 当前质量状态良好，无需特别改进\n"

        report += f"""
## 🎯 下一步行动

### 立即行动 (今天)
- 修复所有失败的测试
- 提升覆盖率低于 50% 的模块

### 短期改进 (1周内)
- 将整体覆盖率提升到 70%+
- 优化性能超过 100ms 的函数

### 长期规划 (1个月内)
- 建立性能基准监控
- 实施自动化质量门禁
- 定期质量审查

---

**📊 质量改进是一个持续的过程，建议每周运行此分析！**
"""

        return report

    def save_report(self, report: str) -> str:
        """保存报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"quality-report-{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        # 同时保存为最新报告
        latest_file = self.reports_dir / "quality-report-latest.md"
        with open(latest_file, "w", encoding="utf-8") as f:
            f.write(report)

        return str(report_file)


def main():
    """主函数"""
    print("📈 启动质量改进分析器...")

    analyzer = QualityAnalyzer()

    try:
        # 生成质量报告
        report = analyzer.generate_quality_report()

        # 保存报告
        report_file = analyzer.save_report(report)

        print(f"✅ 质量报告已生成: {report_file}")
        print("\n" + "=" * 50)
        print(report)
        print("=" * 50)

        # 检查是否有严重问题
        if "🔴" in report:
            print("\n⚠️  发现严重质量问题，建议立即处理！")
            return 1
        elif "🟡" in report:
            print("\n💡 发现质量改进机会，建议及时处理。")
            return 0
        else:
            print("\n🎉 质量状态良好！")
            return 0

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
