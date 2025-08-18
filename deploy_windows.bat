@echo off
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
