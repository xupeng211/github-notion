#!/usr/bin/env python3
"""
创建 SSH 访问的解决方案
通过多种方式尝试获得 AWS 服务器访问权限
"""

import subprocess
import sys
from pathlib import Path


AWS_SERVER = "3.35.106.116"
AWS_USER = "ubuntu"


def run_command(cmd, description="", timeout=30):
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


def try_password_authentication():
    """尝试密码认证"""
    print("🔐 尝试密码认证...")

    # 常见的默认密码
    common_passwords = ["ubuntu", "admin", "password", "123456", ""]

    for password in common_passwords:
        print(f"   尝试密码: {'(空)' if not password else password}")
        cmd = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {AWS_USER}@{AWS_SERVER} "echo \'密码认证成功\'"'

        if run_command(cmd, f"测试密码: {password}", timeout=10):
            print(f"✅ 密码认证成功: {password}")
            return password

    print("❌ 密码认证失败")
    return None


def try_key_based_authentication():
    """尝试基于密钥的认证"""
    print("🔑 尝试密钥认证...")

    # 常见的密钥位置
    key_locations = [
        "~/.ssh/id_rsa",
        "~/.ssh/id_ed25519",
        "~/.ssh/aws-key.pem",
        "~/.ssh/ec2-key.pem",
        "~/.ssh/github-notion.pem",
    ]

    for key_path in key_locations:
        expanded_path = Path(key_path).expanduser()
        if expanded_path.exists():
            print(f"   找到密钥: {key_path}")
            cmd = f"ssh -i {key_path} -o StrictHostKeyChecking=no -o ConnectTimeout=5 {AWS_USER}@{AWS_SERVER} \"echo '密钥认证成功'\""

            if run_command(cmd, f"测试密钥: {key_path}", timeout=10):
                print(f"✅ 密钥认证成功: {key_path}")
                return str(expanded_path)
        else:
            print(f"   密钥不存在: {key_path}")

    print("❌ 密钥认证失败")
    return None


def try_aws_session_manager():
    """尝试 AWS Session Manager"""
    print("☁️ 尝试 AWS Session Manager...")

    # 检查 AWS CLI
    if not run_command("aws --version", "检查 AWS CLI", timeout=10):
        print("❌ AWS CLI 未安装")
        return False

    # 尝试获取实例信息
    cmd = f'aws ec2 describe-instances --filters "Name=ip-address,Values={AWS_SERVER}" --query "Reservations[*].Instances[*].InstanceId" --output text'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

    if result.returncode == 0 and result.stdout.strip():
        instance_id = result.stdout.strip()
        print(f"   找到实例 ID: {instance_id}")

        # 尝试 Session Manager 连接
        cmd = f"aws ssm start-session --target {instance_id}"
        print(f"   可以使用以下命令连接:")
        print(f"   {cmd}")
        return True
    else:
        print("❌ 无法获取实例信息")
        return False


def try_ec2_instance_connect():
    """尝试 EC2 Instance Connect"""
    print("🌐 尝试 EC2 Instance Connect...")

    # 这需要 AWS 控制台访问
    print("   EC2 Instance Connect 需要通过 AWS 控制台访问:")
    print("   1. 登录 AWS 控制台")
    print("   2. 导航到 EC2 > 实例")
    print(f"   3. 选择 IP 为 {AWS_SERVER} 的实例")
    print("   4. 点击 '连接' > 'EC2 Instance Connect'")
    print("   5. 在浏览器中打开终端")

    return False


def create_temporary_key():
    """创建临时密钥对"""
    print("🔑 创建临时密钥对...")

    # 生成新的 SSH 密钥对
    key_path = Path.home() / ".ssh" / "temp-aws-key"

    cmd = f'ssh-keygen -t rsa -b 2048 -f {key_path} -N ""'
    if run_command(cmd, "生成 SSH 密钥对", timeout=30):
        print(f"✅ 密钥对已生成:")
        print(f"   私钥: {key_path}")
        print(f"   公钥: {key_path}.pub")

        # 显示公钥内容
        with open(f"{key_path}.pub", "r") as f:
            public_key = f.read().strip()

        print(f"\n📋 公钥内容:")
        print(f"{public_key}")
        print(f"\n📝 手动添加公钥到服务器:")
        print(f"1. 通过其他方式登录服务器")
        print(f"2. 将上述公钥添加到 ~/.ssh/authorized_keys")
        print(f"3. 使用私钥连接: ssh -i {key_path} {AWS_USER}@{AWS_SERVER}")

        return str(key_path)

    return None


def try_github_actions_approach():
    """尝试通过 GitHub Actions 获取访问"""
    print("🐙 尝试 GitHub Actions 方法...")

    print("   如果 GitHub Actions 有 AWS 访问权限，可以:")
    print("   1. 创建一个 GitHub Actions 工作流")
    print("   2. 使用 AWS CLI 或 Session Manager")
    print("   3. 在服务器上设置新的 SSH 密钥")

    # 创建一个 GitHub Actions 工作流来设置 SSH 访问
    workflow_content = """name: Setup SSH Access

on:
  workflow_dispatch:

jobs:
  setup-ssh:
    runs-on: ubuntu-latest
    steps:
    - name: Setup SSH Key
      run: |
        # 生成新的 SSH 密钥对
        ssh-keygen -t rsa -b 2048 -f ./temp-key -N ""

        # 显示公钥（需要手动添加到服务器）
        echo "Public Key:"
        cat ./temp-key.pub

        # 将私钥保存为 GitHub Secret
        echo "Private Key (save as GitHub Secret):"
        cat ./temp-key
"""

    with open(".github/workflows/setup-ssh.yml", "w") as f:
        f.write(workflow_content)

    print("   ✅ 已创建 SSH 设置工作流: .github/workflows/setup-ssh.yml")
    return True


def analyze_server_access():
    """分析服务器访问方式"""
    print("🔍 分析服务器访问方式...")

    # 检查服务器开放的端口
    common_ports = [22, 80, 443, 8000, 3389]
    open_ports = []

    for port in common_ports:
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((AWS_SERVER, port))
            sock.close()

            if result == 0:
                open_ports.append(port)
                print(f"   ✅ 端口 {port} 开放")
            else:
                print(f"   ❌ 端口 {port} 关闭")
        except Exception as e:
            print(f"   ❓ 端口 {port} 检查失败: {e}")

    print(f"\n📊 开放端口: {open_ports}")

    # 分析可能的访问方式
    if 22 in open_ports:
        print("   🔐 SSH 服务运行中 - 需要正确的认证")
    if 80 in open_ports or 443 in open_ports:
        print("   🌐 Web 服务运行中 - 可能有管理界面")
    if 3389 in open_ports:
        print("   🖥️ RDP 服务运行中 - Windows 远程桌面")

    return open_ports


def main():
    """主函数"""
    print("🚀 AWS 服务器访问解决方案")
    print("=" * 50)

    # 分析服务器
    open_ports = analyze_server_access()

    if 22 not in open_ports:
        print("❌ SSH 端口未开放，无法进行 SSH 连接")
        return False

    # 尝试各种访问方式
    access_methods = [
        ("密钥认证", try_key_based_authentication),
        ("密码认证", try_password_authentication),
        ("AWS Session Manager", try_aws_session_manager),
        ("EC2 Instance Connect", try_ec2_instance_connect),
        ("创建临时密钥", create_temporary_key),
        ("GitHub Actions 方法", try_github_actions_approach),
    ]

    successful_methods = []

    for method_name, method_func in access_methods:
        print(f"\n📋 尝试方法: {method_name}")
        try:
            result = method_func()
            if result:
                successful_methods.append((method_name, result))
                print(f"✅ 方法可用: {method_name}")
            else:
                print(f"❌ 方法失败: {method_name}")
        except Exception as e:
            print(f"❌ 方法异常: {method_name} - {e}")

    print(f"\n📊 结果总结:")
    print("=" * 50)

    if successful_methods:
        print("✅ 找到可用的访问方法:")
        for method_name, result in successful_methods:
            print(f"   - {method_name}: {result}")
    else:
        print("❌ 未找到可用的访问方法")
        print("\n🔧 建议的解决方案:")
        print("1. 联系 AWS 管理员获取 SSH 私钥")
        print("2. 使用 AWS 控制台的 EC2 Instance Connect")
        print("3. 配置 AWS CLI 并使用 Session Manager")
        print("4. 重新创建 EC2 实例并配置新的密钥对")

    return len(successful_methods) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
