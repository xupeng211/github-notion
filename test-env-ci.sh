#!/bin/bash
# 完整的CI/CD环境模拟测试脚本
# 模拟GitHub Actions中的完整构建和测试流程

set -e

echo "🚀 完整CI/CD环境模拟测试"
echo "============================================"

# CI/CD 环境变量设置（模拟GitHub Actions）
export DISABLE_METRICS="0"
export DISABLE_NOTION="1"
export GITEE_WEBHOOK_SECRET="secure-test-secret-for-local-ci-testing-12345678"
export GITHUB_WEBHOOK_SECRET="secure-test-secret-for-local-ci-testing-12345678"
export DEADLETTER_REPLAY_TOKEN="secure-deadletter-replay-token-for-testing-12345678"
export DB_URL="sqlite:///data/sync.db"
export LOG_LEVEL="INFO"
export APP_PORT="8000"

echo "📋 阶段1: 环境准备"
echo "----------------------------"
echo "✅ Python版本: $(python3 --version)"
echo "✅ 环境变量配置完成"

echo ""
echo "📋 阶段2: 依赖安装测试"
echo "----------------------------"
pip install -r requirements.txt > /dev/null 2>&1
echo "✅ 依赖安装成功"

echo ""
echo "📋 阶段3: 代码质量检查"
echo "----------------------------"
flake8 app/ --max-line-length=120 --ignore=E203,W503,E127,E128 --exclude=__pycache__,*.pyc
echo "✅ 代码风格检查通过"

echo ""
echo "📋 阶段4: 应用启动测试"
echo "----------------------------"
python3 -c "
from app.server import app
print('✅ 应用模块导入成功')

from app.config_validator import ConfigValidator
validator = ConfigValidator()
result = validator.validate_all()
if result.is_valid:
    print('✅ 配置验证通过')
else:
    print('❌ 配置验证失败')
    for error in result.errors:
        print(f'  - {error}')
    exit(1)
"

echo ""
echo "📋 阶段5: 服务器功能测试"
echo "----------------------------"
# 启动服务器进行功能测试
python3 -m uvicorn app.server:app --host 127.0.0.1 --port 8007 &
SERVER_PID=$!

sleep 6

# 测试关键端点
echo "🧪 测试健康检查端点..."
if curl -f http://127.0.0.1:8007/health >/dev/null 2>&1; then
    echo "✅ 健康检查通过"
else
    echo "❌ 健康检查失败"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

echo "🧪 测试指标端点..."
if curl -f http://127.0.0.1:8007/metrics >/dev/null 2>&1; then
    echo "✅ 指标端点正常"
else
    echo "❌ 指标端点失败"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# 停止服务器
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo ""
echo "📋 阶段6: 指标系统验证"
echo "----------------------------"
python3 -c "
import requests
import subprocess
import time
import sys
import os

# 启动应用
proc = subprocess.Popen([
    sys.executable, '-m', 'uvicorn', 'app.server:app',
    '--host', '127.0.0.1', '--port', '8008'
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    time.sleep(5)
    response = requests.get('http://127.0.0.1:8008/metrics', timeout=5)

    if 'deadletter_queue_size_basic' in response.text and 'deadletter_queue_size_by_provider' in response.text:
        print('✅ 死信队列指标无冲突')
    else:
        print('❌ 指标系统有问题')
        sys.exit(1)

finally:
    proc.terminate()
    proc.wait()
"

echo ""
echo "🎉 完整CI/CD环境模拟测试通过！"
echo "============================================"
echo "✅ 所有阶段都已成功完成"
echo "✅ 应用在CI/CD环境中可以正常运行"
echo "✅ 准备推送到远程仓库触发真实CI/CD"
echo ""
echo "📊 测试总结:"
echo "  - 环境配置: ✅"
echo "  - 依赖管理: ✅"
echo "  - 代码质量: ✅"
echo "  - 应用启动: ✅"
echo "  - API端点: ✅"
echo "  - 指标系统: ✅"
echo ""
echo "🚀 可以安全推送代码了！"
