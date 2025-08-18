#!/usr/bin/env python3
"""
超级简化的直接部署脚本
绕过所有复杂性，直接在服务器上创建最小可用服务
"""

import subprocess
import sys
import time

import requests


def run_command(cmd, description=""):
    """执行命令并显示结果"""
    print(f"🔧 {description}")
    print(f"   命令: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("   ✅ 成功")
            if result.stdout.strip():
                print(f"   输出: {result.stdout.strip()}")
        else:
            print(f"   ❌ 失败 (退出码: {result.returncode})")
            if result.stderr.strip():
                print(f"   错误: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"   ⏰ 超时")
        return False
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return False


def create_minimal_app():
    """创建最小的 FastAPI 应用"""
    app_code = """
from fastapi import FastAPI
from datetime import datetime
import json

app = FastAPI(title="GitHub-Notion Sync - Emergency Mode")

@app.get("/")
async def root():
    return {
        "message": "GitHub-Notion Sync Service",
        "status": "emergency_mode",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": "production",
        "mode": "emergency",
        "message": "Service is running in emergency mode"
    }

@app.get("/metrics")
async def metrics():
    return {
        "service": "github-notion-sync",
        "mode": "emergency",
        "uptime": "unknown",
        "requests": 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

    with open("emergency_app.py", "w") as f:
        f.write(app_code)
    print("✅ 创建了紧急应用文件")


def create_deployment_script():
    """创建部署脚本"""
    deploy_script = """#!/bin/bash
set -e

echo "🚨 执行超级简化部署..."

# 停止所有可能的服务
sudo pkill -f "uvicorn" 2>/dev/null || true
sudo pkill -f "python.*app" 2>/dev/null || true
sudo systemctl stop github-notion-sync 2>/dev/null || true
sudo systemctl stop test-service 2>/dev/null || true

# 检查端口
echo "🔍 检查端口 8000..."
sudo netstat -tlnp | grep :${APP_PORT:-8000} && echo "端口被占用，尝试释放..." || echo "端口空闲"

# 强制释放端口
sudo fuser -k 8000/tcp 2>/dev/null || true

# 等待端口释放
sleep 5

# 安装最基础的依赖
echo "📦 安装基础依赖..."
python3 -m pip install --user fastapi uvicorn --quiet

# 检查安装
echo "🔍 检查安装..."
python3 -c "import fastapi, uvicorn; print('✅ 依赖安装成功')"

# 启动应用
echo "🚀 启动紧急应用..."
cd /opt/github-notion-sync
nohup python3 -m uvicorn emergency_app:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# 等待启动
sleep 10

# 检查进程
echo "🔍 检查进程..."
ps aux | grep uvicorn | grep -v grep || echo "进程未找到"

# 检查端口
echo "🔍 检查端口..."
sudo netstat -tlnp | grep :${APP_PORT:-8000} || echo "端口未监听"

# 测试连接
echo "🧪 测试连接..."
curl -f http://localhost:8000/health || echo "连接测试失败"

echo "✅ 部署完成"
"""

    with open("ultra_deploy.sh", "w") as f:
        f.write(deploy_script)

    # 设置执行权限
    run_command("chmod +x ultra_deploy.sh", "设置脚本执行权限")
    print("✅ 创建了部署脚本")


def deploy_to_server():
    """部署到服务器"""
    server = os.getenv("AWS_SERVER", "3.35.106.116")

    print("🚀 开始超级简化部署...")

    # 1. 创建应用文件
    create_minimal_app()

    # 2. 创建部署脚本
    create_deployment_script()

    # 3. 传输文件（假设 SSH 密钥已配置）
    print("📤 传输文件到服务器...")

    # 创建目录
    run_command(
        f'ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no ubuntu@{server} "sudo mkdir -p /opt/github-notion-sync && sudo chown ubuntu:ubuntu /opt/github-notion-sync"',
        "创建应用目录",
    )

    # 传输文件
    run_command(
        f"scp -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no emergency_app.py ubuntu@{server}:/opt/github-notion-sync/",
        "传输应用文件",
    )
    run_command(
        f"scp -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no ultra_deploy.sh ubuntu@{server}:/opt/github-notion-sync/",
        "传输部署脚本",
    )

    # 4. 执行部署
    print("🚀 执行远程部署...")
    run_command(
        f'ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no ubuntu@{server} "cd /opt/github-notion-sync && ./ultra_deploy.sh"',
        "执行部署脚本",
    )

    # 5. 验证部署
    print("🔍 验证部署...")
    time.sleep(15)

    try:
        APP_PORT = os.getenv("APP_PORT", "8000")
        response = requests.get(f"http://{server}:{APP_PORT}/health", timeout=10)
        if response.status_code == 200:
            print("✅ 部署成功！服务正常运行")
            APP_PORT = os.getenv("APP_PORT", "8000")
            print(f"🌐 服务地址: http://{server}:{APP_PORT}")
            print(f"🏥 健康检查: http://{server}:{APP_PORT}/health")
            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


def main():
    """主函数"""
    print("🚨 超级简化部署开始...")
    print("=" * 50)

    # 检查 SSH 密钥
    import os

    if not os.path.exists(os.path.expanduser("~/.ssh/aws-key.pem")):
        print("❌ SSH 密钥不存在: ~/.ssh/aws-key.pem")
        print("请确保 AWS 私钥已正确配置")
        return False

    # 执行部署
    success = deploy_to_server()

    if success:
        print("\n🎉 超级简化部署成功！")
        print("📊 服务状态: 紧急模式运行")
        print("🔧 下一步: 可以逐步添加完整功能")
    else:
        print("\n❌ 部署失败")
        print("🔍 请检查服务器日志和网络连接")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
