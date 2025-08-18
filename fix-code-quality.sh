#!/bin/bash

# 一键修复代码质量脚本
# 使用方法: ./fix-code-quality.sh

set -e

echo "🚀 开始一键修复代码质量问题..."
echo "================================"

# 检查是否安装了必需工具
echo "📋 检查必需工具..."
MISSING_TOOLS=()

if ! command -v python3 &> /dev/null; then
    MISSING_TOOLS+=("python3")
fi

# 检查Python包
python3 -c "import black" 2>/dev/null || MISSING_TOOLS+=("black")
python3 -c "import isort" 2>/dev/null || MISSING_TOOLS+=("isort")
python3 -c "import flake8" 2>/dev/null || MISSING_TOOLS+=("flake8")
python3 -c "import autoflake" 2>/dev/null || MISSING_TOOLS+=("autoflake")

if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
    echo "❌ 缺少必需工具: ${MISSING_TOOLS[*]}"
    echo "💡 正在安装缺少的工具..."
    pip3 install black isort flake8 autoflake
    echo "✅ 工具安装完成"
fi

# 备份重要文件
echo ""
echo "💾 创建备份..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
find . -name "*.py" -not -path "./.git/*" -not -path "./venv/*" -not -path "./.venv/*" -exec cp {} "$BACKUP_DIR"/ \; 2>/dev/null || true
echo "✅ 备份创建完成: $BACKUP_DIR"

# 步骤1: 移除未使用的导入和变量
echo ""
echo "1️⃣ 移除未使用的导入和变量..."
autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive . \
    --exclude=venv,env,.venv,.git,__pycache__,migrations
echo "✅ 清理完成"

# 步骤2: 格式化代码
echo ""
echo "2️⃣ 格式化代码 (Black)..."
black . --line-length=120 --exclude="/(\.git|__pycache__|\.pytest_cache|venv|env|\.venv|migrations)/"
echo "✅ 代码格式化完成"

# 步骤3: 整理导入顺序
echo ""
echo "3️⃣ 整理导入顺序 (isort)..."
isort . --profile=black --line-length=120
echo "✅ 导入顺序整理完成"

# 步骤4: 检查代码质量
echo ""
echo "4️⃣ 检查代码质量 (flake8)..."
echo "检查前错误统计:"
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true

echo ""
echo "运行完整质量检查:"
if flake8 . --count --max-line-length=120 --statistics; then
    echo "🎉 代码质量检查全部通过！"
    QUALITY_STATUS="✅ 完美"
else
    echo "⚠️ 仍有一些质量问题，但主要问题已修复"
    QUALITY_STATUS="⚠️ 部分问题"
fi

# 步骤5: 清理缓存
echo ""
echo "5️⃣ 清理缓存文件..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
echo "✅ 缓存清理完成"

# 生成报告
echo ""
echo "================================"
echo "📊 修复完成报告"
echo "================================"
echo "修复时间: $(date)"
echo "备份位置: $BACKUP_DIR"
echo "代码质量: $QUALITY_STATUS"
echo ""

# 统计修复情况
TOTAL_PY_FILES=$(find . -name "*.py" -not -path "./.git/*" -not -path "./venv/*" -not -path "./.venv/*" | wc -l)
echo "处理文件: $TOTAL_PY_FILES 个Python文件"

echo ""
echo "🎯 建议后续操作:"
echo "1. 检查修复结果: git diff"
echo "2. 测试功能正常: 运行测试或启动服务"
echo "3. 提交更改: git add . && git commit -m 'style: 修复代码质量问题'"
echo ""

echo "✅ 代码质量修复完成！"

# 询问是否要查看修改
read -p "📋 是否要查看修复的内容? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📄 修复的文件差异:"
    git diff --name-only --diff-filter=M | head -10
    echo ""
    echo "💡 使用 'git diff' 查看详细修改"
fi
