#!/bin/bash
# 快速Docker构建和测试脚本
# 用于验证Docker配置和镜像构建

set -e

echo "🚀 快速Docker构建测试"
echo "=================================="

# 检查Docker可用性
echo "🔍 检查Docker..."
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker未找到，请先配置Docker Desktop WSL集成"
    exit 1
fi

docker --version
echo "✅ Docker可用"

# 构建镜像
echo ""
echo "🏗️ 构建镜像..."
docker build -t gitee-notion:quick-test . --no-cache

# 测试容器启动
echo ""
echo "🧪 测试容器启动..."
CONTAINER_ID=$(docker run -d --name quick-test \
  -p 8003:8000 \
  -e GITEE_WEBHOOK_SECRET=test \
  -e GITHUB_WEBHOOK_SECRET=test \
  -e DISABLE_NOTION=1 \
  -e DISABLE_METRICS=1 \
  gitee-notion:quick-test)

echo "容器ID: $CONTAINER_ID"

# 等待启动
echo "⏳ 等待应用启动..."
sleep 10

# 健康检查
echo "🩺 健康检查..."
if curl -f http://localhost:8003/health >/dev/null 2>&1; then
    echo "✅ 健康检查通过"
    echo "应用运行正常！"
else
    echo "⚠️ 健康检查失败，检查日志："
    docker logs quick-test
fi

# 清理
echo ""
echo "🧹 清理测试环境..."
docker stop quick-test >/dev/null 2>&1 || true
docker rm quick-test >/dev/null 2>&1 || true

echo "✅ 快速测试完成！"
