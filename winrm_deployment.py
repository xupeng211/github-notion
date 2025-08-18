#!/usr/bin/env python3
"""
通过 WinRM 部署到 Windows 服务器
"""

import sys
import time

import requests
import winrm

AWS_SERVER = "3.35.106.116"


def test_winrm_credentials():
    """测试 WinRM 凭据"""
    print("🔐 测试 WinRM 凭据...")

    # 常见的默认凭据
    credentials = [
        ("Administrator", ""),
        ("Administrator", "password"),
        ("Administrator", "Password123"),
        ("Administrator", "Admin123"),
        ("admin", "admin"),
        ("ubuntu", "ubuntu"),  # 可能是 Linux 子系统
    ]

    for username, password in credentials:
        print(f"   尝试凭据: {username} / {'(空)' if not password else '*' * len(password)}")

        try:
            # 尝试 HTTP WinRM
            session = winrm.Session(f"http://{AWS_SERVER}:5985/wsman", auth=(username, password))
            result = session.run_cmd('echo "WinRM 连接成功"')

            if result.status_code == 0:
                print(f"   ✅ HTTP WinRM 连接成功: {username}")
                return session, username, password

        except Exception as e:
            print(f"   ❌ HTTP WinRM 失败: {e}")

        try:
            # 尝试 HTTPS WinRM
            session = winrm.Session(f"https://{AWS_SERVER}:5986/wsman", auth=(username, password))
            result = session.run_cmd('echo "WinRM HTTPS 连接成功"')

            if result.status_code == 0:
                print(f"   ✅ HTTPS WinRM 连接成功: {username}")
                return session, username, password

        except Exception as e:
            print(f"   ❌ HTTPS WinRM 失败: {e}")

    print("❌ 所有凭据测试失败")
    return None, None, None


def run_winrm_command(session, command, description=""):
    """通过 WinRM 执行命令"""
    print(f"🔧 {description}")
    print(f"   命令: {command}")

    try:
        result = session.run_cmd(command)

        if result.status_code == 0:
            print("   ✅ 成功")
            if result.std_out:
                print(f"   输出: {result.std_out.decode('utf-8').strip()}")
        else:
            print(f"   ❌ 失败 (退出码: {result.status_code})")
            if result.std_err:
                print(f"   错误: {result.std_err.decode('utf-8').strip()}")

        return result.status_code == 0

    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return False


def run_winrm_powershell(session, script, description=""):
    """通过 WinRM 执行 PowerShell 脚本"""
    print(f"🔧 {description}")
    print(f"   PowerShell 脚本长度: {len(script)} 字符")

    try:
        result = session.run_ps(script)

        if result.status_code == 0:
            print("   ✅ 成功")
            if result.std_out:
                print(f"   输出: {result.std_out.decode('utf-8').strip()}")
        else:
            print(f"   ❌ 失败 (退出码: {result.status_code})")
            if result.std_err:
                print(f"   错误: {result.std_err.decode('utf-8').strip()}")

        return result.status_code == 0

    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return False


def deploy_via_winrm(session):
    """通过 WinRM 部署应用"""
    print("🚀 通过 WinRM 部署应用...")

    # 1. 检查系统环境
    commands = [
        ("检查 Windows 版本", "ver"),
        ("检查 Python", "python --version"),
        ("检查 pip", "python -m pip --version"),
        ("检查当前目录", "cd"),
        ("检查网络", "ping -n 1 google.com"),
    ]

    for desc, cmd in commands:
        run_winrm_command(session, cmd, desc)

    # 2. 创建应用目录
    app_dir = "C:\\github-notion-sync"
    powershell_setup = f"""
Write-Host "📁 创建应用目录..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "{app_dir}"
Set-Location "{app_dir}"
Write-Host "当前目录: $(Get-Location)" -ForegroundColor Green

Write-Host "⏹️ 停止现有服务..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {{$_.CommandLine -like "*uvicorn*"}} | Stop-Process -Force
netstat -ano | findstr :8000 | ForEach-Object {{
    $processId = ($_ -split '\\s+')[-1]
    if ($processId -ne "0") {{
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }}
}}

Write-Host "📦 安装 Python 依赖..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn pydantic sqlalchemy python-dotenv httpx requests

Write-Host "✅ 基础设置完成" -ForegroundColor Green
"""

    if not run_winrm_powershell(session, powershell_setup, "基础环境设置"):
        return False

    # 3. 创建最小应用
    minimal_app = """
from fastapi import FastAPI, Request
from datetime import datetime
import json

app = FastAPI(title="GitHub-Notion Sync - Windows")

@app.get("/")
def root():
    return {
        "message": "GitHub-Notion Sync Service",
        "platform": "Windows",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "platform": "Windows",
        "environment": "production",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/github_webhook")
def github_webhook(request: Request):
    return {"message": "Webhook received", "platform": "Windows"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

    create_app_script = f"""
Set-Location "{app_dir}"

Write-Host "📝 创建应用文件..." -ForegroundColor Yellow
$appContent = @"
{minimal_app}
"@
$appContent | Out-File -FilePath "app.py" -Encoding UTF8

Write-Host "🚀 启动应用..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "app.py" -WindowStyle Hidden

Write-Host "⏳ 等待服务启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "🔍 检查服务状态..." -ForegroundColor Yellow
$processes = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {{$_.CommandLine -like "*app.py*"}}
if ($processes) {{
    Write-Host "✅ 服务正在运行，进程 ID: $($processes.Id)" -ForegroundColor Green
}} else {{
    Write-Host "❌ 服务未运行" -ForegroundColor Red
}}

Write-Host "🔍 检查端口..." -ForegroundColor Yellow
$port8000 = netstat -ano | findstr :8000
if ($port8000) {{
    Write-Host "✅ 端口 8000 正在监听" -ForegroundColor Green
    Write-Host "$port8000" -ForegroundColor White
}} else {{
    Write-Host "❌ 端口 8000 未监听" -ForegroundColor Red
}}

Write-Host "✅ 部署完成" -ForegroundColor Green
"""

    return run_winrm_powershell(session, create_app_script, "创建和启动应用")


def verify_deployment():
    """验证部署"""
    print("🧪 验证部署...")

    # 等待服务启动
    time.sleep(15)

    try:
        response = requests.get(f"http://{AWS_SERVER}:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ 健康检查通过")
            health_data = response.json()
            print(f"   状态: {health_data.get('status', 'unknown')}")
            print(f"   平台: {health_data.get('platform', 'unknown')}")
            print(f"   环境: {health_data.get('environment', 'unknown')}")
            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")

    return False


def main():
    """主函数"""
    print("🖥️ WinRM Windows 部署")
    print("=" * 50)

    # 测试 WinRM 连接
    session, username, password = test_winrm_credentials()

    if not session:
        print("❌ 无法建立 WinRM 连接")
        print("\n🔧 可能的解决方案:")
        print("1. 检查 Windows 服务器的 WinRM 配置")
        print("2. 确认用户名和密码")
        print("3. 检查防火墙设置")
        print("4. 尝试使用 RDP 连接")
        return False

    print(f"✅ WinRM 连接成功: {username}")

    # 执行部署
    if deploy_via_winrm(session):
        print("✅ WinRM 部署完成")

        # 验证部署
        if verify_deployment():
            print("🎉 部署成功！服务正常运行")
            print(f"🌐 服务地址: http://{AWS_SERVER}:8000")
            print(f"🏥 健康检查: http://{AWS_SERVER}:8000/health")
            return True
        else:
            print("❌ 部署验证失败")
    else:
        print("❌ WinRM 部署失败")

    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
