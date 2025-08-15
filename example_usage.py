#!/usr/bin/env python3
"""
压力测试使用示例
演示如何使用各种测试工具来验证幂等性和监控功能
"""

import subprocess
import sys
import time
from typing import Any, Dict, List


def run_command(cmd: List[str], description: str) -> Dict[str, Any]:
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"🏃 {description}")
    print(f"📝 命令: {' '.join(cmd)}")
    print("=" * 60)

    start_time = time.time()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5分钟超时

        duration = time.time() - start_time
        success = result.returncode == 0

        # 打印输出
        if result.stdout:
            print(result.stdout)

        if result.stderr and not success:
            print(f"❌ 错误输出:\n{result.stderr}")

        print(f"\n⏱️ 耗时: {duration:.1f} 秒")
        print(f"📊 结果: {'✅ 成功' if success else '❌ 失败'}")

        return {
            "success": success,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
        }

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"⏰ 命令超时 ({duration:.1f} 秒)")
        return {"success": False, "duration": duration, "error": "命令超时"}
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ 执行异常: {e}")
        return {"success": False, "duration": duration, "error": str(e)}


def demo_quick_test(base_url: str, webhook_secret: str):
    """演示快速测试"""
    print("\n🎯 场景1: 快速功能验证")
    print("用途: 在开发过程中快速验证基本功能是否正常")
    print("时间: 通常在1-2分钟内完成")

    cmd = [
        sys.executable,
        "quick_idempotency_test.py",
        "--url",
        base_url,
        "--secret",
        webhook_secret,
    ]

    result = run_command(cmd, "快速验证幂等性和监控功能")

    if result["success"]:
        print("\n💡 解读: 快速测试通过，基本功能正常工作")
    else:
        print("\n🚨 警告: 快速测试失败，需要检查基础配置")

    return result


def demo_idempotency_stress_test(base_url: str, webhook_secret: str):
    """演示幂等性压力测试"""
    print("\n🎯 场景2: 幂等性压力测试")
    print("用途: 验证高并发情况下幂等性机制的可靠性")
    print("时间: 通常在5-15分钟内完成")

    # 使用较小的参数进行演示
    cmd = [
        sys.executable,
        "idempotency_monitoring_stress_test.py",
        "--url",
        base_url,
        "--secret",
        webhook_secret,
        "--concurrent",
        "20",  # 降低并发数用于演示
        "--requests",
        "200",  # 减少请求数用于演示
        "--duplicate-rate",
        "0.3",
    ]

    result = run_command(cmd, "幂等性高并发压力测试 (演示版)")

    if result["success"]:
        print("\n💡 解读: 幂等性压力测试通过，系统能够正确处理重复请求")
        print("   - 在高并发场景下，重复请求被正确识别和处理")
        print("   - 监控指标正确记录了幂等性检查的统计信息")
    else:
        print("\n🚨 警告: 幂等性压力测试失败，可能存在并发处理问题")

    return result


def demo_metrics_analysis(base_url: str):
    """演示监控指标分析"""
    print("\n🎯 场景3: 监控指标分析")
    print("用途: 验证监控系统的完整性和数据质量")
    print("时间: 通常在3-8分钟内完成")

    # 使用快速分析模式进行演示
    cmd = [sys.executable, "metrics_analyzer.py", "--url", base_url, "--quick"]

    result = run_command(cmd, "监控指标快速分析")

    if result["success"]:
        print("\n💡 解读: 监控指标分析通过，监控系统工作正常")
        print("   - 关键业务指标完整存在")
        print("   - 数据格式符合Prometheus标准")
        print("   - 指标数值在合理范围内")
    else:
        print("\n🚨 警告: 监控指标分析失败，监控系统可能存在问题")

    return result


def demo_comprehensive_test(base_url: str, webhook_secret: str):
    """演示完整测试套件"""
    print("\n🎯 场景4: 完整测试套件")
    print("用途: 运行完整的压力测试，全面验证系统性能")
    print("时间: 通常在15-30分钟内完成")
    print("注意: 这是一个较长的测试，适合在发布前或定期验证时运行")

    # 使用较小的参数进行演示
    cmd = [
        sys.executable,
        "run_stress_tests.py",
        "--url",
        base_url,
        "--secret",
        webhook_secret,
        "--skip-comprehensive",  # 跳过最长的综合测试
        "--idempotency-concurrent",
        "15",
        "--idempotency-requests",
        "150",
    ]

    result = run_command(cmd, "完整测试套件 (演示版)")

    if result["success"]:
        print("\n💡 解读: 完整测试套件通过，系统整体表现良好")
        print("   - 所有关键功能模块工作正常")
        print("   - 性能指标符合预期标准")
        print("   - 可以安全地在生产环境中部署")
    else:
        print("\n🚨 警告: 部分测试失败，需要详细分析问题并进行修复")

    return result


def main():
    """主函数"""
    print("🧪 压力测试工具使用示例")
    print("=" * 80)
    print("本示例将演示如何使用各种测试工具来验证系统的幂等性和监控功能")
    print("⚠️ 注意: 确保目标服务正在运行，并且可以访问相关端点")
    print("")

    # 配置参数 (可以根据实际情况修改)
    BASE_URL = "http://localhost:8000"  # 修改为你的服务地址
    WEBHOOK_SECRET = "test-secret"  # 修改为你的webhook密钥

    print(f"🎯 测试目标: {BASE_URL}")
    print(f"🔑 Webhook密钥: {WEBHOOK_SECRET}")
    print("")

    # 询问用户是否要继续
    try:
        user_input = input("是否开始演示? (y/n): ").strip().lower()
        if user_input not in ["y", "yes", "是"]:
            print("演示已取消")
            return
    except KeyboardInterrupt:
        print("\n演示已取消")
        return

    results = {}

    try:
        # 场景1: 快速验证测试
        results["quick_test"] = demo_quick_test(BASE_URL, WEBHOOK_SECRET)

        # 询问是否继续
        print(f"\n{'='*60}")
        print("第一个场景完成。是否继续下一个场景?")
        user_input = input("继续? (y/n): ").strip().lower()
        if user_input not in ["y", "yes", "是"]:
            print("演示结束")
            return

        # 场景2: 幂等性压力测试
        results["idempotency_stress"] = demo_idempotency_stress_test(BASE_URL, WEBHOOK_SECRET)

        # 询问是否继续
        print(f"\n{'='*60}")
        print("第二个场景完成。是否继续下一个场景?")
        user_input = input("继续? (y/n): ").strip().lower()
        if user_input not in ["y", "yes", "是"]:
            print("演示结束")
            return

        # 场景3: 监控指标分析
        results["metrics_analysis"] = demo_metrics_analysis(BASE_URL)

        # 询问是否运行最后的完整测试
        print(f"\n{'='*60}")
        print("前三个场景完成。是否运行完整测试套件? (这将需要更多时间)")
        user_input = input("运行完整测试? (y/n): ").strip().lower()
        if user_input in ["y", "yes", "是"]:
            # 场景4: 完整测试套件
            results["comprehensive_test"] = demo_comprehensive_test(BASE_URL, WEBHOOK_SECRET)

    except KeyboardInterrupt:
        print("\n\n⏹️ 演示被用户中断")

    # 总结报告
    print("\n" + "=" * 80)
    print("📊 演示总结报告")
    print("=" * 80)

    successful_tests = sum(1 for result in results.values() if result.get("success", False))
    total_tests = len(results)
    total_duration = sum(result.get("duration", 0) for result in results.values())

    print(f"总场景数: {total_tests}")
    print(f"成功场景: {successful_tests}")
    print(f"失败场景: {total_tests - successful_tests}")
    print(f"总耗时: {total_duration:.1f} 秒")

    print("\n各场景结果:")
    for test_name, result in results.items():
        status_icon = "✅" if result.get("success", False) else "❌"
        print(f"  {status_icon} {test_name}: {result.get('duration', 0):.1f}s")
        if not result.get("success", False) and "error" in result:
            print(f"     错误: {result['error']}")

    if successful_tests == total_tests:
        print("\n🎉 所有演示场景成功完成!")
        print("💡 你的系统在压力测试中表现良好，可以继续进行生产部署准备。")
    elif successful_tests > 0:
        print(f"\n⚠️ 部分演示场景成功 ({successful_tests}/{total_tests})")
        print("💡 建议检查失败的场景，解决相关问题后再次测试。")
    else:
        print("\n❌ 所有演示场景都失败了")
        print("💡 请检查服务配置和连接，确保服务正常运行。")

    print("\n📚 接下来的步骤:")
    print("1. 查看生成的测试报告文件")
    print("2. 根据测试结果优化系统配置")
    print("3. 在生产环境部署前进行完整的压力测试")
    print("4. 设置定期的性能监控和测试")

    print("\n📖 更多信息请参考: STRESS_TEST_GUIDE.md")
    print("=" * 80)


if __name__ == "__main__":
    main()
