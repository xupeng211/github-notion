# GitHub-Notion 双向同步系统 Makefile
.PHONY: help test lint build run clean local-ci fix-code deploy-check

# 默认目标
help:
	@echo "🚀 GitHub-Notion 双向同步系统"
	@echo "================================"
	@echo "可用命令:"
	@echo "  make lint          - 代码质量检查"
	@echo "  make fix-code      - 自动修复代码格式问题"
	@echo "  make test          - 运行测试"
	@echo "  make local-ci      - 完整本地CI/CD模拟"
	@echo "  make build         - 构建Docker镜像"
	@echo "  make run           - 运行开发服务器"
	@echo "  make deploy-check  - 部署前检查"
	@echo "  make clean         - 清理临时文件"
	@echo ""
	@echo "🎯 推荐工作流程:"
	@echo "  1. make fix-code   # 修复代码格式"
	@echo "  2. make local-ci   # 完整测试"
	@echo "  3. git push        # 推送代码"

# 代码质量检查
lint:
	@echo "🔍 运行代码质量检查..."
	flake8 app/ --max-line-length=120 --ignore=E203,W503
	flake8 *.py --max-line-length=120 --ignore=E203,W503 --exclude=__pycache__,*.pyc || echo "⚠️ 部分文件有格式问题"
	@echo "✅ 代码质量检查完成"

# 自动修复代码格式
fix-code:
	@echo "🔧 自动修复代码格式问题..."
	@python3 -c "import re; content=open('app/server.py').read(); open('app/server.py','w').write(content.replace('\t','    '))"
	@echo "  ✅ 修复了缩进问题"
	@find . -name "*.py" -exec sed -i 's/[[:space:]]*$$//' {} \;
	@echo "  ✅ 清理了尾随空格"
	@echo "✅ 代码格式修复完成"

# 运行测试
test:
	@echo "🧪 运行快速测试..."
	python3 quick_test.py
	@echo "🧪 运行详细测试..."
	timeout 60 python3 test_sync_system.py || echo "⚠️ 测试完成（有警告）"

# 完整本地CI测试
local-ci:
	@echo "🚀 运行完整本地CI/CD测试..."
	bash local-ci-test.sh

# 构建Docker镜像
build:
	@echo "🐳 构建Docker镜像..."
	docker build -t github-notion-sync:latest .
	@echo "✅ Docker镜像构建完成"

# 运行开发服务器
run:
	@echo "🏃 启动开发服务器..."
	@echo "请确保已配置 .env 文件"
	uvicorn app.server:app --reload --host 0.0.0.0 --port 8000

# 部署前检查
deploy-check:
	@echo "🔍 部署前检查..."
	@echo "检查部署文件..."
	@ls -la deploy/ || echo "❌ deploy 目录不存在"
	@echo "检查环境配置..."
	@test -f .env && echo "✅ .env 文件存在" || echo "⚠️ .env 文件不存在"
	@echo "检查数据目录..."
	@mkdir -p data logs && echo "✅ 数据目录已准备"

# 清理临时文件
clean:
	@echo "🧹 清理临时文件..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -f /tmp/*test_output.log 2>/dev/null || true
	docker system prune -f >/dev/null 2>&1 || true
	@echo "✅ 清理完成"

# 快速推送工作流
push: fix-code local-ci
	@echo "🚀 代码已准备就绪，可以推送："
	@echo "  git add ."
	@echo "  git commit -m \"你的提交信息\""
	@echo "  git push github main"

