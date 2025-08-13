#!/bin/bash

# =================================================================
# AWS 服务器自动部署脚本
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

# AWS 服务器配置
AWS_SERVER="13.209.76.79"
AWS_USER="ubuntu"  # 默认 Ubuntu AMI 用户
SSH_KEY_PATH="$HOME/.ssh/aws-key.pem"  # 您需要提供 SSH 密钥路径

# GitHub 容器注册表配置
export REGISTRY="ghcr.io"
export REGISTRY_USERNAME="xupeng211"
export REGISTRY_PASSWORD="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"
export IMAGE_NAME="xupeng211/gitee-notion"

# 生成版本标签
VERSION=$(git rev-parse --short HEAD)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

log_info "=== AWS 服务器部署 ==="
log_info "目标服务器: $AWS_SERVER"
log_info "镜像: $REGISTRY/$IMAGE_NAME:$VERSION"
log_info "时间戳: $TIMESTAMP"

# 步骤 1: 本地构建和推送镜像
deploy_local_build() {
    log_info "🏗️ 本地构建镜像..."
    
    # 检查 Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    # 登录 GitHub Container Registry
    log_info "🔑 登录 GitHub Container Registry..."
    echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY" -u "$REGISTRY_USERNAME" --password-stdin
    
    # 构建镜像
    log_info "🏗️ 构建 Docker 镜像..."
    if [[ -f "Dockerfile.optimized" ]]; then
        DOCKERFILE="Dockerfile.optimized"
    else
        DOCKERFILE="Dockerfile"
    fi
    
    docker build \
        --build-arg VERSION="$VERSION" \
        --build-arg BUILD_TIME="$TIMESTAMP" \
        --target production \
        --cache-from "${REGISTRY}/${IMAGE_NAME}:latest" \
        -f "$DOCKERFILE" \
        -t "${REGISTRY}/${IMAGE_NAME}:${VERSION}" \
        -t "${REGISTRY}/${IMAGE_NAME}:latest" \
        .
    
    # 推送镜像
    log_info "📤 推送镜像到注册表..."
    docker push "${REGISTRY}/${IMAGE_NAME}:${VERSION}"
    docker push "${REGISTRY}/${IMAGE_NAME}:latest"
    
    log_success "镜像构建和推送完成"
}

# 步骤 2: 准备服务器部署文件
prepare_deployment_files() {
    log_info "📋 准备部署文件..."
    
    # 创建临时部署目录
    DEPLOY_DIR="/tmp/gitee-notion-deploy-${TIMESTAMP}"
    mkdir -p "$DEPLOY_DIR"
    
    # 复制必要文件
    cp docker-compose.production.yml "$DEPLOY_DIR/"
    cp -r monitoring "$DEPLOY_DIR/" 2>/dev/null || log_warning "监控配置目录不存在"
    cp -r reverse-proxy "$DEPLOY_DIR/" 2>/dev/null || log_warning "反向代理配置不存在"
    
    # 创建环境变量文件
    cat > "$DEPLOY_DIR/.env" << EOF
# 生产环境配置
LOG_LEVEL=INFO
ENVIRONMENT=production
APP_PORT=8000

# 数据库配置
DB_URL=sqlite:///data/sync.db

# 镜像配置
REGISTRY=$REGISTRY
IMAGE_NAME=$IMAGE_NAME
IMAGE_TAG=$VERSION

# 服务配置
SERVICE_PORT=8000
SERVICE_ENV=production
DEPLOYMENT_TIME=$TIMESTAMP

# 安全配置
RATE_LIMIT_PER_MINUTE=60
MAX_REQUEST_SIZE=1048576
DEADLETTER_REPLAY_TOKEN=admin-secure-token-$TIMESTAMP

# 监控配置
GRAFANA_PASSWORD=admin123secure
GRAFANA_SECRET_KEY=grafana-secret-$TIMESTAMP

# Gitee 配置 (需要您设置)
GITEE_WEBHOOK_SECRET=your-webhook-secret-here

# Notion 配置 (需要您设置)
# NOTION_TOKEN=secret_your-notion-token
# NOTION_DATABASE_ID=your-database-id
EOF
    
    # 创建部署脚本
    cat > "$DEPLOY_DIR/deploy_on_server.sh" << 'EOF'
#!/bin/bash
set -e

echo "🚀 开始服务器部署..."

# 安装 Docker 和 Docker Compose (如果未安装)
install_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "📦 安装 Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        echo "📦 安装 Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
}

# 主部署流程
main_deploy() {
    install_docker
    
    # 创建应用目录
    APP_DIR="/opt/gitee-notion-sync"
    sudo mkdir -p "$APP_DIR"
    sudo chown $USER:$USER "$APP_DIR"
    
    # 复制文件到应用目录
    cp -r . "$APP_DIR/"
    cd "$APP_DIR"
    
    # 加载环境变量
    source .env
    
    # 登录容器注册表
    echo "🔑 登录容器注册表..."
    echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY" -u "$REGISTRY_USERNAME" --password-stdin
    
    # 创建必要目录
    mkdir -p data logs monitoring
    
    # 停止旧服务
    echo "🛑 停止旧服务..."
    docker-compose -f docker-compose.production.yml down 2>/dev/null || true
    
    # 拉取最新镜像
    echo "📥 拉取镜像..."
    docker pull "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    
    # 启动服务
    echo "🚀 启动服务..."
    docker-compose -f docker-compose.production.yml up -d
    
    # 等待服务启动
    echo "⏳ 等待服务启动..."
    sleep 15
    
    # 健康检查
    for i in {1..30}; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            echo "✅ 服务启动成功!"
            break
        fi
        if [[ $i -eq 30 ]]; then
            echo "❌ 服务启动失败"
            docker-compose -f docker-compose.production.yml logs
            exit 1
        fi
        echo "等待服务启动... ($i/30)"
        sleep 2
    done
    
    # 显示服务状态
    echo "📊 服务状态:"
    docker-compose -f docker-compose.production.yml ps
    
    echo ""
    echo "🎉 部署完成!"
    echo "📍 服务访问地址:"
    echo "  健康检查: http://$(curl -s ifconfig.me):8000/health"
    echo "  API 文档:  http://$(curl -s ifconfig.me):8000/docs"
    echo "  监控指标: http://$(curl -s ifconfig.me):8000/metrics"
}

main_deploy
EOF
    
    chmod +x "$DEPLOY_DIR/deploy_on_server.sh"
    
    log_success "部署文件准备完成: $DEPLOY_DIR"
}

# 步骤 3: 上传和部署到服务器
deploy_to_server() {
    log_info "🌐 部署到 AWS 服务器..."
    
    # 检查 SSH 密钥
    if [[ ! -f "$SSH_KEY_PATH" ]]; then
        log_warning "SSH 密钥文件不存在: $SSH_KEY_PATH"
        log_info "请确保您有 AWS EC2 的 SSH 密钥文件"
        read -p "请输入 SSH 密钥文件路径: " SSH_KEY_PATH
    fi
    
    # 测试 SSH 连接
    log_info "🔗 测试 SSH 连接..."
    if ! ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$AWS_USER@$AWS_SERVER" "echo 'SSH 连接成功'" 2>/dev/null; then
        log_error "SSH 连接失败，请检查:"
        echo "  1. SSH 密钥文件路径: $SSH_KEY_PATH"
        echo "  2. 服务器地址: $AWS_SERVER"
        echo "  3. 安全组是否开放 SSH (端口 22)"
        exit 1
    fi
    
    # 上传部署文件
    log_info "📤 上传部署文件..."
    scp -i "$SSH_KEY_PATH" -r "$DEPLOY_DIR" "$AWS_USER@$AWS_SERVER:/tmp/"
    
    # 执行远程部署
    log_info "🚀 执行远程部署..."
    ssh -i "$SSH_KEY_PATH" "$AWS_USER@$AWS_SERVER" "cd /tmp/$(basename $DEPLOY_DIR) && bash deploy_on_server.sh"
    
    log_success "服务器部署完成!"
    
    # 显示访问信息
    echo ""
    log_info "🌟 部署成功信息:"
    echo "  服务器地址: http://$AWS_SERVER:8000"
    echo "  健康检查: http://$AWS_SERVER:8000/health"
    echo "  API 文档:  http://$AWS_SERVER:8000/docs"
    echo "  监控指标: http://$AWS_SERVER:8000/metrics"
    echo ""
    log_info "📋 后续配置提醒:"
    echo "  1. 配置 Gitee Webhook URL: http://$AWS_SERVER:8000/gitee_webhook"
    echo "  2. 设置 GITEE_WEBHOOK_SECRET 环境变量"
    echo "  3. 配置 Notion API Token 和 Database ID"
    echo "  4. 配置 AWS 安全组开放端口 8000"
}

# 主函数
main() {
    echo "请选择部署方式:"
    echo "1. 完整自动部署 (推荐)"
    echo "2. 仅本地构建镜像"
    echo "3. 仅部署到服务器 (假设镜像已存在)"
    
    read -p "请输入选择 (1-3): " choice
    
    case $choice in
        1)
            deploy_local_build
            prepare_deployment_files
            deploy_to_server
            ;;
        2)
            deploy_local_build
            ;;
        3)
            prepare_deployment_files
            deploy_to_server
            ;;
        *)
            log_error "无效选择"
            exit 1
            ;;
    esac
}

# 错误处理
trap 'log_error "部署过程被中断"' INT TERM

# 检查必要的工具
if ! command -v git >/dev/null 2>&1; then
    log_error "Git 未安装"
    exit 1
fi

if ! command -v ssh >/dev/null 2>&1; then
    log_error "SSH 客户端未安装"
    exit 1
fi

# 执行主函数
main 