#!/usr/bin/env bash
# 🔄 回滚脚本 - 支持多种回滚策略

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
DEPLOY_DIR="/opt/gitee-notion-sync"
COMPOSE_FILE="docker-compose.prod.yml"
SERVICE_NAME="app"
BACKUP_DIR="/opt/backups"

# 显示帮助信息
show_help() {
    cat << EOF
🔄 回滚脚本 - 支持多种回滚策略

用法:
  $0 --to-previous              # 回滚到上一版本
  $0 --to-version <version>     # 回滚到指定版本
  $0 --emergency-stop           # 紧急停止服务
  $0 --list-versions            # 列出可用版本
  $0 --dry-run <strategy>       # 预演回滚（不实际执行）

示例:
  $0 --to-previous
  $0 --to-version v1.2.3
  $0 --emergency-stop
  $0 --dry-run --to-previous

选项:
  -h, --help                    显示此帮助信息
  --dry-run                     预演模式，不实际执行
  --force                       强制执行，跳过确认
EOF
}

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境
check_environment() {
    log_info "检查环境..."
    
    if [[ ! -d "$DEPLOY_DIR" ]]; then
        log_error "部署目录不存在: $DEPLOY_DIR"
        exit 1
    fi
    
    if [[ ! -f "$DEPLOY_DIR/$COMPOSE_FILE" ]]; then
        log_error "Docker Compose文件不存在: $DEPLOY_DIR/$COMPOSE_FILE"
        exit 1
    fi
    
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker未安装或不可用"
        exit 1
    fi
    
    log_success "环境检查通过"
}

# 获取当前版本
get_current_version() {
    cd "$DEPLOY_DIR"
    local current_image=$(grep "image:" "$COMPOSE_FILE" | head -1 | sed 's/.*image: *//' | tr -d '"')
    echo "$current_image"
}

# 获取上一版本
get_previous_version() {
    # 从备份目录或Git历史中获取上一版本
    # 这里简化为从镜像标签中推断
    local current=$(get_current_version)
    local tag=$(echo "$current" | cut -d':' -f2)
    
    # 如果是commit hash，尝试获取previous标签
    if [[ ${#tag} -eq 7 ]]; then
        echo "${current%:*}:previous"
    else
        # 如果是版本号，尝试减1
        echo "${current%:*}:previous"
    fi
}

# 列出可用版本
list_versions() {
    log_info "可用版本列表:"
    echo "当前版本: $(get_current_version)"
    echo "上一版本: $(get_previous_version)"
    
    # 从Docker镜像列表中获取更多版本
    local image_base=$(get_current_version | cut -d':' -f1)
    log_info "本地可用镜像:"
    docker images "$image_base" --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}" || true
}

# 备份当前配置
backup_current_config() {
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/config_backup_$backup_timestamp.yml"
    
    mkdir -p "$BACKUP_DIR"
    cp "$DEPLOY_DIR/$COMPOSE_FILE" "$backup_file"
    log_success "当前配置已备份到: $backup_file"
}

# 执行回滚
execute_rollback() {
    local target_version="$1"
    local dry_run="${2:-false}"
    
    log_info "准备回滚到版本: $target_version"
    
    if [[ "$dry_run" == "true" ]]; then
        log_warning "预演模式 - 不会实际执行"
        echo "将执行的操作:"
        echo "1. 备份当前配置"
        echo "2. 更新镜像版本: $target_version"
        echo "3. 重启服务"
        echo "4. 验证服务状态"
        return 0
    fi
    
    # 备份当前配置
    backup_current_config
    
    # 更新镜像版本
    cd "$DEPLOY_DIR"
    sed -i "s|image: .*|image: ${target_version}|" "$COMPOSE_FILE"
    log_success "镜像版本已更新为: $target_version"
    
    # 重启服务
    log_info "重启服务..."
    docker compose -f "$COMPOSE_FILE" down
    docker compose -f "$COMPOSE_FILE" up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 验证服务状态
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log_success "回滚成功！服务已启动"
        log_info "当前版本: $(get_current_version)"
    else
        log_error "回滚失败！服务未正常启动"
        exit 1
    fi
}

# 紧急停止
emergency_stop() {
    local dry_run="${1:-false}"
    
    log_warning "执行紧急停止..."
    
    if [[ "$dry_run" == "true" ]]; then
        log_warning "预演模式 - 不会实际执行"
        echo "将执行的操作:"
        echo "1. 立即停止所有服务"
        echo "2. 备份当前状态"
        return 0
    fi
    
    cd "$DEPLOY_DIR"
    docker compose -f "$COMPOSE_FILE" down
    log_success "所有服务已紧急停止"
}

# 主函数
main() {
    local action=""
    local target_version=""
    local dry_run="false"
    local force="false"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --to-previous)
                action="rollback_previous"
                shift
                ;;
            --to-version)
                action="rollback_version"
                target_version="$2"
                shift 2
                ;;
            --emergency-stop)
                action="emergency_stop"
                shift
                ;;
            --list-versions)
                action="list_versions"
                shift
                ;;
            --dry-run)
                dry_run="true"
                shift
                ;;
            --force)
                force="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查必需参数
    if [[ -z "$action" ]]; then
        log_error "请指定操作"
        show_help
        exit 1
    fi
    
    # 检查环境
    check_environment
    
    # 执行操作
    case $action in
        rollback_previous)
            local previous_version=$(get_previous_version)
            if [[ "$force" != "true" && "$dry_run" != "true" ]]; then
                echo -n "确认回滚到上一版本 ($previous_version)? [y/N]: "
                read -r confirm
                if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
                    log_info "操作已取消"
                    exit 0
                fi
            fi
            execute_rollback "$previous_version" "$dry_run"
            ;;
        rollback_version)
            if [[ -z "$target_version" ]]; then
                log_error "请指定目标版本"
                exit 1
            fi
            if [[ "$force" != "true" && "$dry_run" != "true" ]]; then
                echo -n "确认回滚到版本 ($target_version)? [y/N]: "
                read -r confirm
                if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
                    log_info "操作已取消"
                    exit 0
                fi
            fi
            execute_rollback "$target_version" "$dry_run"
            ;;
        emergency_stop)
            if [[ "$force" != "true" && "$dry_run" != "true" ]]; then
                echo -n "确认紧急停止所有服务? [y/N]: "
                read -r confirm
                if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
                    log_info "操作已取消"
                    exit 0
                fi
            fi
            emergency_stop "$dry_run"
            ;;
        list_versions)
            list_versions
            ;;
        *)
            log_error "未知操作: $action"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
