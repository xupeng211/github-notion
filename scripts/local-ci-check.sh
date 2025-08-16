#!/bin/bash
# 本地 CI 完整模拟脚本
# 模拟 GitHub Actions 的完整检查流程

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "\n${BLUE}📋 $1${NC}"
    echo "=================================================="
}

# 检查必要工具
check_tools() {
    log_step "检查必要工具"

    tools=("python" "pip" "docker" "git")
    for tool in "${tools[@]}"; do
        if command -v $tool &> /dev/null; then
            log_success "$tool 已安装"
        else
            log_error "$tool 未安装，请先安装"
            exit 1
        fi
    done
}

# 安装依赖
install_dependencies() {
    log_step "安装开发依赖"

    log_info "升级 pip..."
    python -m pip install --upgrade pip

    log_info "安装生产依赖..."
    pip install -r requirements.txt

    log_info "安装开发依赖..."
    pip install -r requirements-dev.txt

    log_success "依赖安装完成"
}

# 代码格式检查
check_formatting() {
    log_step "步骤 1/6: 代码格式检查"

    log_info "检查 Black 格式..."
    if black --check --diff .; then
        log_success "Black 格式检查通过"
    else
        log_error "Black 格式检查失败，运行 'make fix' 修复"
        return 1
    fi

    log_info "检查 isort 导入排序..."
    if isort --check-only --diff .; then
        log_success "isort 检查通过"
    else
        log_error "isort 检查失败，运行 'make fix' 修复"
        return 1
    fi
}

# 代码质量检查
check_code_quality() {
    log_step "步骤 2/6: 代码质量检查"

    log_info "运行 flake8 检查..."
    if flake8 . --count --show-source --statistics; then
        log_success "flake8 检查通过"
    else
        log_error "flake8 检查失败"
        return 1
    fi
}

# 安全扫描
security_scan() {
    log_step "步骤 3/6: 安全扫描"

    log_info "检查依赖安全性..."
    safety check || log_warning "Safety 检查发现问题，请检查报告"

    log_info "检查代码安全性..."
    bandit -r app/ -f json -o bandit-report.json || log_warning "Bandit 扫描发现问题，请检查 bandit-report.json"

    log_info "检查密钥泄露..."
    detect-secrets scan --all-files \
        --exclude-files '\.git/.*' \
        --exclude-files '.mypy_cache/.*' \
        --exclude-files '.venv/.*' \
        --exclude-files '.*\.meta\.json$' \
        --exclude-files 'alembic/versions/.*\.py$' \
        --exclude-files 'tests/.*\.py$' \
        --exclude-files '\.env$' \
        --exclude-files 'htmlcov/.*' \
        --exclude-files '\.coverage$' \
        > detect-secrets-report.json || log_warning "密钥扫描发现问题，请检查 detect-secrets-report.json"

    log_success "安全扫描完成"
}

# 运行测试
run_tests() {
    log_step "步骤 4/6: 运行测试"

    log_info "运行测试套件..."
    if pytest tests/ -v --cov=app --cov-append --cov-report=term-missing --cov-fail-under=5 -n auto; then
        log_success "测试通过"
    else
        log_warning "测试失败或覆盖率不足，请检查测试结果"
    fi
}

# 构建 Docker 镜像
build_docker() {
    log_step "步骤 5/6: 构建 Docker 镜像"

    log_info "构建 Docker 镜像..."
    if docker build -t github-notion:local .; then
        log_success "Docker 镜像构建成功"
    else
        log_error "Docker 镜像构建失败"
        return 1
    fi
}

# 测试 Docker 镜像
test_docker() {
    log_step "步骤 6/6: 测试 Docker 镜像"

    log_info "测试 Docker 镜像..."
    if docker run --rm -e ENVIRONMENT=testing github-notion:local python -c "print('Docker 镜像测试成功！')"; then
        log_success "Docker 镜像测试通过"
    else
        log_error "Docker 镜像测试失败"
        return 1
    fi
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    rm -f bandit-report.json detect-secrets-report.json
}

# 主函数
main() {
    echo "🚀 GitHub-Notion 本地 CI 完整模拟"
    echo "=================================================="
    echo "模拟 GitHub Actions 的完整检查流程"
    echo ""

    # 记录开始时间
    start_time=$(date +%s)

    # 设置错误处理
    trap cleanup EXIT

    # 执行检查步骤
    check_tools

    # 可选：安装依赖（如果需要）
    if [[ "$1" == "--install-deps" ]]; then
        install_dependencies
    fi

    # 执行所有检查
    check_formatting
    check_code_quality
    security_scan
    run_tests
    build_docker
    test_docker

    # 计算耗时
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo ""
    echo "=================================================="
    log_success "🎉 本地 CI 模拟完成！"
    log_info "总耗时: ${duration} 秒"
    echo ""
    log_info "📊 生成的报告文件:"
    echo "  - htmlcov/index.html (测试覆盖率报告)"
    echo "  - bandit-report.json (安全扫描报告)"
    echo "  - detect-secrets-report.json (密钥检测报告)"
    echo ""
    log_success "✅ 项目已准备好提交到 GitHub！"
}

# 显示帮助信息
show_help() {
    echo "本地 CI 模拟脚本"
    echo ""
    echo "用法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --install-deps    安装依赖（首次运行时使用）"
    echo "  --help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                # 运行完整检查"
    echo "  $0 --install-deps # 安装依赖并运行检查"
}

# 参数处理
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
