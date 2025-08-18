#!/bin/bash
# 🧪 本地构建测试脚本

set -e

echo "🧪 开始本地构建测试..."

# 1. 测试 Docker 构建
echo "1. 测试 Docker 构建..."
docker build -f Dockerfile.optimized -t github-notion:test . --no-cache

# 2. 测试容器启动
echo "2. 测试容器启动..."
CONTAINER_ID=$(docker run -d --name test-container \
  -p 8001:8000 \
  -e ENVIRONMENT=testing \
  -e DISABLE_NOTION=true \
  -e DISABLE_METRICS=true \
  github-notion:test)

# 3. 等待启动
echo "3. 等待服务启动..."
sleep 10

# 4. 健康检查
echo "4. 执行健康检查..."
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
  echo "✅ 本地构建测试成功！"
else
  echo "❌ 健康检查失败"
  docker logs test-container
  exit 1
fi

# 5. 清理
echo "5. 清理测试环境..."
docker stop test-container
docker rm test-container

echo "🎉 本地测试完成！"
