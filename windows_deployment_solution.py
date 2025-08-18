#!/usr/bin/env python3
"""
Windows 服务器部署解决方案
发现服务器可能是 Windows 系统（RDP 端口 3389 开放）
"""

import subprocess
import sys
import time
import requests
import json
from pathlib import Path

AWS_SERVER = "3.35.106.116"

def test_rdp_connection():
    """测试 RDP 连接"""
    print("🖥️ 测试 RDP 连接...")
    
    print("   RDP 端口 3389 已开放")
    print("   可以尝试以下方式连接:")
    print("   1. Windows: 使用 mstsc (远程桌面连接)")
    print("   2. Linux: 使用 rdesktop 或 xfreerdp")
    print("   3. macOS: 使用 Microsoft Remote Desktop")
    
    # 尝试使用 xfreerdp (如果可用)
    try:
        result = subprocess.run("which xfreerdp", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ 找到 xfreerdp，可以尝试连接:")
            print(f"   xfreerdp /v:{AWS_SERVER}:3389 /u:Administrator")
            return True
    except:
        pass
    
    try:
        result = subprocess.run("which rdesktop", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ 找到 rdesktop，可以尝试连接:")
            print(f"   rdesktop {AWS_SERVER}:3389")
            return True
    except:
        pass
    
    print("   ⚠️ 未找到 RDP 客户端，请手动安装或使用图形界面")
    return False

def test_windows_services():
    """测试 Windows 服务"""
    print("🔍 测试 Windows 服务...")
    
    # 测试常见的 Windows 服务端口
    windows_ports = {
        80: "IIS Web Server",
        443: "IIS HTTPS",
        8000: "Custom Application",
        3389: "Remote Desktop",
        5985: "WinRM HTTP",
        5986: "WinRM HTTPS"
    }
    
    for port, service in windows_ports.items():
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((AWS_SERVER, port))
            sock.close()
            
            if result == 0:
                print(f"   ✅ {service} (端口 {port}) - 开放")
            else:
                print(f"   ❌ {service} (端口 {port}) - 关闭")
        except Exception as e:
            print(f"   ❓ {service} (端口 {port}) - 检查失败: {e}")

def test_web_interface():
    """测试 Web 管理界面"""
    print("🌐 测试 Web 管理界面...")
    
    # 常见的 Web 管理路径
    web_paths = [
        "/",
        "/admin",
        "/manager",
        "/console",
        "/dashboard",
        "/iisadmin",
        "/remote"
    ]
    
    for path in web_paths:
        for protocol in ["http", "https"]:
            url = f"{protocol}://{AWS_SERVER}{path}"
            try:
                response = requests.get(url, timeout=5, verify=False)
                print(f"   ✅ {url} - HTTP {response.status_code}")
                
                # 检查是否是管理界面
                content = response.text.lower()
                if any(keyword in content for keyword in ["login", "admin", "管理", "console"]):
                    print(f"      🎯 可能的管理界面")
                    
            except requests.exceptions.SSLError:
                print(f"   ⚠️ {url} - SSL 错误")
            except requests.exceptions.ConnectTimeout:
                print(f"   ❌ {url} - 连接超时")
            except requests.exceptions.ConnectionError:
                print(f"   ❌ {url} - 连接失败")
            except Exception as e:
                print(f"   ❓ {url} - 异常: {e}")

def try_winrm_connection():
    """尝试 WinRM 连接"""
    print("⚡ 尝试 WinRM 连接...")
    
    try:
        # 检查是否安装了 pywinrm
        import winrm
        
        # 尝试连接
        session = winrm.Session(f'http://{AWS_SERVER}:5985/wsman', auth=('Administrator', ''))
        result = session.run_cmd('echo "WinRM 连接成功"')
        
        if result.status_code == 0:
            print("   ✅ WinRM 连接成功")
            return True
        else:
            print(f"   ❌ WinRM 连接失败: {result.std_err}")
            
    except ImportError:
        print("   ⚠️ pywinrm 未安装，可以尝试安装: pip install pywinrm")
    except Exception as e:
        print(f"   ❌ WinRM 连接异常: {e}")
    
    return False

def create_windows_deployment_script():
    """创建 Windows 部署脚本"""
    print("📝 创建 Windows 部署脚本...")
    
    # PowerShell 部署脚本
    powershell_script = '''
# GitHub-Notion 同步服务 Windows 部署脚本

Write-Host "🚀 开始 Windows 部署..." -ForegroundColor Green

# 检查 Python
Write-Host "🐍 检查 Python 环境..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python 未安装，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 检查 pip
Write-Host "📦 检查 pip..." -ForegroundColor Yellow
python -m pip --version

# 创建应用目录
$AppDir = "C:\\github-notion-sync"
Write-Host "📁 创建应用目录: $AppDir" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $AppDir
Set-Location $AppDir

# 停止现有服务
Write-Host "⏹️ 停止现有服务..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*uvicorn*"} | Stop-Process -Force
netstat -ano | findstr :8000 | ForEach-Object {
    $processId = ($_ -split '\s+')[-1]
    if ($processId -ne "0") {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}

# 安装依赖
Write-Host "📦 安装 Python 依赖..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn[standard] pydantic sqlalchemy python-dotenv httpx requests

# 创建环境配置
Write-Host "⚙️ 创建环境配置..." -ForegroundColor Yellow
$envContent = @"
ENVIRONMENT=production
DB_URL=sqlite:///./data/app.db
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=100
MAX_REQUEST_SIZE=2097152
DISABLE_NOTION=false
GITHUB_WEBHOOK_SECRET=7a0f7d8a1b968a26275206e7ded245849207a302651eed1ef5b965dad931c518
"@
$envContent | Out-File -FilePath ".env" -Encoding UTF8

# 创建数据目录
New-Item -ItemType Directory -Force -Path "data"
New-Item -ItemType Directory -Force -Path "logs"

# 创建启动脚本
Write-Host "🚀 创建启动脚本..." -ForegroundColor Yellow
$startScript = @"
@echo off
cd /d C:\github-notion-sync
python -m uvicorn app.server:app --host 0.0.0.0 --port 8000
"@
$startScript | Out-File -FilePath "start_service.bat" -Encoding ASCII

# 创建 Windows 服务（可选）
Write-Host "🔧 创建 Windows 服务..." -ForegroundColor Yellow
$serviceScript = @"
import win32serviceutil
import win32service
import win32event
import subprocess
import os

class GitHubNotionService(win32serviceutil.ServiceFramework):
    _svc_name_ = "GitHubNotionSync"
    _svc_display_name_ = "GitHub-Notion Sync Service"
    _svc_description_ = "GitHub-Notion 双向同步服务"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.process:
            self.process.terminate()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        os.chdir(r"C:\github-notion-sync")
        self.process = subprocess.Popen([
            "python", "-m", "uvicorn", "app.server:app", 
            "--host", "0.0.0.0", "--port", "8000"
        ])
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(GitHubNotionService)
"@
$serviceScript | Out-File -FilePath "windows_service.py" -Encoding UTF8

Write-Host "✅ Windows 部署脚本创建完成" -ForegroundColor Green
Write-Host "📋 下一步:" -ForegroundColor Yellow
Write-Host "1. 将应用文件复制到 $AppDir" -ForegroundColor White
Write-Host "2. 运行: .\\start_service.bat" -ForegroundColor White
Write-Host "3. 或安装为 Windows 服务: python windows_service.py install" -ForegroundColor White
'''
    
    with open("deploy_windows.ps1", "w", encoding="utf-8") as f:
        f.write(powershell_script)
    
    print("   ✅ 已创建 Windows PowerShell 部署脚本: deploy_windows.ps1")
    
    # 创建批处理脚本
    batch_script = '''@echo off
echo 🚀 GitHub-Notion Windows 部署
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 管理员权限确认
) else (
    echo ❌ 需要管理员权限，请以管理员身份运行
    pause
    exit /b 1
)

REM 执行 PowerShell 脚本
powershell -ExecutionPolicy Bypass -File deploy_windows.ps1

pause
'''
    
    with open("deploy_windows.bat", "w", encoding="utf-8") as f:
        f.write(batch_script)
    
    print("   ✅ 已创建 Windows 批处理部署脚本: deploy_windows.bat")
    return True

def main():
    """主函数"""
    print("🖥️ Windows 服务器部署解决方案")
    print("=" * 50)
    
    print("🔍 服务器分析:")
    print(f"   IP: {AWS_SERVER}")
    print("   开放端口: 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (App), 3389 (RDP)")
    print("   推测: Windows 服务器 (RDP 端口开放)")
    
    # 执行各种测试
    tests = [
        ("Windows 服务检测", test_windows_services),
        ("Web 界面检测", test_web_interface),
        ("RDP 连接测试", test_rdp_connection),
        ("WinRM 连接测试", try_winrm_connection),
        ("创建部署脚本", create_windows_deployment_script)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 执行: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
            if result:
                print(f"✅ 完成: {test_name}")
            else:
                print(f"⚠️ 部分完成: {test_name}")
        except Exception as e:
            print(f"❌ 异常: {test_name} - {e}")
            results[test_name] = False
    
    print(f"\n📊 Windows 部署方案总结:")
    print("=" * 50)
    
    print("🎯 推荐的部署方式:")
    print("1. 🖥️ RDP 远程桌面连接 (推荐)")
    print("   - 使用远程桌面连接到服务器")
    print("   - 手动运行部署脚本")
    print("   - 直接管理和监控服务")
    
    print("\n2. ⚡ WinRM 远程管理")
    print("   - 如果 WinRM 可用，可以远程执行命令")
    print("   - 需要正确的认证凭据")
    
    print("\n3. 🌐 Web 管理界面")
    print("   - 如果有 Web 管理界面，可以通过浏览器管理")
    print("   - 检查 http/https 端口的管理页面")
    
    print("\n📝 部署文件已创建:")
    print("   - deploy_windows.ps1 (PowerShell 脚本)")
    print("   - deploy_windows.bat (批处理脚本)")
    
    print("\n🔧 下一步操作:")
    print("1. 获取 Windows 服务器的登录凭据")
    print("2. 使用 RDP 连接到服务器")
    print("3. 将应用文件和部署脚本传输到服务器")
    print("4. 以管理员身份运行 deploy_windows.bat")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
