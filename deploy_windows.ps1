
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
$AppDir = "C:\github-notion-sync"
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
Write-Host "2. 运行: .\start_service.bat" -ForegroundColor White
Write-Host "3. 或安装为 Windows 服务: python windows_service.py install" -ForegroundColor White
