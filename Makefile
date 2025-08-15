# GitHub-Notion 双向同步系统 Makefile
.PHONY: format lint fix test clean install-dev help

# 默认目标
help:
	@echo "📋 可用的代码质量管理命令:"
	@echo ""
	@echo "  make install-dev    - 安装开发依赖工具"
	@echo "  make format        - 格式化代码 (black + isort)"  
	@echo "  make lint          - 检查代码质量 (flake8)"
	@echo "  make fix           - 自动修复代码问题"
	@echo "  make check         - 完整检查 (format + lint)"
	@echo "  make clean         - 清理缓存文件"
	@echo "  make test-prep     - 测试前准备 (fix + lint)"
	@echo ""

# 安装开发工具
install-dev:
	@echo "📦 安装开发依赖工具..."
	pip install black isort flake8 autoflake pre-commit
	@echo "✅ 开发工具安装完成"

# 代码格式化
format:
	@echo "🎨 格式化代码..."
	black .
	isort .
	@echo "✅ 代码格式化完成"

# 代码质量检查
lint:
	@echo "🔍 检查代码质量..."
	flake8 . --count --show-source --statistics
	@echo "✅ 代码质量检查完成"

# 自动修复
fix:
	@echo "🔧 自动修复代码问题..."
	autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .
	black .
	isort .
	@echo "✅ 代码问题修复完成"

# 完整检查
check: format lint
	@echo "🎯 完整代码质量检查完成"

# 清理缓存
clean:
	@echo "🧹 清理缓存文件..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete  
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 缓存清理完成"

# 测试前准备
test-prep: fix lint
	@echo "🚀 测试环境准备完成"

# 初始化项目代码质量
init-quality:
	@echo "🚀 初始化项目代码质量..."
	make install-dev
	make fix
	make clean
	@echo "✅ 项目代码质量初始化完成"

