#!/usr/bin/env python3
"""
现代化 AWS 部署脚本
支持 Docker 容器化部署、零停机更新、回滚等功能
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# 配置
AWS_SERVER = "3.35.106.116"
AWS_USER = "ubuntu"
SSH_KEY_PATH = "~/.ssh/aws-key.pem"
DOCKER_REGISTRY = "ghcr.io/xupeng211/github-notion"


class ModernDeployer:
    def __init__(self, environment="production", dry_run=False):
        self.environment = environment
        self.dry_run = dry_run
        self.deployment_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def run_command(self, cmd, description="", timeout=60):
        """执行命令"""
        self.log(f"🔧 {description}")
        self.log(f"   命令: {cmd}")

        if self.dry_run:
            self.log("   [DRY RUN] 跳过执行")
            return True

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                self.log("   ✅ 成功")
                if result.stdout.strip():
                    self.log(f"   输出: {result.stdout.strip()}")
                return True
            else:
                self.log(f"   ❌ 失败 (退出码: {result.returncode})", "ERROR")
                if result.stderr.strip():
                    self.log(f"   错误: {result.stderr.strip()}", "ERROR")
                return False
        except subprocess.TimeoutExpired:
            self.log("   ⏰ 超时", "ERROR")
            return False
        except Exception as e:
            self.log(f"   ❌ 异常: {e}", "ERROR")
            return False

    def run_ssh_command(self, cmd, description="", timeout=60):
        """在远程服务器执行命令"""
        ssh_cmd = f'ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} "{cmd}"'
        return self.run_command(ssh_cmd, description, timeout)

    def check_prerequisites(self):
        """检查部署前提条件"""
        self.log("🔍 检查部署前提条件...")

        # 检查 SSH 密钥
        ssh_key = Path(SSH_KEY_PATH).expanduser()
        if not ssh_key.exists():
            self.log(f"❌ SSH 密钥不存在: {SSH_KEY_PATH}", "ERROR")
            return False

        # 检查 SSH 连接
        if not self.run_ssh_command("echo 'SSH 连接测试'", "测试 SSH 连接", 10):
            return False

        # 检查 Docker
        if not self.run_ssh_command("docker --version", "检查 Docker", 10):
            self.log("🐳 安装 Docker...")
            if not self.install_docker():
                return False

        # 检查 Docker Compose
        if not self.run_ssh_command("docker-compose --version", "检查 Docker Compose", 10):
            self.log("🐳 安装 Docker Compose...")
            if not self.install_docker_compose():
                return False

        self.log("✅ 前提条件检查完成")
        return True

    def install_docker(self):
        """安装 Docker"""
        install_script = """
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        sudo systemctl enable docker
        sudo systemctl start docker
        """
        return self.run_ssh_command(install_script, "安装 Docker", 300)

    def install_docker_compose(self):
        """安装 Docker Compose"""
        install_script = """
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        """
        return self.run_ssh_command(install_script, "安装 Docker Compose", 120)

    def backup_current_deployment(self):
        """备份当前部署"""
        self.log("💾 备份当前部署...")

        backup_script = f"""
        cd /opt/github-notion-sync

        # 创建备份目录
        sudo mkdir -p /opt/backups/{self.deployment_id}

        # 备份数据
        sudo cp -r data /opt/backups/{self.deployment_id}/ 2>/dev/null || true

        # 备份配置
        sudo cp .env /opt/backups/{self.deployment_id}/ 2>/dev/null || true
        sudo cp docker-compose.yml /opt/backups/{self.deployment_id}/ 2>/dev/null || true

        # 记录当前运行的容器
        docker ps --format "table {{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}" > /opt/backups/{self.deployment_id}/containers.txt

        echo "备份完成: /opt/backups/{self.deployment_id}"
        """

        return self.run_ssh_command(backup_script, "备份当前部署", 60)

    def deploy_application(self):
        """部署应用"""
        self.log("🚀 开始应用部署...")

        # 传输部署文件
        if not self.transfer_files():
            return False

        # 拉取最新镜像
        if not self.pull_images():
            return False

        # 零停机部署
        if not self.zero_downtime_deploy():
            return False

        return True

    def transfer_files(self):
        """传输部署文件"""
        self.log("📤 传输部署文件...")

        # 创建应用目录
        if not self.run_ssh_command(
            "sudo mkdir -p /opt/github-notion-sync && sudo chown ubuntu:ubuntu /opt/github-notion-sync", "创建应用目录"
        ):
            return False

        # 传输文件
        files_to_transfer = ["docker-compose.prod.yml", ".env", "nginx/", "monitoring/", "scripts/"]

        for file_path in files_to_transfer:
            if Path(file_path).exists():
                if Path(file_path).is_dir():
                    cmd = f"scp -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no -r {file_path} {AWS_USER}@{AWS_SERVER}:/opt/github-notion-sync/"
                else:
                    cmd = f"scp -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no {file_path} {AWS_USER}@{AWS_SERVER}:/opt/github-notion-sync/"

                if not self.run_command(cmd, f"传输 {file_path}", 60):
                    self.log(f"⚠️ 传输 {file_path} 失败，继续...", "WARNING")

        return True

    def pull_images(self):
        """拉取 Docker 镜像"""
        self.log("📥 拉取 Docker 镜像...")

        pull_script = f"""
        cd /opt/github-notion-sync

        # 登录到 GitHub Container Registry
        echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin

        # 拉取最新镜像
        docker pull {DOCKER_REGISTRY}:latest

        # 清理旧镜像
        docker image prune -f
        """

        return self.run_ssh_command(pull_script, "拉取 Docker 镜像", 300)

    def zero_downtime_deploy(self):
        """零停机部署"""
        self.log("🔄 执行零停机部署...")

        deploy_script = f"""
        cd /opt/github-notion-sync

        # 使用生产配置
        cp docker-compose.prod.yml docker-compose.yml

        # 启动新容器（蓝绿部署）
        docker-compose up -d --no-deps app

        # 等待新容器启动
        sleep 30

        # 健康检查
        for i in {{1..10}}; do
            if curl -f http://localhost:8000/health > /dev/null 2>&1; then
                echo "健康检查通过"
                break
            fi
            echo "等待服务启动... ($i/10)"
            sleep 10
        done

        # 最终健康检查
        if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "健康检查失败，回滚部署"
            exit 1
        fi

        # 清理旧容器
        docker system prune -f

        echo "部署成功"
        """

        return self.run_ssh_command(deploy_script, "零停机部署", 300)

    def verify_deployment(self):
        """验证部署"""
        self.log("🧪 验证部署...")

        # 等待服务完全启动
        time.sleep(30)

        # 外部健康检查
        try:
            response = requests.get(f"http://{AWS_SERVER}:8000/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                self.log("✅ 外部健康检查通过")
                self.log(f"   状态: {health_data.get('status', 'unknown')}")
                self.log(f"   环境: {health_data.get('environment', 'unknown')}")
                return True
            else:
                self.log(f"❌ 健康检查失败: HTTP {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ 健康检查异常: {e}", "ERROR")

        return False

    def rollback(self, backup_id=None):
        """回滚部署"""
        if not backup_id:
            backup_id = self.deployment_id

        self.log(f"🔙 回滚到备份: {backup_id}")

        rollback_script = f"""
        cd /opt/github-notion-sync

        # 停止当前服务
        docker-compose down

        # 恢复备份
        sudo cp -r /opt/backups/{backup_id}/data . 2>/dev/null || true
        sudo cp /opt/backups/{backup_id}/.env . 2>/dev/null || true
        sudo cp /opt/backups/{backup_id}/docker-compose.yml . 2>/dev/null || true

        # 重新启动服务
        docker-compose up -d

        echo "回滚完成"
        """

        return self.run_ssh_command(rollback_script, "执行回滚", 120)

    def deploy(self):
        """主部署流程"""
        self.log(f"🚀 开始现代化部署 (环境: {self.environment}, 部署ID: {self.deployment_id})")

        try:
            # 检查前提条件
            if not self.check_prerequisites():
                self.log("❌ 前提条件检查失败", "ERROR")
                return False

            # 备份当前部署
            if not self.backup_current_deployment():
                self.log("❌ 备份失败", "ERROR")
                return False

            # 部署应用
            if not self.deploy_application():
                self.log("❌ 部署失败，开始回滚", "ERROR")
                self.rollback()
                return False

            # 验证部署
            if not self.verify_deployment():
                self.log("❌ 部署验证失败，开始回滚", "ERROR")
                self.rollback()
                return False

            self.log("🎉 部署成功完成！")
            self.log(f"🌐 服务地址: http://{AWS_SERVER}:8000")
            self.log(f"🏥 健康检查: http://{AWS_SERVER}:8000/health")
            return True

        except Exception as e:
            self.log(f"❌ 部署过程中发生异常: {e}", "ERROR")
            self.rollback()
            return False


def main():
    parser = argparse.ArgumentParser(description="现代化 AWS 部署脚本")
    parser.add_argument(
        "--environment", "-e", default="production", choices=["development", "staging", "production"], help="部署环境"
    )
    parser.add_argument("--dry-run", action="store_true", help="干运行模式")
    parser.add_argument("--rollback", help="回滚到指定备份ID")

    args = parser.parse_args()

    deployer = ModernDeployer(environment=args.environment, dry_run=args.dry_run)

    if args.rollback:
        success = deployer.rollback(args.rollback)
    else:
        success = deployer.deploy()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
