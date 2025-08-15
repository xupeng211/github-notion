#!/usr/bin/env python3
"""
远程服务器状态检查脚本
用于验证GitHub-Notion同步服务在远程服务器上的运行状态
"""

import argparse
import sys
from datetime import datetime

import requests


def check_service_health(base_url, timeout=10):
    """检查服务健康状态"""
    print(f"🔍 检查服务健康状态: {base_url}")

    try:
        response = requests.get(f"{base_url}/health", timeout=timeout)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ 服务运行正常")
            print(f"   环境: {health_data.get('environment', 'unknown')}")
            print(f"   版本: {health_data.get('app_info', {}).get('version', 'unknown')}")
            print(f"   时间: {health_data.get('timestamp', 'unknown')}")

            # 检查各组件状态
            checks = health_data.get("checks", {})
            for component, status in checks.items():
                status_icon = (
                    "✅" if status.get("status") == "ok" else "⚠️" if status.get("status") == "warning" else "❌"
                )
                print(f"   {component}: {status_icon} {status.get('message', 'No message')}")

            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 无法连接到 {base_url}")
        print("   可能原因: 服务未启动、端口不正确、防火墙阻挡")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时: {timeout}秒内无响应")
        return False
    except Exception as e:
        print(f"❌ 检查异常: {str(e)}")
        return False


def check_metrics_endpoint(base_url, timeout=10):
    """检查监控指标端点"""
    print(f"\n📊 检查监控指标: {base_url}/metrics")

    try:
        response = requests.get(f"{base_url}/metrics", timeout=timeout)
        if response.status_code == 200:
            metrics_text = response.text
            metrics_count = len([line for line in metrics_text.split("\n") if line.startswith("#")])

            print("✅ 监控指标正常")
            print(f"   指标数量: ~{metrics_count//2} 个")

            # 检查关键指标
            key_metrics = ["webhook_requests_total", "idempotency_checks_total", "app_health", "sync_events_total"]

            found_metrics = []
            for metric in key_metrics:
                if metric in metrics_text:
                    found_metrics.append(metric)

            print(f"   核心指标: {len(found_metrics)}/{len(key_metrics)} 个")
            for metric in found_metrics:
                print(f"     ✅ {metric}")

            missing_metrics = set(key_metrics) - set(found_metrics)
            for metric in missing_metrics:
                print(f"     ❌ {metric} (缺失)")

            return len(found_metrics) >= len(key_metrics) * 0.75

        else:
            print(f"❌ 监控端点异常: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 监控检查失败: {str(e)}")
        return False


def test_webhook_endpoint(base_url, timeout=10):
    """测试webhook端点可用性"""
    print(f"\n🔗 检查webhook端点: {base_url}/gitee_webhook")

    try:
        # 发送一个无效的请求，期望得到特定的错误响应
        response = requests.post(
            f"{base_url}/gitee_webhook",
            json={"test": "data"},
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )

        if response.status_code in [400, 401, 403, 422]:
            print("✅ webhook端点可访问")
            if response.status_code == 403:
                print("   ✅ 安全检查正常工作 (需要正确的secret)")
            elif response.status_code == 422:
                print("   ✅ 数据验证正常工作")
            return True
        elif response.status_code == 500:
            print("⚠️ webhook端点响应异常，可能配置问题")
            print(f"   响应: {response.text[:200]}")
            return False
        else:
            print(f"⚠️ webhook端点状态异常: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ webhook检查失败: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="检查远程GitHub-Notion同步服务状态")
    parser.add_argument("--url", required=True, help="服务基础URL (如: http://your-server:8000)")
    parser.add_argument("--timeout", type=int, default=10, help="请求超时时间 (默认: 10秒)")

    args = parser.parse_args()

    # 清理URL
    base_url = args.url.rstrip("/")

    print("=" * 60)
    print("🚀 GitHub-Notion同步服务远程状态检查")
    print(f"📍 目标服务: {base_url}")
    print(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 执行各项检查
    health_ok = check_service_health(base_url, args.timeout)
    metrics_ok = check_metrics_endpoint(base_url, args.timeout)
    webhook_ok = test_webhook_endpoint(base_url, args.timeout)

    # 总结报告
    print("\n" + "=" * 60)
    print("📋 检查结果总结:")
    print(f"   服务健康: {'✅ 正常' if health_ok else '❌ 异常'}")
    print(f"   监控指标: {'✅ 正常' if metrics_ok else '❌ 异常'}")
    print(f"   Webhook端点: {'✅ 可用' if webhook_ok else '❌ 异常'}")

    if all([health_ok, metrics_ok, webhook_ok]):
        print("\n🎉 远程服务完全正常，可以使用！")
        sys.exit(0)
    elif health_ok:
        print("\n⚠️ 服务基本正常，但部分功能可能异常")
        print("💡 建议: 检查环境变量配置和日志")
        sys.exit(1)
    else:
        print("\n❌ 服务异常，需要排查问题")
        print("💡 建议: 检查服务是否启动、端口配置、防火墙设置")
        sys.exit(2)


if __name__ == "__main__":
    main()
