#!/bin/bash
# 推送代码前的快速检查脚本

set -e  # 遇到错误立即退出

echo "🚀 开始推送前检查..."

# 检查必需的文件
echo "📁 检查关键文件..."
required_files=(
    "env.example"
    "requirements.txt"
    "scripts/validate_fixes.py"
    "scripts/start_service.py"
    "DEPLOYMENT_GUIDE.md"
    "PRE_COMMIT_CHECKLIST.md"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 缺少文件: $file"
        exit 1
    fi
done
echo "✅ 关键文件检查通过"

# 运行架构验证
echo "🔧 运行架构验证..."
if python scripts/validate_fixes.py > /dev/null 2>&1; then
    echo "✅ 架构验证通过"
else
    echo "❌ 架构验证失败"
    echo "详细信息："
    python scripts/validate_fixes.py
    exit 1
fi

# 检查模块导入
echo "📦 检查模块导入..."
python -c "
import sys
try:
    import app.server
    import app.service
    import app.models
    import app.notion
    import app.github
    print('✅ 模块导入检查通过')
except ImportError as e:
    print(f'❌ 模块导入失败: {e}')
    sys.exit(1)
"

# 检查敏感信息
echo "🔒 检查敏感信息..."
if git status --porcelain | grep -E "\.env$|\.env\..*$" > /dev/null; then
    echo "❌ 检测到 .env 文件被暂存，请移除"
    echo "运行: git reset HEAD .env"
    exit 1
fi

if grep -r "ghp_[a-zA-Z0-9]\{36\}\|secret_[a-zA-Z0-9]\{50\}" app/ > /dev/null 2>&1; then
    echo "❌ 检测到可能的硬编码密钥"
    exit 1
fi
echo "✅ 安全检查通过"

# 检查代码格式（可选）
echo "📝 检查代码格式..."
if command -v flake8 > /dev/null; then
    if flake8 app/ --max-line-length=120 --ignore=E203,W503 --exclude=__pycache__ > /dev/null 2>&1; then
        echo "✅ 代码格式检查通过"
    else
        echo "⚠️ 代码格式有问题，但不影响推送"
    fi
else
    echo "⚠️ flake8 未安装，跳过格式检查"
fi

# 检查 Git 状态
echo "📊 检查 Git 状态..."
if [ -z "$(git status --porcelain)" ]; then
    echo "⚠️ 没有暂存的更改"
else
    echo "✅ 有待提交的更改"
fi

# 最终确认
echo ""
echo "🎉 所有检查通过！"
echo ""
echo "📋 推送前最终确认："
echo "   ✅ 架构验证通过"
echo "   ✅ 模块导入正常"
echo "   ✅ 安全检查通过"
echo "   ✅ 关键文件齐全"
echo ""
echo "🚀 代码可以安全推送！"
echo ""
echo "推送命令:"
echo "   git add ."
echo "   git commit -m \"your commit message\""
echo "   git push origin main" 