#!/bin/bash

# 环境对比脚本 - 比较本地环境与 CI 环境的差异

set -e

echo "🔍 环境对比分析"
echo "==============================================="

echo ""
echo "📊 本地环境信息:"
echo "----------------------------------------"
echo "🐍 Python 版本: $(python --version)"
echo "📍 Python 路径: $(which python)"
echo "🏠 虚拟环境: ${VIRTUAL_ENV:-'未激活'}"
echo "💻 操作系统: $(uname -a)"
echo "📦 pip 版本: $(pip --version)"

echo ""
echo "📋 已安装的关键包:"
echo "----------------------------------------"
pip list | grep -E "(sqlalchemy|pytest|fastapi|black|flake8)" || echo "❌ 关键包未找到"

echo ""
echo "🔧 环境变量:"
echo "----------------------------------------"
echo "PYTHONPATH: ${PYTHONPATH:-'未设置'}"
echo "ENVIRONMENT: ${ENVIRONMENT:-'未设置'}"
echo "DISABLE_METRICS: ${DISABLE_METRICS:-'未设置'}"
echo "DISABLE_NOTION: ${DISABLE_NOTION:-'未设置'}"

echo ""
echo "📁 目录结构:"
echo "----------------------------------------"
echo "当前目录: $(pwd)"
echo "数据目录存在: $([ -d data ] && echo '✅ 是' || echo '❌ 否')"
echo "测试目录存在: $([ -d tests ] && echo '✅ 是' || echo '❌ 否')"

echo ""
echo "🧪 快速导入测试:"
echo "----------------------------------------"
python -c "
try:
    import sqlalchemy
    print('✅ SQLAlchemy:', sqlalchemy.__version__)
except ImportError as e:
    print('❌ SQLAlchemy 导入失败:', e)

try:
    import pytest
    print('✅ Pytest:', pytest.__version__)
except ImportError as e:
    print('❌ Pytest 导入失败:', e)

try:
    from app.models import Base
    print('✅ App models 导入成功')
except ImportError as e:
    print('❌ App models 导入失败:', e)

try:
    import fastapi
    print('✅ FastAPI:', fastapi.__version__)
except ImportError as e:
    print('❌ FastAPI 导入失败:', e)
"

echo ""
echo "🎯 CI 环境对比:"
echo "----------------------------------------"
echo "预期 Python 版本: 3.11.x"
echo "预期操作系统: Ubuntu 22.04"
echo "预期环境变量: ENVIRONMENT=testing"
echo "预期包管理: 全新 pip 安装"

echo ""
echo "💡 建议:"
echo "----------------------------------------"
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  建议激活虚拟环境以获得更准确的对比"
fi

if [[ "$ENVIRONMENT" != "testing" ]]; then
    echo "⚠️  建议设置 ENVIRONMENT=testing 以匹配 CI"
fi

echo "🐳 要获得完全相同的环境，请运行: make ci-exact"

echo ""
echo "✅ 环境对比完成"
