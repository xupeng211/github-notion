#!/bin/bash

# 镜像构建测试脚本
set -euo pipefail

echo "🐳 开始 Docker 镜像构建测试..."

# 清理旧的测试资源
echo "🧹 清理旧的测试资源..."
docker rm -f test-app 2>/dev/null || true
docker rmi test-build:latest 2>/dev/null || true

# 构建镜像
echo "🏗️ 构建 Docker 镜像..."
docker build -f Dockerfile -t test-build:latest .

# 测试镜像基本功能
echo "🧪 测试镜像基本功能..."
docker run -d --name test-app -p 8001:8000 \
  -e APP_PORT=8000 \
  -e LOG_LEVEL=INFO \
  -e GITEE_WEBHOOK_SECRET=test-secret \
  -e DB_URL=sqlite:///data/sync.db \
  -e ENVIRONMENT=test \
  -e DISABLE_NOTION=true \
  -e DISABLE_METRICS=false \
  test-build:latest

# 等待服务启动
echo "⏳ 等待服务启动..."
for i in {1..30}; do
  if curl -f http://127.0.0.1:8001/health >/dev/null 2>&1; then
    echo "✅ 服务启动成功"
    break
  fi
  echo "等待中... ($i/30)"
  sleep 2
done

# 健康检查测试
echo "🏥 健康检查测试..."
health_response=$(curl -s http://127.0.0.1:8001/health)
echo "健康检查响应: $health_response"

# 指标端点测试
echo "📊 指标端点测试..."
metrics_code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/metrics)
if [ "$metrics_code" == "200" ] || [ "$metrics_code" == "307" ]; then
  echo "✅ 指标端点正常: $metrics_code"
else
  echo "❌ 指标端点异常: $metrics_code"
  docker logs test-app
  exit 1
fi

# API 文档测试
echo "📚 API 文档测试..."
docs_code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/docs)
if [ "$docs_code" == "200" ]; then
  echo "✅ API 文档正常: $docs_code"
else
  echo "❌ API 文档异常: $docs_code"
  docker logs test-app
  exit 1
fi

# 显示容器日志
echo "📋 容器日志 (最后20行):"
docker logs --tail 20 test-app

# 清理测试资源
echo "🧹 清理测试资源..."
docker rm -f test-app
docker rmi test-build:latest

echo "🎉 Docker 镜像构建测试完成！所有测试都通过了。"
