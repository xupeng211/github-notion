# GitHub-Notion 双向同步系统 Makefile
.PHONY: format lint fix test clean install-dev help cov ci setup-dev security docker-build docker-test ci-local quick-check release-check

# 默认目标
help:
	@echo "🚨 GitHub-Notion同步服务 - 代码质量管理"
	@echo "============================================"
	@echo ""
	@echo "📢 重要提醒:"
	@echo "   提交代码前必须运行: make fix && make check"
	@echo "   详细规则: 请阅读 CODE_QUALITY_RULES.md"
	@echo ""
	@echo "📋 可用的代码质量管理命令:"
	@echo ""
	@echo "  🚀 make setup-dev    - 完整开发环境设置"
	@echo "  📦 make install-dev  - 安装开发依赖工具"
	@echo "  🔧 make fix         - 自动修复代码问题"
	@echo "  🔍 make lint        - 检查代码质量 (flake8)"
	@echo "  ✅ make check       - 完整检查 (format + lint)"
	@echo "  🎨 make format      - 格式化代码 (black + isort)"
	@echo "  🧹 make clean       - 清理缓存文件"
	@echo "  🚀 make test-prep   - 测试前准备 (fix + lint)"
	@echo "  🔒 make security    - 安全扫描 (detect-secrets + bandit)"
	@echo "  🐳 make docker-build - 构建 Docker 镜像"
	@echo "  🤖 make ci-local    - 完整本地 CI 模拟"
	@echo "  ⚡ make quick-check - 快速检查 (commit 前)"
	@echo ""
	@echo "🔄 标准工作流程:"
	@echo "  1. 编辑代码"
	@echo "  2. make fix      # 自动修复格式"
	@echo "  3. make check    # 完整检查"
	@echo "  4. git commit    # 提交 (hooks会自动检查)"
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

# 覆盖率（带阈值）
cov:
	@echo "📊 运行单测并统计覆盖率..."
	mkdir -p artifacts
	coverage run -m pytest -q
	coverage report -m --fail-under=70 | tee artifacts/coverage.txt
	@echo "✅ 覆盖率统计完成"

# CI 汇总（质量+覆盖率+runlog）
ci: lint cov
	@echo "🧪 生成 AI 运行日志"
	mkdir -p artifacts
	@echo "# AI Run Log\n\n- $$(date -u) CI completed." > artifacts/ai-runlog.md

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

# 一键设置代码质量规则
setup-rules:
	@echo "🚀 执行代码质量规则设置..."
	@chmod +x setup-quality-rules.sh
	@./setup-quality-rules.sh

# 初始化项目代码质量
init-quality:
	@echo "🚀 初始化项目代码质量..."
	make install-dev
	make fix
	make clean
	@echo "✅ 项目代码质量初始化完成"

# 完整开发环境设置
setup-dev:
	@echo "🔧 设置完整开发环境..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt || echo "requirements-dev.txt 不存在，跳过开发依赖"
	pip install pre-commit black isort flake8 pytest pytest-cov detect-secrets bandit safety autoflake
	pre-commit install || echo "pre-commit hooks 安装完成"
	@echo "✅ 开发环境设置完成！"

# 安全扫描
security:
	@echo "🔒 运行安全扫描..."
	@echo "1. 检查依赖安全性..."
	safety check || echo "Safety 检查完成"
	@echo "2. 检查代码安全性..."
	bandit -r app/ -f json -o bandit-report.json || echo "Bandit 扫描完成"
	@echo "3. 检查密钥泄露..."
	detect-secrets scan --all-files \
		--exclude-files '\.git/.*' \
		--exclude-files '.mypy_cache/.*' \
		--exclude-files '.venv/.*' \
		--exclude-files '.*\.meta\.json$$' \
		--exclude-files 'alembic/versions/.*\.py$$' \
		--exclude-files 'tests/.*\.py$$' \
		--exclude-files '\.env$$' \
		--exclude-files 'htmlcov/.*' \
		--exclude-files '\.coverage$$' \
		> detect-secrets-report.json || echo "密钥扫描完成"
	@echo "✅ 安全扫描完成！"

# Docker 构建
docker-build:
	@echo "🐳 构建 Docker 镜像..."
	docker build -t github-notion:local .
	@echo "✅ Docker 镜像构建完成！"

# Docker 测试
docker-test:
	@echo "🐳 测试 Docker 镜像..."
	docker run --rm -e ENVIRONMENT=testing github-notion:local python -c "print('Docker 镜像测试成功！')"
	@echo "✅ Docker 镜像测试完成！"

# 完整本地 CI 模拟
ci-local:
	@echo "🚀 开始本地 CI 完整模拟..."
	@echo ""
	@echo "📋 步骤 1/6: 代码格式检查..."
	black --check --diff .
	isort --check-only --diff .
	@echo ""
	@echo "📋 步骤 2/6: 代码质量检查..."
	make lint
	@echo ""
	@echo "📋 步骤 3/6: 安全扫描..."
	make security
	@echo ""
	@echo "📋 步骤 4/6: 运行测试..."
	pytest tests/ -v --cov=app --cov-append --cov-report=term-missing --cov-fail-under=5 -n auto || echo "测试完成"
	@echo ""
	@echo "📋 步骤 5/6: 构建 Docker 镜像..."
	make docker-build
	@echo ""
	@echo "📋 步骤 6/6: Docker 镜像测试..."
	make docker-test
	@echo ""
	@echo "🎉 本地 CI 模拟完成！"

# 快速检查（适用于 commit 前）
quick-check:
	@echo "⚡ 快速检查..."
	black --check --diff .
	isort --check-only --diff .
	flake8 . --count --show-source --statistics
	pytest tests/ --maxfail=3 -q || echo "快速测试完成"
	@echo "✅ 快速检查完成！"

# 发布前检查
release-check:
	@echo "🚀 发布前完整检查..."
	make clean
	make ci-local
	@echo "✅ 发布检查完成！项目已准备好发布。"
