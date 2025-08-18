#!/usr/bin/env python3
"""
本地到 AWS 的直接部署脚本
绕过 GitHub Actions，直接从本地部署到 AWS EC2
"""

import subprocess
import sys
import time
import requests
import os
from pathlib import Path

# AWS 配置
AWS_SERVER = "3.35.106.116"
AWS_USER = "ubuntu"
APP_DIR = "/opt/github-notion-sync"
SERVICE_NAME = "github-notion-sync"

# 环境变量（需要手动设置）
REQUIRED_SECRETS = {
    "GITHUB_WEBHOOK_SECRET": "7a0f7d8a1b968a26275206e7ded245849207a302651eed1ef5b965dad931c518",
    "NOTION_TOKEN": "请设置您的 Notion Token",
    "NOTION_DATABASE_ID": "请设置您的 Notion Database ID",
    "GITHUB_TOKEN": "请设置您的 GitHub Token",
    "DEADLETTER_REPLAY_TOKEN": "请设置您的 Deadletter Replay Token",
}


def run_command(cmd, description="", timeout=60):
    """执行命令并显示结果"""
    print(f"🔧 {description}")
    print(f"   命令: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            print(f"   ✅ 成功")
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


def check_ssh_key():
    """检查 SSH 密钥"""
    ssh_key_path = Path.home() / ".ssh" / "aws-key.pem"
    if not ssh_key_path.exists():
        print("❌ SSH 密钥不存在: ~/.ssh/aws-key.pem")
        print("请将 AWS 私钥保存到该位置并设置权限 600")
        return False

    # 设置权限
    run_command(f"chmod 600 {ssh_key_path}", "设置 SSH 密钥权限")
    return True


def test_ssh_connection():
    """测试 SSH 连接"""
    print("🔍 测试 SSH 连接...")
    cmd = f"ssh -i ~/.ssh/aws-key.pem -o ConnectTimeout=10 -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} \"echo 'SSH 连接成功'\""
    return run_command(cmd, "测试 SSH 连接", timeout=15)


def cleanup_server():
    """清理服务器环境"""
    print("🧹 清理服务器环境...")

    cleanup_script = f"""
sudo systemctl stop {SERVICE_NAME} 2>/dev/null || true
sudo systemctl stop emergency-service 2>/dev/null || true
sudo systemctl stop test-service 2>/dev/null || true
sudo pkill -f "uvicorn" 2>/dev/null || true
sudo fuser -k 8000/tcp 2>/dev/null || true
sudo mkdir -p {APP_DIR}
sudo chown {AWS_USER}:{AWS_USER} {APP_DIR}
cd {APP_DIR}
rm -rf app/ *.py *.txt *.log *.db 2>/dev/null || true
echo "✅ 服务器清理完成"
"""

    cmd = f"ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} '{cleanup_script}'"
    return run_command(cmd, "清理服务器环境", timeout=30)


def install_dependencies():
    """安装依赖"""
    print("📦 安装依赖...")

    install_script = f"""
python3 --version
python3 -m pip install --user --upgrade pip

echo "安装核心依赖..."
python3 -m pip install --user --timeout 60 --retries 3 \\
    fastapi==0.111.0 \\
    uvicorn==0.30.1 \\
    pydantic==1.10.22 \\
    sqlalchemy==2.0.30 \\
    python-dotenv==1.0.1 \\
    httpx==0.27.0

python3 -c "import fastapi, uvicorn, sqlalchemy; print('✅ 核心依赖验证通过')"
echo "✅ 依赖安装完成"
"""

    cmd = f"ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} '{install_script}'"
    return run_command(cmd, "安装依赖", timeout=120)


def transfer_files():
    """传输文件"""
    print("📤 传输应用文件...")

    # 传输应用目录
    cmd1 = f"scp -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no -r app/ {AWS_USER}@{AWS_SERVER}:{APP_DIR}/"
    success1 = run_command(cmd1, "传输 app 目录", timeout=60)

    # 传输 requirements.txt
    cmd2 = f"scp -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no requirements.txt {AWS_USER}@{AWS_SERVER}:{APP_DIR}/"
    success2 = run_command(cmd2, "传输 requirements.txt", timeout=30)

    return success1 and success2


def configure_environment():
    """配置环境"""
    print("⚙️ 配置环境...")

    # 创建环境配置
    env_content = f"""
ENVIRONMENT=production
DB_URL=sqlite:///./data/app.db
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=100
MAX_REQUEST_SIZE=2097152
DISABLE_NOTION=false
GITHUB_WEBHOOK_SECRET={REQUIRED_SECRETS["GITHUB_WEBHOOK_SECRET"]}
GITHUB_TOKEN={REQUIRED_SECRETS["GITHUB_TOKEN"]}
NOTION_TOKEN={REQUIRED_SECRETS["NOTION_TOKEN"]}
NOTION_DATABASE_ID={REQUIRED_SECRETS["NOTION_DATABASE_ID"]}
DEADLETTER_REPLAY_TOKEN={REQUIRED_SECRETS["DEADLETTER_REPLAY_TOKEN"]}
"""

    config_script = f"""
cd {APP_DIR}
cat > .env << 'ENVEOF'
{env_content.strip()}
ENVEOF
mkdir -p data logs
echo "✅ 环境配置完成"
"""

    cmd = f"ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} '{config_script}'"
    return run_command(cmd, "配置环境", timeout=30)


def initialize_database():
    """初始化数据库"""
    print("🗄️ 初始化数据库...")

    db_script = f"""
cd {APP_DIR}
python3 -c "
import sys
sys.path.insert(0, '.')
from app.models import init_db
init_db()
print('✅ 数据库初始化成功')
"
echo "✅ 数据库初始化完成"
"""

    cmd = f"ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} '{db_script}'"
    return run_command(cmd, "初始化数据库", timeout=30)


def create_systemd_service():
    """创建 systemd 服务"""
    print("🔧 创建 systemd 服务...")

    service_content = f"""[Unit]
Description=GitHub-Notion Sync Service
After=network.target

[Service]
Type=simple
User={AWS_USER}
WorkingDirectory={APP_DIR}
Environment=PATH=/home/{AWS_USER}/.local/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile={APP_DIR}/.env
ExecStart=/home/{AWS_USER}/.local/bin/uvicorn app.server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target"""

    service_script = f"""
sudo tee /etc/systemd/system/{SERVICE_NAME}.service > /dev/null << 'SERVICEEOF'
{service_content}
SERVICEEOF
sudo systemctl daemon-reload
sudo systemctl enable {SERVICE_NAME}
echo "✅ systemd 服务创建完成"
"""

    cmd = f"ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} '{service_script}'"
    return run_command(cmd, "创建 systemd 服务", timeout=30)


def start_service():
    """启动服务"""
    print("🚀 启动服务...")

    start_script = f"""
sudo systemctl start {SERVICE_NAME}
sleep 15
sudo systemctl status {SERVICE_NAME} --no-pager
ps aux | grep uvicorn | grep -v grep || echo "⚠️ 未找到进程"
sudo netstat -tlnp | grep :8000 || echo "⚠️ 端口未监听"
echo "✅ 服务启动完成"
"""

    cmd = f"ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} '{start_script}'"
    return run_command(cmd, "启动服务", timeout=45)


def verify_deployment():
    """验证部署"""
    print("🧪 验证部署...")

    # 等待服务完全启动
    time.sleep(20)

    # 测试健康检查
    for i in range(5):
        try:
            response = requests.get(f"http://{AWS_SERVER}:8000/health", timeout=10)
            if response.status_code == 200:
                print("✅ 健康检查通过")
                health_data = response.json()
                print(f"   状态: {health_data.get('status', 'unknown')}")
                print(f"   环境: {health_data.get('environment', 'unknown')}")
                return True
            else:
                print(f"❌ 健康检查失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ 连接失败: {e}")

        if i < 4:
            print(f"   重试 {i+1}/5...")
            time.sleep(10)

    return False


def main():
    """主函数"""
    print("🚀 开始本地到 AWS 的直接部署...")
    print("=" * 60)

    # 检查前置条件
    if not check_ssh_key():
        return False

    if not test_ssh_connection():
        print("❌ SSH 连接失败，请检查网络和密钥配置")
        return False

    # 执行部署步骤
    steps = [
        ("清理服务器", cleanup_server),
        ("安装依赖", install_dependencies),
        ("传输文件", transfer_files),
        ("配置环境", configure_environment),
        ("初始化数据库", initialize_database),
        ("创建服务", create_systemd_service),
        ("启动服务", start_service),
        ("验证部署", verify_deployment),
    ]

    for step_name, step_func in steps:
        print(f"\n📋 执行步骤: {step_name}")
        if not step_func():
            print(f"❌ 步骤失败: {step_name}")
            return False
        print(f"✅ 步骤完成: {step_name}")

    print("\n🎉 AWS 部署成功！")
    print(f"🌐 服务地址: http://{AWS_SERVER}:8000")
    print(f"🏥 健康检查: http://{AWS_SERVER}:8000/health")
    print(f"🔗 GitHub Webhook: http://{AWS_SERVER}:8000/github_webhook")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
