#!/usr/bin/env python3
"""
获取GitHub Actions日志的脚本
分析CI/CD失败原因
"""

import json
import re
from datetime import datetime

import requests


def get_workflow_jobs(run_id):
    """获取工作流的作业信息"""
    try:
        url = f"https://api.github.com/repos/xupeng211/github-notion/actions/runs/{run_id}/jobs"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 获取作业信息失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 获取作业信息出错: {e}")
        return None


def analyze_failure_patterns(logs):
    """分析常见的失败模式"""
    failure_patterns = {
        "pytest_error": r"FAILED.*test_.*\.py",
        "import_error": r"ImportError|ModuleNotFoundError",
        "syntax_error": r"SyntaxError",
        "coverage_error": r"Coverage failure|coverage.*less than",
        "docker_error": r"docker.*error|build.*failed",
        "network_error": r"network.*error|connection.*failed|timeout",
        "permission_error": r"permission.*denied|access.*denied",
        "dependency_error": r"pip.*error|package.*not found",
    }

    found_issues = []

    for pattern_name, pattern in failure_patterns.items():
        matches = re.findall(pattern, logs, re.IGNORECASE)
        if matches:
            found_issues.append({"type": pattern_name, "matches": matches[:3]})  # 只显示前3个匹配

    return found_issues


def get_latest_failed_run():
    """获取最新失败的运行"""
    try:
        url = "https://api.github.com/repos/xupeng211/github-notion/actions/runs"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            for run in data.get("workflow_runs", []):
                if run["conclusion"] == "failure":
                    return run["id"]
        return None
    except Exception as e:
        print(f"❌ 获取失败运行出错: {e}")
        return None


def main():
    print("🔍 分析CI/CD失败原因...")
    print("=" * 50)

    # 获取最新失败的运行ID
    run_id = get_latest_failed_run()
    if not run_id:
        print("❌ 未找到失败的运行")
        return

    print(f"📋 分析运行ID: {run_id}")

    # 获取作业信息
    jobs_data = get_workflow_jobs(run_id)
    if not jobs_data:
        return

    failed_jobs = []
    for job in jobs_data.get("jobs", []):
        if job["conclusion"] == "failure":
            failed_jobs.append(job)

    if not failed_jobs:
        print("❓ 未找到失败的作业")
        return

    print(f"\n❌ 发现 {len(failed_jobs)} 个失败的作业:")

    for i, job in enumerate(failed_jobs, 1):
        print(f"\n{i}. 作业: {job['name']}")
        print(f"   状态: {job['conclusion']}")
        print(f"   开始时间: {job['started_at']}")
        print(f"   结束时间: {job['completed_at']}")

        # 分析失败的步骤
        failed_steps = [step for step in job.get("steps", []) if step["conclusion"] == "failure"]
        if failed_steps:
            print(f"   失败步骤:")
            for step in failed_steps:
                print(f"     - {step['name']}")

        print(f"   🔗 日志链接: https://github.com/xupeng211/github-notion/actions/runs/{run_id}")

    # 基于作业名称提供修复建议
    print(f"\n💡 修复建议:")

    for job in failed_jobs:
        job_name = job["name"].lower()

        if "quality" in job_name or "test" in job_name:
            print("🧪 测试相关问题:")
            print("   - 检查pytest配置是否正确")
            print("   - 验证测试依赖是否安装")
            print("   - 确认覆盖率阈值设置合理")
            print("   - 运行: python -m pytest tests/priority/ -v")

        elif "build" in job_name or "docker" in job_name:
            print("🐳 构建相关问题:")
            print("   - 检查Dockerfile语法")
            print("   - 验证依赖安装")
            print("   - 检查网络连接")
            print("   - 运行: docker build -f Dockerfile.github .")

        elif "deploy" in job_name:
            print("🚀 部署相关问题:")
            print("   - 检查AWS凭证配置")
            print("   - 验证服务器连接")
            print("   - 检查环境变量设置")


if __name__ == "__main__":
    main()
