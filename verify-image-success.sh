#!/bin/bash

# 🔍 验证Docker镜像构建成功状态
# 确认镜像是否已经成功推送到GitHub Container Registry

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 镜像信息
REGISTRY="ghcr.io"
IMAGE_NAME="xupeng211/gitee-notion"
IMAGE_FULL="${REGISTRY}/${IMAGE_NAME}"

echo "🔍 验证Docker镜像构建成功状态"
echo "================================="

# 步骤1: 检查镜像是否可拉取
log_info "Step 1: 尝试拉取镜像..."
if docker pull "${IMAGE_FULL}:latest" 2>/dev/null; then
    log_success "✅ 镜像拉取成功！镜像已存在于registry中"
    PULL_SUCCESS=true
else
    log_error "❌ 镜像拉取失败，可能需要认证或镜像不存在"
    PULL_SUCCESS=false
fi

# 步骤2: 如果拉取成功，验证镜像
if [[ "$PULL_SUCCESS" == "true" ]]; then
    log_info "Step 2: 验证镜像信息..."

    # 显示镜像详情
    echo "镜像详情:"
    docker images "${IMAGE_FULL}:latest" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

    # 检查镜像标签和创建时间
    IMAGE_ID=$(docker images "${IMAGE_FULL}:latest" --format "{{.ID}}")
    CREATED=$(docker images "${IMAGE_FULL}:latest" --format "{{.CreatedAt}}")

    echo ""
    log_info "镜像ID: $IMAGE_ID"
    log_info "创建时间: $CREATED"

    # 步骤3: 运行容器测试
    log_info "Step 3: 运行容器测试..."

    CONTAINER_NAME="verify-container"
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

    if docker run -d \
        --name "$CONTAINER_NAME" \
        -p 8080:8000 \
        -e GITEE_WEBHOOK_SECRET="test-secret" \
        -e DB_URL="sqlite:///data/sync.db" \
        -e LOG_LEVEL="INFO" \
        -e ENVIRONMENT="testing" \
        -e DISABLE_NOTION="1" \
        "${IMAGE_FULL}:latest" 2>/dev/null; then

        log_success "容器启动成功！"

        # 等待服务启动
        log_info "等待服务启动..."
        for i in {1..30}; do
            if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
                log_success "✅ 健康检查通过！服务正常运行"

                # 获取健康检查响应
                health_response=$(curl -s http://localhost:8080/health)
                log_info "健康检查响应: $health_response"
                break
            fi

            if [[ $i -eq 30 ]]; then
                log_warning "健康检查超时，但容器可能仍在启动"
            fi

            sleep 1
        done

        # 显示容器日志
        echo ""
        log_info "容器日志 (最后10行):"
        docker logs --tail 10 "$CONTAINER_NAME"

        # 清理
        docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1

    else
        log_error "❌ 容器启动失败"
        docker logs "$CONTAINER_NAME" 2>/dev/null || true
        docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    fi

else
    log_info "Step 2: 检查是否需要Docker登录..."
    log_info "如果镜像确实存在但拉取失败，可能需要登录："
    echo "  docker login ghcr.io -u xupeng211"
    echo ""
    log_info "或者检查镜像是否为private，需要适当的权限"
fi

# 步骤4: 提供使用指南
echo ""
log_info "📖 使用指南:"

if [[ "$PULL_SUCCESS" == "true" ]]; then
    echo "✅ 恭喜！你的Docker镜像构建成功并且可以正常使用！"
    echo ""
    echo "🚀 使用方法:"
    echo "1. 拉取镜像:"
    echo "   docker pull ${IMAGE_FULL}:latest"
    echo ""
    echo "2. 运行容器:"
    echo "   docker run -d \\"
    echo "     --name gitee-notion-app \\"
    echo "     -p 8000:8000 \\"
    echo "     -e GITEE_WEBHOOK_SECRET=\"your-webhook-secret\" \\"
    echo "     -e DB_URL=\"sqlite:///data/sync.db\" \\"
    echo "     ${IMAGE_FULL}:latest"
    echo ""
    echo "3. 访问服务:"
    echo "   - 健康检查: http://localhost:8000/health"
    echo "   - API文档: http://localhost:8000/docs"
    echo "   - 监控指标: http://localhost:8000/metrics"
    echo ""
    log_success "🎉 镜像构建和推送完全成功！"
else
    echo "🔍 镜像验证结果："
    echo "- 可能镜像已经存在但需要认证"
    echo "- 或者镜像确实还未成功构建"
    echo ""
    echo "📝 下一步建议："
    echo "1. 检查GitHub Actions的最新运行状态"
    echo "2. 查看是否有新的workflow正在运行"
    echo "3. 如果需要，可以手动触发新的构建"
fi

echo ""
echo "🔗 相关链接:"
echo "- GitHub Actions: https://github.com/xupeng211/github-notion/actions"
echo "- GitHub Registry: https://github.com/xupeng211/github-notion/pkgs/container/gitee-notion"

echo ""
log_info "验证完成！"
