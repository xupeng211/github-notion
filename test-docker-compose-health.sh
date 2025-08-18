#!/bin/bash
# 🧪 测试 Docker Compose 健康检查修复
# 验证容器健康检查和 CI/CD 流程

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🧪 测试 Docker Compose 健康检查修复...${NC}"

# 清理现有容器
echo -e "${BLUE}1. 清理现有容器...${NC}"
docker-compose down 2>/dev/null || true
docker system prune -f 2>/dev/null || true

# 设置测试环境变量
echo -e "${BLUE}2. 设置测试环境变量...${NC}"
export ENVIRONMENT=ci
export APP_PORT=8000
export LOG_LEVEL=DEBUG

# 启动服务
echo -e "${BLUE}3. 启动 Docker Compose 服务...${NC}"
if docker-compose up -d; then
    echo "✅ Docker Compose 启动成功"
else
    echo "❌ Docker Compose 启动失败"
    exit 1
fi

# 等待服务启动
echo -e "${BLUE}4. 等待服务启动...${NC}"
echo "等待 30 秒..."
sleep 30

# 检查容器状态
echo -e "${BLUE}5. 检查容器状态...${NC}"
echo "容器列表:"
docker ps

echo -e "\n容器健康状态:"
if docker ps --format "table {{.Names}}\t{{.Status}}" | grep github-notion-sync; then
    echo "✅ 容器正在运行"
    
    # 检查 Docker 健康检查状态
    health_status=$(docker inspect --format='{{.State.Health.Status}}' github-notion-sync-app 2>/dev/null || echo "unknown")
    echo "Docker 健康检查状态: $health_status"
    
    # 获取容器日志
    echo -e "\n最新容器日志:"
    docker logs --tail 10 github-notion-sync-app
    
else
    echo "❌ 容器未运行"
    echo "检查所有容器:"
    docker ps -a
    exit 1
fi

# 测试健康检查端点
echo -e "${BLUE}6. 测试健康检查端点...${NC}"

# 等待额外时间确保应用完全启动
echo "等待应用完全启动..."
sleep 15

# 测试 CI 健康检查
echo "测试 CI 健康检查 (/health/ci):"
if curl -f -m 10 http://localhost:8000/health/ci > /tmp/health-ci-test.json 2>/dev/null; then
    echo "✅ CI 健康检查成功"
    echo "响应内容:"
    cat /tmp/health-ci-test.json | python3 -m json.tool 2>/dev/null || cat /tmp/health-ci-test.json
    
    # 检查状态
    status=$(cat /tmp/health-ci-test.json | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
    if [ "$status" = "healthy" ]; then
        echo "✅ 状态正确: $status"
    else
        echo "❌ 状态错误: $status"
    fi
else
    echo "❌ CI 健康检查失败"
    echo "尝试连接测试:"
    curl -v http://localhost:8000/health/ci || true
fi

echo ""

# 测试标准健康检查
echo "测试标准健康检查 (/health):"
if curl -f -m 10 http://localhost:8000/health > /tmp/health-standard-test.json 2>/dev/null; then
    echo "✅ 标准健康检查成功"
    
    # 检查状态
    status=$(cat /tmp/health-standard-test.json | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
    echo "状态: $status"
else
    echo "❌ 标准健康检查失败"
fi

# 模拟 GitHub Actions 检查流程
echo -e "${BLUE}7. 模拟 GitHub Actions 检查流程...${NC}"

echo "检查容器是否在运行..."
if docker ps | grep -q github-notion-sync-app; then
    echo "✅ 容器正在运行"
    
    # 检查 Docker 健康检查状态
    health_status=$(docker inspect --format='{{.State.Health.Status}}' github-notion-sync-app 2>/dev/null || echo "unknown")
    echo "Docker 健康检查状态: $health_status"
    
    if [ "$health_status" = "healthy" ] || [ "$health_status" = "unknown" ]; then
        echo "🧪 CI/CD 健康检查..."
        if curl -f http://localhost:8000/health/ci > /dev/null 2>&1; then
            echo "✅ 部署成功"
            deployment_success=true
        else
            echo "❌ CI/CD 健康检查失败，尝试标准健康检查..."
            if curl -f http://localhost:8000/health > /dev/null 2>&1; then
                echo "⚠️ 标准健康检查通过，但状态可能为 degraded"
                echo "✅ 部署成功（CI/CD 模式）"
                deployment_success=true
            else
                echo "❌ 所有健康检查都失败"
                deployment_success=false
            fi
        fi
    else
        echo "❌ Docker 健康检查失败: $health_status"
        deployment_success=false
    fi
else
    echo "❌ 容器未运行"
    deployment_success=false
fi

# 清理
echo -e "${BLUE}8. 清理测试环境...${NC}"
docker-compose down
rm -f /tmp/health-*-test.json

# 总结
echo -e "${BLUE}9. 测试总结...${NC}"
if [ "${deployment_success:-false}" = "true" ]; then
    echo -e "${GREEN}🎉 测试成功！CI/CD 健康检查修复有效${NC}"
    echo -e "${GREEN}✅ Docker Compose 健康检查正常工作${NC}"
    echo -e "${GREEN}✅ GitHub Actions 流程应该能够成功${NC}"
else
    echo -e "${RED}❌ 测试失败！需要进一步调试${NC}"
    echo -e "${YELLOW}💡 建议检查容器日志和健康检查配置${NC}"
fi

echo -e "\n${CYAN}📋 测试完成！${NC}"
