#!/usr/bin/env python3
"""
测试 AWS 连接和基本部署能力
"""

import subprocess
import sys
from pathlib import Path

import requests

AWS_SERVER = "3.35.106.116"
AWS_USER = "ubuntu"


def run_command(cmd, description="", timeout=30):
    """执行命令并显示结果"""
    print(f"🔧 {description}")
    print(f"   命令: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
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


def test_basic_connection():
    """测试基本网络连接"""
    print("🌐 测试基本网络连接...")

    # 测试 ping
    cmd = f"ping -c 3 {AWS_SERVER}"
    return run_command(cmd, "Ping 测试", timeout=15)


def test_ssh_connection():
    """测试 SSH 连接"""
    print("🔐 测试 SSH 连接...")

    # 检查 SSH 密钥
    ssh_key_path = Path.home() / ".ssh" / "aws-key.pem"
    if not ssh_key_path.exists():
        print("❌ SSH 密钥不存在: ~/.ssh/aws-key.pem")
        print("请将 AWS 私钥保存到该位置")
        return False

    # 设置权限
    run_command(f"chmod 600 {ssh_key_path}", "设置 SSH 密钥权限")

    # 测试连接
    cmd = f"ssh -i ~/.ssh/aws-key.pem -o ConnectTimeout=10 -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} \"echo 'SSH 连接成功'\""
    return run_command(cmd, "SSH 连接测试", timeout=15)


def test_server_environment():
    """测试服务器环境"""
    print("🖥️ 测试服务器环境...")

    env_script = """
echo "=== 系统信息 ==="
uname -a
echo "=== Python 版本 ==="
python3 --version
echo "=== 磁盘空间 ==="
df -h /
echo "=== 内存信息 ==="
free -h
echo "=== 网络状态 ==="
sudo netstat -tlnp | grep :8000 || echo "端口 8000 空闲"
echo "=== 当前进程 ==="
ps aux | grep uvicorn | grep -v grep || echo "没有 uvicorn 进程"
"""

    cmd = f"ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} '{env_script}'"
    return run_command(cmd, "检查服务器环境", timeout=30)


def test_python_environment():
    """测试 Python 环境"""
    print("🐍 测试 Python 环境...")

    python_script = """
echo "=== Python 路径 ==="
which python3
echo "=== pip 版本 ==="
python3 -m pip --version
echo "=== 已安装包 ==="
python3 -m pip list | grep -E "(fastapi|uvicorn|sqlalchemy)" || echo "核心包未安装"
echo "=== 测试导入 ==="
python3 -c "
try:
    import fastapi
    print('✅ FastAPI 可用')
except ImportError:
    print('❌ FastAPI 不可用')

try:
    import uvicorn
    print('✅ Uvicorn 可用')
except ImportError:
    print('❌ Uvicorn 不可用')

try:
    import sqlalchemy
    print('✅ SQLAlchemy 可用')
except ImportError:
    print('❌ SQLAlchemy 不可用')
"
"""

    cmd = f"ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} '{python_script}'"
    return run_command(cmd, "检查 Python 环境", timeout=30)


def test_minimal_service():
    """测试最小服务"""
    print("🧪 测试最小服务...")

    # 创建最小测试应用
    minimal_app = """
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/")
def root():
    return {"message": "AWS 测试服务", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health")
def health():
    return {"status": "ok", "server": "aws", "timestamp": datetime.utcnow().isoformat()}
"""

    service_script = f"""
cd /tmp
cat > test_app.py << 'APPEOF'
{minimal_app}
APPEOF

echo "启动测试服务..."
python3 -m pip install --user fastapi uvicorn --quiet
nohup /home/{AWS_USER}/.local/bin/uvicorn test_app:app --host 0.0.0.0 --port 8000 > test_service.log 2>&1 &
sleep 10

echo "检查服务状态..."
ps aux | grep uvicorn | grep -v grep || echo "服务未启动"
sudo netstat -tlnp | grep :8000 || echo "端口未监听"

echo "测试连接..."
curl -f http://localhost:8000/health || echo "连接失败"

echo "停止测试服务..."
pkill -f "uvicorn test_app" || true
"""

    cmd = f"ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no {AWS_USER}@{AWS_SERVER} '{service_script}'"
    return run_command(cmd, "测试最小服务", timeout=60)


def test_external_access():
    """测试外部访问"""
    print("🌍 测试外部访问...")

    try:
        response = requests.get(f"http://{AWS_SERVER}:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ 外部访问成功")
            print(f"   响应: {response.json()}")
            return True
        else:
            print(f"❌ 外部访问失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ 外部访问异常: {e}")

    return False


def main():
    """主函数"""
    print("🧪 AWS 连接和环境测试")
    print("=" * 50)

    tests = [
        ("基本网络连接", test_basic_connection),
        ("SSH 连接", test_ssh_connection),
        ("服务器环境", test_server_environment),
        ("Python 环境", test_python_environment),
        ("最小服务", test_minimal_service),
        ("外部访问", test_external_access),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n📋 执行测试: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
            if result:
                print(f"✅ 测试通过: {test_name}")
            else:
                print(f"❌ 测试失败: {test_name}")
        except Exception as e:
            print(f"❌ 测试异常: {test_name} - {e}")
            results[test_name] = False

    print("\n📊 测试结果总结:")
    print("=" * 50)

    passed = 0
    total = len(tests)

    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n📈 总体结果: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！AWS 环境就绪")
        return True
    elif passed >= total * 0.7:
        print("⚠️ 大部分测试通过，可以尝试部署")
        return True
    else:
        print("❌ 多个测试失败，需要修复环境问题")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
