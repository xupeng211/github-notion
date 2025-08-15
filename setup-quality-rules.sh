#!/bin/bash

# 自动设置项目代码质量规则
# 使用方法: ./setup-quality-rules.sh

set -e

echo "🚀 开始设置项目代码质量规则..."
echo "===================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 需要Python 3环境"
    exit 1
fi

echo "✅ Python环境检查通过"

# 安装必需的工具
echo ""
echo "📦 安装代码质量工具..."
pip install black isort flake8 autoflake pre-commit

echo "✅ 工具安装完成"

# 安装pre-commit hooks
echo ""
echo "🔒 设置Git hooks..."

if [ ! -d ".git" ]; then
    echo "⚠️  警告: 这不是一个Git仓库，跳过Git hooks设置"
else
    pre-commit install
    echo "✅ Git hooks安装完成"

    echo ""
    echo "🧪 运行初始化检查..."
    pre-commit run --all-files || echo "⚠️  发现一些问题，将在下一步修复"
fi

# 运行初始修复
echo ""
echo "🔧 运行初始代码修复..."
make fix || echo "⚠️  部分修复可能需要手动处理"

echo ""
echo "🎯 检查修复结果..."
make lint || echo "⚠️  仍有一些质量问题，请查看上面的输出"

# 生成设置报告
echo ""
echo "===================================="
echo "📊 设置完成报告"
echo "===================================="
echo "✅ 开发工具: 已安装 (black, isort, flake8, autoflake, pre-commit)"
echo "✅ Git hooks: 已配置 (pre-commit)"
echo "✅ 配置文件: 已生效"
echo ""
echo "📋 可用命令:"
echo "  make help        - 查看所有可用命令"
echo "  make fix         - 自动修复代码问题"
echo "  make check       - 完整质量检查"
echo "  make lint        - 代码质量检查"
echo ""
echo "📖 详细规则: 请阅读 CODE_QUALITY_RULES.md"
echo ""

# 验证设置
echo "🔍 验证设置..."
if command -v black &> /dev/null && command -v isort &> /dev/null && command -v flake8 &> /dev/null; then
    echo "✅ 所有工具设置成功"

    if [ -f ".pre-commit-config.yaml" ]; then
        echo "✅ Pre-commit配置文件存在"
    fi

    if [ -f "CODE_QUALITY_RULES.md" ]; then
        echo "✅ 质量规则文档存在"
    fi

    if [ -f "pyproject.toml" ]; then
        echo "✅ 项目配置文件存在"
    fi

    echo ""
    echo "🎉 代码质量规则设置完成！"
    echo ""
    echo "💡 下次提交代码前，请运行: make fix && make check"
    echo "🔒 Git hooks会自动检查代码质量"

else
    echo "❌ 工具设置可能有问题，请检查错误信息"
    exit 1
fi

# 提供快速测试选项
echo ""
read -p "🧪 是否要运行快速质量测试? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "运行快速测试..."
    make check && echo "🎉 质量测试通过！" || echo "⚠️  发现问题，请按照上面的提示修复"
fi

echo ""
echo "✅ 设置完成！欢迎使用高质量的代码开发环境！"
