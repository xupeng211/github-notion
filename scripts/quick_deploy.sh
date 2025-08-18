#!/bin/bash

# =================================================================
# 快速 CI/CD 部署脚本
# =================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 默认配置
ENVIRONMENT="staging"
BUILD_ONLY=false
DEPLOY_ONLY=false
WITH_MONITORING=false
SKIP_TESTS=false
REGISTRY="${REGISTRY:-your-registry.com}"
IMAGE_NAME="${IMAGE_NAME:-gitee-notion-sync}"

show_help() {
    cat << EOF
快速 CI/CD 部署脚本

用法: $0 [选项]

选项:
  -e, --env             目标环境 (dev|staging|production) [默认: staging]
  -b, --build-only      仅构建镜像，不部署
  -d, --deploy-only     仅部署，不构建 (使用 latest 标签)
  -m, --monitoring      同时启动监控服务 (Prometheus + Grafana)
  -s, --skip-tests      跳过测试阶段
  -h, --help            显示帮助信息

示例:
  $0                           # 构建并部署到 staging
  $0 -e production -m          # 构建并部署到生产环境，启用监控
  $0 --build-only              # 仅构建镜像
  $0 --deploy-only -e staging  # 仅部署到 staging

EOF
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -b|--build-only)
            BUILD_ONLY=true
            shift
            ;;
        -d|--deploy-only)
            DEPLOY_ONLY=true
            shift
            ;;
        -m|--monitoring)
            WITH_MONITORING=true
            shift
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
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

# 生成版本标签
VERSION=$(git rev-parse --short HEAD)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_FULL="${REGISTRY}/${IMAGE_NAME}"

log_info "=== 快速 CI/CD 部署 ==="
log_info "环境: $ENVIRONMENT"
log_info "版本: $VERSION"
log_info "时间戳: $TIMESTAMP"

# 阶段 1: 测试 (可选)
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "跳过测试阶段"
        return
    fi

    log_info "📋 运行测试..."

    # 检查虚拟环境
    if [[ ! -d ".venv" ]]; then
        log_info "创建虚拟环境..."
        python3 -m venv .venv
    fi

    source .venv/bin/activate
    pip install -q -r requirements.txt

    # 运行测试
    python -m pytest tests/ -v --tb=short -x

    # 检查代码质量 (可选)
    if command -v flake8 >/dev/null 2>&1; then
        log_info "检查代码风格..."
        flake8 app/ --max-line-length=120 --ignore=E203,W503 || log_warning "代码风格检查发现问题"
    fi

    log_success "测试完成"
}

# 阶段 2: 构建镜像
build_image() {
    log_info "🏗️ 构建 Docker 镜像..."

    # 使用优化的 Dockerfile
    if [[ -f "Dockerfile.optimized" ]]; then
        DOCKERFILE="Dockerfile.optimized"
    else
        DOCKERFILE="Dockerfile"
    fi

    # 构建镜像
    docker build \
        --build-arg VERSION="$VERSION" \
        --build-arg BUILD_TIME="$TIMESTAMP" \
        --target production \
        --cache-from "${IMAGE_FULL}:latest" \
        -f "$DOCKERFILE" \
        -t "${IMAGE_FULL}:${VERSION}" \
        -t "${IMAGE_FULL}:latest" \
        -t "${IMAGE_FULL}:${TIMESTAMP}" \
        .

    log_success "镜像构建完成"

    # 快速冒烟测试
    log_info "💨 运行冒烟测试..."
    docker run -d --name quick-test -p 18000:8000 \
        -e GITEE_WEBHOOK_SECRET=test \
        -e LOG_LEVEL=INFO \
        "${IMAGE_FULL}:${VERSION}"

    sleep 3

    if curl -f http://localhost:18000/health >/dev/null 2>&1; then
        log_success "冒烟测试通过"
    else
        log_error "冒烟测试失败"
        docker logs quick-test
        docker rm -f quick-test
        exit 1
    fi

    docker rm -f quick-test

    # 推送镜像 (如果配置了 registry)
    if [[ -n "$REGISTRY_PASSWORD" && -n "$REGISTRY_USERNAME" ]]; then
        log_info "📤 推送镜像到仓库..."
        echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY" -u "$REGISTRY_USERNAME" --password-stdin

        docker push "${IMAGE_FULL}:${VERSION}"
        docker push "${IMAGE_FULL}:latest"
        docker push "${IMAGE_FULL}:${TIMESTAMP}"

        log_success "镜像推送完成"
    else
        log_warning "未配置镜像仓库凭据，跳过推送"
    fi
}

# 阶段 3: 部署服务
deploy_service() {
    log_info "🚀 部署到 $ENVIRONMENT 环境..."

    # 确定 compose 文件
    case $ENVIRONMENT in
        dev)
            COMPOSE_FILE="docker-compose.dev.yml"
            PORT=8001
            ;;
        staging)
            COMPOSE_FILE="docker-compose.staging.yml"
            PORT=8002
            ;;
        production)
            COMPOSE_FILE="docker-compose.production.yml"
            PORT=8000
            ;;
        *)
            log_error "不支持的环境: $ENVIRONMENT"
            exit 1
            ;;
    esac

    # 检查配置文件
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "找不到配置文件: $COMPOSE_FILE"
        exit 1
    fi

    # 设置环境变量
    export IMAGE_TAG="$VERSION"
    export SERVICE_PORT="$PORT"
    export SERVICE_ENV="$ENVIRONMENT"
    export DEPLOYMENT_TIME="$TIMESTAMP"

    # 创建必要目录
    mkdir -p data logs monitoring

    # 部署服务
    if [[ "$WITH_MONITORING" == "true" ]]; then
        log_info "启用监控服务..."
        docker-compose -f "$COMPOSE_FILE" --profile monitoring up -d
    else
        docker-compose -f "$COMPOSE_FILE" up -d
    fi

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10

    # 健康检查
    MAX_ATTEMPTS=30
    for i in $(seq 1 $MAX_ATTEMPTS); do
        if curl -f "http://localhost:$PORT/health" >/dev/null 2>&1; then
            log_success "服务启动成功"
            break
        fi

        if [[ $i -eq $MAX_ATTEMPTS ]]; then
            log_error "服务启动失败"
            docker-compose -f "$COMPOSE_FILE" logs
            exit 1
        fi

        log_info "等待服务启动... ($i/$MAX_ATTEMPTS)"
        sleep 2
    done

    # 显示服务状态
    log_info "📊 服务状态:"
    docker-compose -f "$COMPOSE_FILE" ps

    echo ""
    log_success "部署完成!"
    log_info "服务访问地址:"
    echo "  🏥 健康检查: http://localhost:$PORT/health"
    echo "  📚 API 文档:  http://localhost:$PORT/docs"
    echo "  📊 监控指标: http://localhost:$PORT/metrics"

    if [[ "$WITH_MONITORING" == "true" ]]; then
        echo "  📈 Prometheus: http://localhost:9090"
        echo "  📊 Grafana:    http://localhost:3000"
    fi
}

# 主要流程
main() {
    # 检查 Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_error "未安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "未安装 Docker Compose"
        exit 1
    fi

    # 执行流程
    if [[ "$DEPLOY_ONLY" == "true" ]]; then
        deploy_service
    elif [[ "$BUILD_ONLY" == "true" ]]; then
        run_tests
        build_image
    else
        # 完整流程
        run_tests
        build_image
        deploy_service
    fi

    log_success "🎉 所有任务完成!"
}

# 错误处理
trap 'log_error "部署过程被中断"' INT TERM

# 执行主函数
main
