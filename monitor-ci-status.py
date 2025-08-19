#!/usr/bin/env python3
"""
CI/CD 状态监控脚本
实时监控GitHub Actions的执行状态
"""

import json
import time
from datetime import datetime

import requests


def get_latest_workflow_run():
    """获取最新的工作流运行状态"""
    try:
        # GitHub API endpoint for workflow runs
        url = "https://api.github.com/repos/xupeng211/github-notion/actions/runs"

        # 不需要认证也可以获取公开仓库的基本信息
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("workflow_runs"):
                latest_run = data["workflow_runs"][0]
                return {
                    "id": latest_run["id"],
                    "status": latest_run["status"],
                    "conclusion": latest_run["conclusion"],
                    "workflow_name": latest_run["name"],
                    "created_at": latest_run["created_at"],
                    "updated_at": latest_run["updated_at"],
                    "html_url": latest_run["html_url"],
                    "head_commit": (
                        latest_run["head_commit"]["message"][:50] if latest_run.get("head_commit") else "N/A"
                    ),
                }
        else:
            print(f"❌ API请求失败: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ 获取工作流状态失败: {e}")
        return None


def format_status(status, conclusion):
    """格式化状态显示"""
    if status == "completed":
        if conclusion == "success":
            return "✅ 成功"
        elif conclusion == "failure":
            return "❌ 失败"
        elif conclusion == "cancelled":
            return "⏹️ 取消"
        else:
            return f"❓ {conclusion}"
    elif status == "in_progress":
        return "🔄 运行中"
    elif status == "queued":
        return "⏳ 排队中"
    else:
        return f"❓ {status}"


def monitor_ci_status():
    """监控CI/CD状态"""
    print("🚀 开始监控CI/CD状态...")
    print("=" * 60)

    last_status = None
    last_run_id = None

    while True:
        try:
            run_info = get_latest_workflow_run()

            if run_info:
                current_status = f"{run_info['status']}-{run_info['conclusion']}"
                current_run_id = run_info["id"]

                # 只在状态变化或新的运行时显示
                if current_status != last_status or current_run_id != last_run_id:
                    now = datetime.now().strftime("%H:%M:%S")
                    status_display = format_status(run_info["status"], run_info["conclusion"])

                    print(f"\n[{now}] 📊 CI/CD 状态更新:")
                    print(f"  🔧 工作流: {run_info['workflow_name']}")
                    print(f"  📝 提交: {run_info['head_commit']}")
                    print(f"  📊 状态: {status_display}")
                    print(f"  🔗 链接: {run_info['html_url']}")

                    if run_info["status"] == "completed":
                        if run_info["conclusion"] == "success":
                            print("\n🎉 CI/CD 流水线执行成功！")
                            print("✅ 质量门禁通过")
                            print("✅ 构建成功")
                            print("✅ 部署完成")
                            break
                        elif run_info["conclusion"] == "failure":
                            print("\n❌ CI/CD 流水线执行失败！")
                            print("请检查GitHub Actions页面查看详细错误信息")
                            print(f"🔗 {run_info['html_url']}")
                            break

                    last_status = current_status
                    last_run_id = current_run_id

            else:
                print("⚠️ 无法获取工作流状态，继续监控...")

            # 等待30秒后再次检查
            time.sleep(30)

        except KeyboardInterrupt:
            print("\n\n⏹️ 监控已停止")
            break
        except Exception as e:
            print(f"❌ 监控过程中出错: {e}")
            time.sleep(30)


if __name__ == "__main__":
    monitor_ci_status()
