#!/bin/bash

# =================================================================
# Gitee-Notion 同步服务部署脚本
# =================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 帮助信息
show_help() {
    cat << EOF
Gitee-Notion 同步服务部署脚本

用法: $0 [选项] <环境>

环境:
  dev         开发环境
  staging     预发布环境
  production  生产环境

选项:
  -v, --version     指定版本 (默认: latest)
  -r, --rollback    回滚到上一个版本
  -h, --help        显示帮助信息
  --dry-run         模拟运行，不执行实际部署
  --force           强制部署，跳过健康检查
  --backup          部署前备份当前版本

示例:
  $0 staging                    # 部署最新版本到预发布环境
  $0 -v v1.2.3 production      # 部署指定版本到生产环境
  $0 --rollback production     # 回滚生产环境到上一版本
  $0 --dry-run staging         # 模拟部署到预发布环境

EOF
}

# 默认值
ENVIRONMENT=""
VERSION="latest"
ROLLBACK=false
DRY_RUN=false
FORCE=false
BACKUP=false
REGISTRY="${REGISTRY:-your-registry.com}"
IMAGE_NAME="${IMAGE_NAME:-gitee-notion-sync}"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -r|--rollback)
            ROLLBACK=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --backup)
            BACKUP=true
            shift
            ;;
        dev|staging|production)
            ENVIRONMENT="$1"
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 验证环境参数
if [[ -z "$ENVIRONMENT" ]]; then
    log_error "必须指定环境: dev, staging, 或 production"
    show_help
    exit 1
fi

# 环境配置
case $ENVIRONMENT in
    dev)
        SERVICE_NAME="gitee-notion-sync-dev"
        PORT=8001
        COMPOSE_FILE="docker-compose.dev.yml"
        ;;
    staging)
        SERVICE_NAME="gitee-notion-sync-staging"
        PORT=8002
        COMPOSE_FILE="docker-compose.staging.yml"
        ;;
    production)
        SERVICE_NAME="gitee-notion-sync-prod"
        PORT=8000
        COMPOSE_FILE="docker-compose.prod.yml"
        ;;
esac

# 健康检查函数
health_check() {
    local url="$1"
    local max_attempts=30
    local attempt=1

    log_info "健康检查: $url"

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "$url/health" > /dev/null 2>&1; then
            log_success "健康检查通过"
            return 0
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            log_error "健康检查失败，已尝试 $max_attempts 次"
            return 1
        fi

        log_info "健康检查失败，等待重试... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
}

# 获取当前运行的版本
get_current_version() {
    if docker ps --format "table {{.Names}}\t{{.Image}}" | grep -q "$SERVICE_NAME"; then
        docker ps --format "table {{.Names}}\t{{.Image}}" | grep "$SERVICE_NAME" | awk '{print $2}' | cut -d: -f2
    else
        echo "none"
    fi
}

# 备份当前版本
backup_current_version() {
    local current_version=$(get_current_version)

    if [[ "$current_version" != "none" ]]; then
        log_info "备份当前版本: $current_version"
        echo "$current_version" > "/tmp/${SERVICE_NAME}_previous_version"
        log_success "版本备份完成"
    else
        log_warning "没有找到运行中的服务，跳过备份"
    fi
}

# 回滚功能
rollback() {
    local previous_version_file="/tmp/${SERVICE_NAME}_previous_version"

    if [[ ! -f "$previous_version_file" ]]; then
        log_error "未找到备份版本信息，无法回滚"
        exit 1
    fi

    local previous_version=$(cat "$previous_version_file")
    log_info "回滚到版本: $previous_version"

    VERSION="$previous_version"
    deploy_service
}

# 部署服务
deploy_service() {
    local image_full="${REGISTRY}/${IMAGE_NAME}:${VERSION}"

    log_info "开始部署到 $ENVIRONMENT 环境"
    log_info "镜像: $image_full"
    log_info "服务名: $SERVICE_NAME"
    log_info "端口: $PORT"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "模拟运行模式，不执行实际部署"
        return 0
    fi

    # 备份当前版本
    if [[ "$BACKUP" == "true" ]]; then
        backup_current_version
    fi

    # 拉取镜像
    log_info "拉取镜像..."
    if ! docker pull "$image_full"; then
        log_error "拉取镜像失败: $image_full"
        exit 1
    fi

    # 检查 Docker Compose 文件
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Docker Compose 文件不存在: $COMPOSE_FILE"
        exit 1
    fi

    # 设置环境变量
    export IMAGE_TAG="$VERSION"
    export SERVICE_PORT="$PORT"
    export SERVICE_ENV="$ENVIRONMENT"

    # 停止旧服务
    log_info "停止旧服务..."
    docker-compose -f "$COMPOSE_FILE" down || true

    # 启动新服务
    log_info "启动新服务..."
    if ! docker-compose -f "$COMPOSE_FILE" up -d; then
        log_error "启动服务失败"
        exit 1
    fi

    # 等待服务启动
    sleep 5

    # 健康检查
    if [[ "$FORCE" != "true" ]]; then
        if ! health_check "http://localhost:$PORT"; then
            log_error "健康检查失败，开始回滚..."

            # 自动回滚
            docker-compose -f "$COMPOSE_FILE" down

            if [[ -f "/tmp/${SERVICE_NAME}_previous_version" ]]; then
                local previous_version=$(cat "/tmp/${SERVICE_NAME}_previous_version")
                export IMAGE_TAG="$previous_version"
                docker-compose -f "$COMPOSE_FILE" up -d
                log_warning "已回滚到版本: $previous_version"
            fi

            exit 1
        fi
    fi

    # 清理旧镜像
    log_info "清理未使用的镜像..."
    docker image prune -f || true

    log_success "部署完成!"
    log_info "服务状态:"
    docker-compose -f "$COMPOSE_FILE" ps

    # 显示服务信息
    echo ""
    log_info "服务访问地址:"
    echo "  健康检查: http://localhost:$PORT/health"
    echo "  API 文档:  http://localhost:$PORT/docs"
    echo "  指标监控: http://localhost:$PORT/metrics"
}

# 主函数
main() {
    log_info "=== Gitee-Notion 同步服务部署脚本 ==="
    log_info "环境: $ENVIRONMENT"
    log_info "版本: $VERSION"

    if [[ "$ROLLBACK" == "true" ]]; then
        rollback
    else
        deploy_service
    fi
}

# 陷阱处理，确保清理
trap 'log_error "部署过程被中断"' INT TERM

# 执行主函数
main
