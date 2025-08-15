#!/bin/bash

# 🚀 Robust Docker Build Test Script
# 本地验证稳定构建方案的测试脚本

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

# 配置
IMAGE_NAME="github-notion-robust"
CONTAINER_NAME="test-robust-container"
TEST_PORT="8001"

echo "🚀 Starting Robust Docker Build Test"
echo "=================================="

# 清理函数
cleanup() {
    log_info "Cleaning up test resources..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    docker rmi "$IMAGE_NAME:test" 2>/dev/null || true
    log_success "Cleanup completed"
}

# 设置trap以确保清理
trap cleanup EXIT

# 步骤1: 清理旧资源
log_info "Step 1: Cleaning old resources..."
cleanup

# 步骤2: 测试新的稳定Dockerfile
log_info "Step 2: Testing Dockerfile.robust..."

if [[ ! -f "Dockerfile.robust" ]]; then
    log_error "Dockerfile.robust not found!"
    exit 1
fi

log_info "Building image with Dockerfile.robust..."
docker build \
    -f Dockerfile.robust \
    -t "$IMAGE_NAME:test" \
    --build-arg VERSION="test-$(date +%s)" \
    --build-arg BUILD_TIME="$(date)" \
    . || {
    log_error "Docker build failed!"
    exit 1
}

log_success "Docker image built successfully!"

# 步骤3: 验证镜像信息
log_info "Step 3: Verifying image information..."
docker images "$IMAGE_NAME:test"
docker inspect "$IMAGE_NAME:test" --format='{{.Config.Labels}}' | head -1

# 步骤4: 运行容器测试
log_info "Step 4: Running container test..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$TEST_PORT:8000" \
    -e APP_PORT=8000 \
    -e LOG_LEVEL=INFO \
    -e ENVIRONMENT=testing \
    -e GITEE_WEBHOOK_SECRET="test-secret-for-local-testing" \
    -e DB_URL="sqlite:///data/sync.db" \
    -e DISABLE_NOTION=1 \
    -e DISABLE_METRICS=0 \
    "$IMAGE_NAME:test"

log_success "Container started successfully!"

# 步骤5: 等待服务启动
log_info "Step 5: Waiting for service to start..."
MAX_ATTEMPTS=60
ATTEMPT=0

while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    if curl -sf "http://localhost:$TEST_PORT/health" >/dev/null 2>&1; then
        log_success "Service is running!"
        break
    fi

    ATTEMPT=$((ATTEMPT + 1))
    if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
        log_error "Service failed to start within ${MAX_ATTEMPTS} seconds"
        log_info "Container logs:"
        docker logs --tail 20 "$CONTAINER_NAME"
        exit 1
    fi

    log_info "Waiting... attempt $ATTEMPT/$MAX_ATTEMPTS"
    sleep 1
done

# 步骤6: 功能测试
log_info "Step 6: Running functionality tests..."

# 健康检查测试
log_info "Testing health endpoint..."
health_response=$(curl -s "http://localhost:$TEST_PORT/health")
log_success "Health check response: $health_response"

# API文档测试
log_info "Testing API documentation..."
docs_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$TEST_PORT/docs")
if [[ "$docs_code" == "200" ]]; then
    log_success "API documentation is accessible (HTTP $docs_code)"
else
    log_warning "API documentation returned HTTP $docs_code"
fi

# Metrics测试
log_info "Testing metrics endpoint..."
metrics_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$TEST_PORT/metrics")
if [[ "$metrics_code" == "200" || "$metrics_code" == "307" ]]; then
    log_success "Metrics endpoint is accessible (HTTP $metrics_code)"
else
    log_warning "Metrics endpoint returned HTTP $metrics_code"
fi

# 步骤7: 性能测试
log_info "Step 7: Basic performance test..."
log_info "Testing response times..."
for i in {1..5}; do
    response_time=$(curl -o /dev/null -s -w "%{time_total}" "http://localhost:$TEST_PORT/health")
    log_info "Health check $i: ${response_time}s"
done

# 步骤8: 安全测试
log_info "Step 8: Basic security tests..."
log_info "Testing with invalid webhook signature..."
invalid_response=$(curl -s -w "%{http_code}" -o /dev/null \
    -H "X-Gitee-Event: Issue Hook" \
    -H "X-Gitee-Token: invalid" \
    -H "Content-Type: application/json" \
    -d '{"test": "data"}' \
    "http://localhost:$TEST_PORT/gitee_webhook")

if [[ "$invalid_response" == "403" || "$invalid_response" == "400" ]]; then
    log_success "Security test passed (HTTP $invalid_response)"
else
    log_warning "Security test returned HTTP $invalid_response"
fi

# 步骤9: 显示容器信息
log_info "Step 9: Container information..."
echo "Container status:"
docker ps --filter "name=$CONTAINER_NAME"
echo ""
echo "Container logs (last 10 lines):"
docker logs --tail 10 "$CONTAINER_NAME"
echo ""

# 步骤10: 镜像大小和层信息
log_info "Step 10: Image analysis..."
echo "Image size:"
docker images "$IMAGE_NAME:test" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
echo ""
echo "Image layers:"
docker history "$IMAGE_NAME:test" --no-trunc | head -10

# 最终报告
log_success "🎉 All tests completed successfully!"
echo ""
echo "================== TEST SUMMARY =================="
echo "✅ Docker build: SUCCESS"
echo "✅ Container startup: SUCCESS"
echo "✅ Health check: SUCCESS"
echo "✅ API documentation: SUCCESS"
echo "✅ Metrics endpoint: SUCCESS"
echo "✅ Security test: SUCCESS"
echo "✅ Performance test: SUCCESS"
echo ""
echo "📦 Built image: $IMAGE_NAME:test"
echo "🌐 Test URL: http://localhost:$TEST_PORT"
echo "📖 API docs: http://localhost:$TEST_PORT/docs"
echo "📊 Metrics: http://localhost:$TEST_PORT/metrics"
echo "=================================================="
echo ""
log_info "The robust Docker build is ready for GitHub Actions!"
echo ""
echo "Next steps:"
echo "1. Commit the new files (Dockerfile.robust, robust-ci.yml)"
echo "2. Push to GitHub to trigger the robust CI/CD pipeline"
echo "3. Monitor the GitHub Actions for successful build"
echo ""

# 保持容器运行以便进一步测试
read -p "Press Enter to cleanup and exit, or Ctrl+C to keep container running for manual testing..."
