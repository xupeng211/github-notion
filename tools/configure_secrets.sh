#!/bin/bash
# =============================================================================
# GitHub Secrets 批量配置工具
# =============================================================================
# 用途：从 .secrets.env 文件或交互式输入读取值，批量写入 GitHub Secrets
# 依赖：GitHub CLI (gh)
# 作者：DevOps Assistant
# =============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 期望的 Secrets 清单
declare -A EXPECTED_SECRETS=(
    ["GITHUB_WEBHOOK_SECRET"]="必需|GitHub webhook 签名验证密钥"
    ["NOTION_TOKEN"]="必需|Notion API 访问令牌"
    ["NOTION_DATABASE_ID"]="必需|Notion 目标数据库 ID"
    ["AWS_PRIVATE_KEY"]="必需|EC2 SSH 私钥（PEM 格式）"
    ["GITHUB_TOKEN"]="推荐|GitHub API 访问令牌"
    ["DEADLETTER_REPLAY_TOKEN"]="推荐|死信队列管理令牌"
)

# 全局变量
REPO=""
SECRETS_FILE=".secrets.env"
declare -A SECRET_VALUES=()

# =============================================================================
# 工具函数
# =============================================================================

print_header() {
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}🔐 GitHub Secrets 批量配置工具${NC}"
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

# 验证 PEM 私钥格式
validate_pem_key() {
    local key_content="$1"

    if [[ ! "$key_content" =~ -----BEGIN.*PRIVATE\ KEY----- ]]; then
        return 1
    fi

    if [[ ! "$key_content" =~ -----END.*PRIVATE\ KEY----- ]]; then
        return 1
    fi

    # 检查是否包含实际的密钥内容
    local key_body
    key_body=$(echo "$key_content" | sed -n '/-----BEGIN/,/-----END/p' | grep -v "BEGIN\|END" | tr -d '\n\r ')

    if [[ ${#key_body} -lt 100 ]]; then
        return 1
    fi

    return 0
}

# 从 .secrets.env 读取配置
load_secrets_from_file() {
    if [[ ! -f "$SECRETS_FILE" ]]; then
        print_warning "未找到 $SECRETS_FILE 文件，将使用交互式输入"
        return
    fi

    print_info "从 $SECRETS_FILE 读取配置..."

    while IFS='=' read -r key value; do
        # 跳过注释和空行
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue

        # 移除前后空格
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)

        # 只处理期望的 secrets
        if [[ -n "${EXPECTED_SECRETS[$key]:-}" ]]; then
            SECRET_VALUES["$key"]="$value"
            print_success "从文件读取: $key"
        fi
    done < "$SECRETS_FILE"
}

# 交互式输入缺失的 secrets
interactive_input() {
    print_info "交互式输入缺失的 secrets..."
    echo ""

    for key in "${!EXPECTED_SECRETS[@]}"; do
        if [[ -n "${SECRET_VALUES[$key]:-}" ]]; then
            continue  # 已从文件读取
        fi

        local description="${EXPECTED_SECRETS[$key]#*|}"
        local priority="${EXPECTED_SECRETS[$key]%%|*}"

        echo -e "${BLUE}配置 $key${NC}"
        echo -e "描述: $description"
        echo -e "优先级: $priority"
        echo ""

        if [[ "$key" == "AWS_PRIVATE_KEY" ]]; then
            echo "请输入 PEM 格式的私钥（包含 -----BEGIN 和 -----END 行）:"
            echo "提示: 可以使用 'cat your-key.pem' 然后复制粘贴"
            echo "输入完成后按 Ctrl+D:"

            local pem_content=""
            while IFS= read -r line; do
                pem_content+="$line"$'\n'
            done

            if validate_pem_key "$pem_content"; then
                SECRET_VALUES["$key"]="$pem_content"
                print_success "PEM 私钥格式验证通过"
            else
                print_error "PEM 私钥格式无效"
                echo "请确保包含完整的 -----BEGIN PRIVATE KEY----- 和 -----END PRIVATE KEY----- 行"
                exit 1
            fi
        else
            echo -n "请输入 $key: "
            read -s value
            echo ""

            if [[ -z "$value" ]]; then
                if [[ "$priority" == "必需" ]]; then
                    print_error "$key 是必需的，不能为空"
                    exit 1
                else
                    print_warning "跳过可选的 $key"
                    continue
                fi
            fi

            SECRET_VALUES["$key"]="$value"
        fi

        echo ""
    done
}

# 写入 GitHub Secrets
write_secrets() {
    print_info "开始写入 GitHub Secrets..."
    echo ""

    local success_count=0
    local total_count=${#SECRET_VALUES[@]}

    for key in "${!SECRET_VALUES[@]}"; do
        local value="${SECRET_VALUES[$key]}"

        print_info "设置 $key..."

        if echo -n "$value" | gh secret set "$key" --repo "$REPO" --body -; then
            print_success "$key 设置成功"
            ((success_count++))
        else
            print_error "$key 设置失败"
        fi
    done

    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}📊 配置完成统计${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo "成功设置: $success_count/$total_count"
    echo "仓库: $REPO"
    echo ""

    if [[ $success_count -eq $total_count ]]; then
        print_success "所有 Secrets 配置成功！"
    else
        print_warning "部分 Secrets 配置失败，请检查错误信息"
    fi
}

# 显示使用帮助
show_help() {
    cat << EOF
GitHub Secrets 批量配置工具

用法:
    $0 [选项]

选项:
    -h, --help          显示此帮助信息
    -f, --file FILE     指定 secrets 文件路径（默认: .secrets.env）
    -r, --repo REPO     指定仓库（格式: owner/name，默认从 git remote 获取）

环境变量:
    REPO               覆盖仓库设置（格式: owner/name）

示例:
    # 使用默认 .secrets.env 文件
    $0

    # 指定自定义文件
    $0 -f my-secrets.env

    # 指定仓库
    $0 -r myorg/myrepo

期望的 Secrets:
EOF

    for key in "${!EXPECTED_SECRETS[@]}"; do
        local description="${EXPECTED_SECRETS[$key]#*|}"
        local priority="${EXPECTED_SECRETS[$key]%%|*}"
        printf "    %-25s %s - %s\n" "$key" "[$priority]" "$description"
    done
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
            -f|--file)
                SECRETS_FILE="$2"
                shift 2
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

    # 执行配置流程
    check_dependencies
    get_repo_info
    load_secrets_from_file
    interactive_input
    write_secrets

    echo ""
    print_info "配置完成！可以使用以下命令验证:"
    echo "  gh secret list --repo $REPO"
    echo "  tools/validate_workflows.py"
}

# 运行主函数
main "$@"
