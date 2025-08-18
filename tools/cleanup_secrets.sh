#!/bin/bash
# =============================================================================
# GitHub Secrets 清理工具
# =============================================================================
# 用途：删除未使用/废弃的 GitHub Secrets
# 依赖：GitHub CLI (gh), Python 3
# 作者：DevOps Assistant
# =============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 全局变量
REPO=""
DRY_RUN=false
FORCE=false
INTERACTIVE=true

# =============================================================================
# 工具函数
# =============================================================================

print_header() {
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}🗑️  GitHub Secrets 清理工具${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""
}

print_error() {
    echo -e "${RED}❌ 错误: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."

    # 检查 gh CLI
    if ! command -v gh &> /dev/null; then
        print_error "GitHub CLI (gh) 未安装"
        echo "请安装 GitHub CLI: https://cli.github.com/"
        exit 1
    fi

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未安装"
        exit 1
    fi

    # 检查 gh 登录状态
    if ! gh auth status &> /dev/null; then
        print_error "GitHub CLI 未登录"
        echo "请先登录: gh auth login"
        exit 1
    fi

    # 检查 git 仓库
    if ! git rev-parse --git-dir &> /dev/null; then
        print_error "当前目录不是 Git 仓库"
        exit 1
    fi

    # 检查 validate_workflows.py
    if [[ ! -f "tools/validate_workflows.py" ]]; then
        print_error "未找到 tools/validate_workflows.py"
        echo "请确保该文件存在并可执行"
        exit 1
    fi

    print_success "依赖检查通过"
}

# 获取仓库信息
get_repo_info() {
    if [[ -n "${REPO:-}" ]]; then
        print_info "使用环境变量指定的仓库: $REPO"
        return
    fi

    local remote_url
    remote_url=$(git remote get-url origin 2>/dev/null || echo "")

    if [[ -z "$remote_url" ]]; then
        print_error "无法获取 Git 远程仓库 URL"
        exit 1
    fi

    # 解析 owner/repo
    if [[ "$remote_url" =~ github\.com[:/]([^/]+)/([^/]+)(\.git)?$ ]]; then
        local owner="${BASH_REMATCH[1]}"
        local repo_name="${BASH_REMATCH[2]}"
        repo_name="${repo_name%.git}"  # 移除 .git 后缀
        REPO="$owner/$repo_name"
    else
        print_error "无法解析 GitHub 仓库信息: $remote_url"
        exit 1
    fi

    print_info "检测到仓库: $REPO"
}

# 获取可清理的 secrets
get_cleanable_secrets() {
    print_info "分析可清理的 secrets..."

    # 运行 validate_workflows.py 获取分析结果
    local temp_file
    temp_file=$(mktemp)

    if ! python3 tools/validate_workflows.py > "$temp_file" 2>&1; then
        print_warning "workflow 分析完成，但发现一些问题"
    fi

    # 解析输出，提取废弃和多余的 secrets
    local deprecated_secrets=()
    local extra_secrets=()
    local in_deprecated_section=false
    local in_extra_section=false

    while IFS= read -r line; do
        if [[ "$line" =~ 🗑️.*废弃的.*Secrets ]]; then
            in_deprecated_section=true
            in_extra_section=false
            continue
        elif [[ "$line" =~ ℹ️.*多余的.*Secrets ]]; then
            in_deprecated_section=false
            in_extra_section=true
            continue
        elif [[ "$line" =~ ^[[:space:]]*$ ]] || [[ "$line" =~ ^[^[:space:]] ]]; then
            in_deprecated_section=false
            in_extra_section=false
            continue
        fi

        if [[ "$in_deprecated_section" == true ]] && [[ "$line" =~ ^[[:space:]]*-[[:space:]]*([A-Z_]+): ]]; then
            deprecated_secrets+=("${BASH_REMATCH[1]}")
        elif [[ "$in_extra_section" == true ]] && [[ "$line" =~ ^[[:space:]]*-[[:space:]]*([A-Z_]+): ]]; then
            extra_secrets+=("${BASH_REMATCH[1]}")
        fi
    done < "$temp_file"

    rm -f "$temp_file"

    # 合并所有可清理的 secrets
    local all_cleanable=("${deprecated_secrets[@]}" "${extra_secrets[@]}")

    if [[ ${#all_cleanable[@]} -eq 0 ]]; then
        print_success "没有发现需要清理的 secrets"
        return 0
    fi

    echo ""
    print_info "发现可清理的 secrets:"

    if [[ ${#deprecated_secrets[@]} -gt 0 ]]; then
        echo -e "${YELLOW}废弃的 secrets:${NC}"
        for secret in "${deprecated_secrets[@]}"; do
            echo "  - $secret"
        done
    fi

    if [[ ${#extra_secrets[@]} -gt 0 ]]; then
        echo -e "${BLUE}多余的 secrets:${NC}"
        for secret in "${extra_secrets[@]}"; do
            echo "  - $secret"
        done
    fi

    echo ""

    # 返回可清理的 secrets 列表
    printf '%s\n' "${all_cleanable[@]}"
}

# 确认删除操作
confirm_deletion() {
    local secrets_to_delete=("$@")

    if [[ "$FORCE" == true ]]; then
        return 0
    fi

    if [[ "$INTERACTIVE" == false ]]; then
        return 0
    fi

    echo -e "${YELLOW}⚠️  即将删除以下 secrets:${NC}"
    for secret in "${secrets_to_delete[@]}"; do
        echo "  - $secret"
    done
    echo ""

    echo -e "${RED}警告: 此操作不可逆！${NC}"
    echo -n "确认删除这些 secrets? [y/N]: "
    read -r response

    case "$response" in
        [yY]|[yY][eE][sS])
            return 0
            ;;
        *)
            print_info "操作已取消"
            return 1
            ;;
    esac
}

# 删除 secrets
delete_secrets() {
    local secrets_to_delete=("$@")

    if [[ ${#secrets_to_delete[@]} -eq 0 ]]; then
        print_info "没有需要删除的 secrets"
        return 0
    fi

    if ! confirm_deletion "${secrets_to_delete[@]}"; then
        return 1
    fi

    local success_count=0
    local total_count=${#secrets_to_delete[@]}

    print_info "开始删除 secrets..."
    echo ""

    for secret in "${secrets_to_delete[@]}"; do
        if [[ "$DRY_RUN" == true ]]; then
            print_info "[DRY RUN] 将删除: $secret"
            ((success_count++))
        else
            print_info "删除 $secret..."

            if gh secret delete "$secret" --repo "$REPO" 2>/dev/null; then
                print_success "$secret 删除成功"
                ((success_count++))
            else
                print_error "$secret 删除失败"
            fi
        fi
    done

    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}📊 清理完成统计${NC}"
    echo -e "${GREEN}=================================${NC}"

    if [[ "$DRY_RUN" == true ]]; then
        echo "模拟删除: $success_count/$total_count"
    else
        echo "成功删除: $success_count/$total_count"
    fi
    echo "仓库: $REPO"
    echo ""

    if [[ $success_count -eq $total_count ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            print_success "模拟清理完成！使用 --execute 执行实际删除"
        else
            print_success "所有 secrets 清理成功！"
        fi
    else
        print_warning "部分 secrets 清理失败，请检查错误信息"
    fi
}

# 显示使用帮助
show_help() {
    cat << EOF
GitHub Secrets 清理工具

用法:
    $0 [选项]

选项:
    -h, --help          显示此帮助信息
    -n, --dry-run       模拟运行，不实际删除（默认）
    -e, --execute       执行实际删除操作
    -f, --force         强制删除，不询问确认
    -y, --yes           非交互模式，自动确认
    -r, --repo REPO     指定仓库（格式: owner/name，默认从 git remote 获取）

环境变量:
    REPO               覆盖仓库设置（格式: owner/name）

示例:
    # 模拟运行（安全预览）
    $0

    # 执行实际删除
    $0 --execute

    # 强制删除，不询问确认
    $0 --execute --force

    # 非交互模式
    $0 --execute --yes

安全提示:
    - 默认为模拟运行模式，不会实际删除任何 secrets
    - 使用 --execute 才会执行实际删除操作
    - 删除操作不可逆，请谨慎使用
    - 建议先运行模拟模式查看将要删除的内容
EOF
}

# =============================================================================
# 主函数
# =============================================================================

main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -e|--execute)
                DRY_RUN=false
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -y|--yes)
                INTERACTIVE=false
                shift
                ;;
            -r|--repo)
                REPO="$2"
                shift 2
                ;;
            *)
                print_error "未知选项: $1"
                echo "使用 -h 查看帮助"
                exit 1
                ;;
        esac
    done

    print_header

    if [[ "$DRY_RUN" == true ]]; then
        print_warning "运行在模拟模式，不会实际删除任何 secrets"
        echo ""
    fi

    # 执行清理流程
    check_dependencies
    get_repo_info

    # 获取可清理的 secrets
    local cleanable_secrets
    mapfile -t cleanable_secrets < <(get_cleanable_secrets)

    # 删除 secrets
    delete_secrets "${cleanable_secrets[@]}"

    echo ""
    print_info "清理完成！可以使用以下命令验证:"
    echo "  gh secret list --repo $REPO"
    echo "  tools/validate_workflows.py"
}

# 运行主函数
main "$@"
